"""
Smart Question Filter - Sistema inteligente para filtrar perguntas redundantes.
Usa regras de exclusão e lógica contextual para evitar perguntas desnecessárias.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re

from app.models.intake import Question
from app.services.context_inference_engine import InferenceResult, InferenceConfidence
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


class FilterReason(Enum):
    """Razões para filtrar perguntas."""

    OBVIOUS_FROM_CONTEXT = "obvious_from_context"
    ALREADY_DESCRIBED = "already_described"
    DOMAIN_IMPLICATION = "domain_implication"
    REDUNDANT_INFORMATION = "redundant_information"
    LOW_VALUE_ADD = "low_value_add"
    CONTRADICTORY = "contradictory"


@dataclass
class FilterDecision:
    """Decisão de filtro para uma pergunta."""

    question_id: str
    should_exclude: bool
    reason: FilterReason
    explanation: str
    confidence: float
    evidence: List[str] = field(default_factory=list)


class SmartQuestionFilter:
    """
    Sistema inteligente para filtrar perguntas redundantes ou desnecessárias.

    Usa regras contextuais e análise semântica para determinar quais perguntas
    não agregam valor dado o contexto já fornecido.
    """

    def __init__(self):
        """Inicializa o filtro inteligente."""
        # Regras de exclusão por domínio
        self.domain_exclusion_rules = self._initialize_domain_rules()

        # Mapeamento de keywords para inferências
        self.keyword_implications = self._initialize_keyword_implications()

        # Padrões de redundância
        self.redundancy_patterns = self._initialize_redundancy_patterns()

        # Estatísticas
        self.filter_stats = {"total_evaluations": 0, "questions_filtered": 0, "filter_reasons": {}}

        logger.info("Smart Question Filter initialized")

    def _initialize_domain_rules(self) -> Dict[str, Dict[str, List[str]]]:
        """Inicializa regras de exclusão específicas por domínio."""
        return {
            "fintech": {
                "obvious_implications": [
                    # Se é fintech, obviamente lida com dados sensíveis
                    "A aplicação lidará com dados sensíveis?",
                    "Quais dados sensíveis serão tratados?",
                    "O sistema precisa de alta segurança?",
                ],
                "domain_specific_redundant": [
                    # Se mencionou fintech, finalidade é óbvia
                    "Qual a finalidade principal da aplicação?",
                    "Que tipo de sistema você está construindo?",
                ],
            },
            "ecommerce": {
                "obvious_implications": [
                    "O sistema terá funcionalidade de vendas?",
                    "Será necessário processar pagamentos?",
                    "Haverá gestão de produtos?",
                    "O sistema precisa de carrinho de compras?",
                ],
                "domain_specific_redundant": [
                    "Qual a finalidade principal da aplicação?",
                    "Que tipo de sistema você está construindo?",
                ],
            },
            "healthcare": {
                "obvious_implications": [
                    "A aplicação lidará com dados sensíveis?",
                    "O sistema precisa de alta segurança?",
                    "Há requisitos de compliance específicos?",
                ],
                "domain_specific_redundant": [
                    "Qual o setor da empresa?",
                    "Que tipo de dados serão processados?",
                ],
            },
            "education": {
                "obvious_implications": [
                    "O sistema terá diferentes tipos de usuários?",
                    "Haverá gestão de conteúdo?",
                    "Será necessário acompanhamento de progresso?",
                ],
                "domain_specific_redundant": [
                    "Qual a finalidade principal da aplicação?",
                ],
            },
        }

    def _initialize_keyword_implications(self) -> Dict[str, Dict[str, Any]]:
        """Mapeia keywords para implicações automáticas."""
        return {
            # Keywords financeiras
            "fintech": {
                "implies": ["dados_sensíveis", "alta_segurança", "compliance_financeiro"],
                "excludes_questions": ["dados sensíveis", "finalidade", "setor"],
            },
            "investimentos": {
                "implies": ["dados_financeiros", "compliance_cvm", "relatórios"],
                "excludes_questions": ["finalidade", "dados sensíveis"],
            },
            "dashboard financeiro": {
                "implies": ["aplicação_web", "relatórios", "gráficos"],
                "excludes_questions": ["tipo aplicação", "finalidade"],
            },
            # Keywords e-commerce
            "loja virtual": {
                "implies": ["ecommerce", "pagamentos", "produtos"],
                "excludes_questions": ["finalidade", "funcionalidades principais"],
            },
            "e-commerce": {
                "implies": ["vendas_online", "estoque", "carrinho"],
                "excludes_questions": ["finalidade", "tipo sistema"],
            },
            # Keywords saúde
            "telemedicina": {
                "implies": ["healthcare", "dados_sensíveis", "hipaa"],
                "excludes_questions": ["setor", "dados sensíveis", "compliance"],
            },
            "prontuário": {
                "implies": ["dados_médicos", "alta_segurança"],
                "excludes_questions": ["dados sensíveis", "setor"],
            },
            # Keywords técnicas
            "dashboard": {
                "implies": ["aplicação_web", "relatórios", "visualização"],
                "excludes_questions": ["tipo aplicação"],
            },
            "api": {"implies": ["backend", "integração"], "excludes_questions": []},
            "mobile app": {
                "implies": ["aplicação_mobile"],
                "excludes_questions": ["tipo aplicação", "plataforma"],
            },
        }

    def _initialize_redundancy_patterns(self) -> List[Dict[str, Any]]:
        """Padrões que indicam redundância."""
        return [
            {
                "pattern": r"dashboard|painel|relatório",
                "implies_web": True,
                "excludes": ["tipo aplicação", "plataforma"],
            },
            {
                "pattern": r"gestão de \w+|gerenciar \w+",
                "implies_management": True,
                "excludes": ["funcionalidades principais"],
            },
            {
                "pattern": r"fintech|financeiro|investimento|banco",
                "implies_financial": True,
                "excludes": ["setor", "dados sensíveis", "compliance"],
            },
            {
                "pattern": r"loja|e-commerce|venda|produto",
                "implies_ecommerce": True,
                "excludes": ["finalidade", "tipo negócio"],
            },
        ]

    def filter_questions(
        self, questions: List[Question], intake_text: str, inference_result: InferenceResult
    ) -> Tuple[List[Question], List[FilterDecision]]:
        """
        Filtra lista de perguntas removendo redundantes.

        Args:
            questions: Lista de perguntas candidatas
            intake_text: Texto original de entrada
            inference_result: Resultado da análise de inferência

        Returns:
            Tupla com (perguntas_filtradas, decisões_de_filtro)
        """
        try:
            logger.info(f"Filtering {len(questions)} candidate questions")

            filtered_questions = []
            filter_decisions = []

            for question in questions:
                decision = self._evaluate_question(question, intake_text, inference_result)
                filter_decisions.append(decision)

                if not decision.should_exclude:
                    filtered_questions.append(question)
                else:
                    logger.debug(f"Filtered question {question.id}: {decision.explanation}")

            # Atualizar estatísticas
            self._update_stats(filter_decisions)

            logger.info(f"Filtered {len(questions) - len(filtered_questions)} redundant questions")
            logger.info(f"Remaining questions: {len(filtered_questions)}")

            return filtered_questions, filter_decisions

        except Exception as e:
            logger.error(f"Error in question filtering: {str(e)}")
            return questions, []  # Retornar todas as perguntas em caso de erro

    def _evaluate_question(
        self, question: Question, intake_text: str, inference_result: InferenceResult
    ) -> FilterDecision:
        """Avalia se uma pergunta específica deve ser filtrada."""

        self.filter_stats["total_evaluations"] += 1

        # 1. Verificar se está na lista de perguntas redundantes da inferência
        if question.id in inference_result.redundant_question_ids:
            return FilterDecision(
                question_id=question.id,
                should_exclude=True,
                reason=FilterReason.OBVIOUS_FROM_CONTEXT,
                explanation="Pergunta redundante identificada pela análise de contexto",
                confidence=0.9,
            )

        # 2. Verificar regras específicas do domínio
        domain_decision = self._check_domain_rules(question, inference_result)
        if domain_decision:
            return domain_decision

        # 3. Verificar implicações de keywords
        keyword_decision = self._check_keyword_implications(question, intake_text)
        if keyword_decision:
            return keyword_decision

        # 4. Verificar padrões de redundância
        pattern_decision = self._check_redundancy_patterns(question, intake_text)
        if pattern_decision:
            return pattern_decision

        # 5. Verificar redundância por similaridade semântica
        semantic_decision = self._check_semantic_redundancy(question, intake_text, inference_result)
        if semantic_decision:
            return semantic_decision

        # 6. Verificar valor agregado
        value_decision = self._check_value_addition(question, inference_result)
        if value_decision:
            return value_decision

        # Se chegou até aqui, a pergunta deve ser mantida
        return FilterDecision(
            question_id=question.id,
            should_exclude=False,
            reason=FilterReason.LOW_VALUE_ADD,  # Não usado neste caso
            explanation="Pergunta agrega valor e não é redundante",
            confidence=0.7,
        )

    def _check_domain_rules(
        self, question: Question, inference_result: InferenceResult
    ) -> Optional[FilterDecision]:
        """Verifica regras específicas do domínio detectado."""

        domain = inference_result.detected_domain
        if not domain or domain not in self.domain_exclusion_rules:
            return None

        domain_rules = self.domain_exclusion_rules[domain]
        question_text = question.text

        # Verificar implicações óbvias do domínio
        for obvious_question in domain_rules.get("obvious_implications", []):
            if self._questions_are_similar(question_text, obvious_question):
                return FilterDecision(
                    question_id=question.id,
                    should_exclude=True,
                    reason=FilterReason.DOMAIN_IMPLICATION,
                    explanation=f"Resposta óbvia para domínio {domain}: {obvious_question}",
                    confidence=0.85,
                    evidence=[f"Domínio detectado: {domain}"],
                )

        # Verificar redundância específica do domínio
        for redundant_question in domain_rules.get("domain_specific_redundant", []):
            if self._questions_are_similar(question_text, redundant_question):
                return FilterDecision(
                    question_id=question.id,
                    should_exclude=True,
                    reason=FilterReason.REDUNDANT_INFORMATION,
                    explanation=f"Informação já implícita no domínio {domain}",
                    confidence=0.8,
                    evidence=[f"Domínio: {domain}", f"Pergunta similar: {redundant_question}"],
                )

        return None

    def _check_keyword_implications(
        self, question: Question, intake_text: str
    ) -> Optional[FilterDecision]:
        """Verifica se keywords no texto tornam a pergunta redundante."""

        intake_lower = intake_text.lower()
        question_lower = question.text.lower()

        for keyword, implications in self.keyword_implications.items():
            if keyword in intake_lower:
                excludes = implications.get("excludes_questions", [])

                # Verificar se a pergunta deve ser excluída
                for exclude_pattern in excludes:
                    if exclude_pattern.lower() in question_lower:
                        return FilterDecision(
                            question_id=question.id,
                            should_exclude=True,
                            reason=FilterReason.ALREADY_DESCRIBED,
                            explanation=f"Informação já fornecida via keyword '{keyword}'",
                            confidence=0.75,
                            evidence=[
                                f"Keyword encontrada: {keyword}",
                                f"Padrão excluído: {exclude_pattern}",
                            ],
                        )

        return None

    def _check_redundancy_patterns(
        self, question: Question, intake_text: str
    ) -> Optional[FilterDecision]:
        """Verifica padrões que indicam redundância."""

        intake_lower = intake_text.lower()
        question_lower = question.text.lower()

        for pattern_config in self.redundancy_patterns:
            pattern = pattern_config["pattern"]

            if re.search(pattern, intake_lower, re.IGNORECASE):
                excludes = pattern_config.get("excludes", [])

                for exclude_pattern in excludes:
                    if exclude_pattern.lower() in question_lower:
                        return FilterDecision(
                            question_id=question.id,
                            should_exclude=True,
                            reason=FilterReason.REDUNDANT_INFORMATION,
                            explanation=f"Padrão '{pattern}' indica informação já fornecida",
                            confidence=0.7,
                            evidence=[f"Padrão encontrado: {pattern}"],
                        )

        return None

    def _check_semantic_redundancy(
        self, question: Question, intake_text: str, inference_result: InferenceResult
    ) -> Optional[FilterDecision]:
        """Verifica redundância semântica baseada nas informações inferidas."""

        # Verificar se a pergunta pede informação que já foi inferida com alta confiança
        for inferred_info in inference_result.inferred_info:
            if inferred_info.confidence in [
                InferenceConfidence.CERTAIN,
                InferenceConfidence.LIKELY,
            ]:
                # Mapear informações inferidas para possíveis perguntas
                question_mappings = {
                    "application_type": ["tipo", "aplicação", "plataforma"],
                    "primary_purpose": ["finalidade", "objetivo", "propósito"],
                    "handles_sensitive_data": ["dados sensíveis", "dados sigilosos"],
                    "target_audience": ["público", "usuários", "clientes"],
                    "business_model": ["modelo", "negócio", "b2b", "b2c"],
                }

                if inferred_info.key in question_mappings:
                    keywords = question_mappings[inferred_info.key]
                    question_lower = question.text.lower()

                    if any(kw in question_lower for kw in keywords):
                        confidence = (
                            0.9 if inferred_info.confidence == InferenceConfidence.CERTAIN else 0.75
                        )

                        return FilterDecision(
                            question_id=question.id,
                            should_exclude=True,
                            reason=FilterReason.OBVIOUS_FROM_CONTEXT,
                            explanation=f"Informação já inferida: {inferred_info.key} = {inferred_info.value}",
                            confidence=confidence,
                            evidence=[f"Informação inferida: {inferred_info.reasoning}"],
                        )

        return None

    def _check_value_addition(
        self, question: Question, inference_result: InferenceResult
    ) -> Optional[FilterDecision]:
        """Verifica se a pergunta adiciona valor dado o contexto atual."""

        # Se a pergunta está relacionada a áreas de foco, tem alto valor
        question_lower = question.text.lower()
        focus_areas = [area.lower() for area in inference_result.focus_areas]

        # Se a pergunta está relacionada a uma área de foco, mantê-la
        for focus_area in focus_areas:
            if any(word in question_lower for word in focus_area.split()):
                return None  # Não filtrar

        # Verificar se a pergunta é muito genérica
        generic_patterns = [
            r"descreva.*aplicação",
            r"que tipo de.*sistema",
            r"qual.*finalidade",
            r"como.*funciona",
        ]

        for pattern in generic_patterns:
            if re.search(pattern, question_lower, re.IGNORECASE):
                # Só filtrar se temos informações suficientes
                if len(inference_result.inferred_info) >= 3:
                    return FilterDecision(
                        question_id=question.id,
                        should_exclude=True,
                        reason=FilterReason.LOW_VALUE_ADD,
                        explanation="Pergunta muito genérica com contexto já rico",
                        confidence=0.6,
                        evidence=[f"Padrão genérico: {pattern}"],
                    )

        return None

    def _questions_are_similar(self, question1: str, question2: str) -> bool:
        """Verifica se duas perguntas são semanticamente similares."""

        # Normalizar textos
        q1_words = set(re.findall(r"\w+", question1.lower()))
        q2_words = set(re.findall(r"\w+", question2.lower()))

        # Remover stop words comuns
        stop_words = {
            "o",
            "a",
            "os",
            "as",
            "do",
            "da",
            "dos",
            "das",
            "é",
            "são",
            "que",
            "qual",
            "como",
            "de",
            "para",
        }
        q1_words -= stop_words
        q2_words -= stop_words

        if not q1_words or not q2_words:
            return False

        # Calcular similaridade Jaccard
        intersection = q1_words.intersection(q2_words)
        union = q1_words.union(q2_words)

        similarity = len(intersection) / len(union)
        return similarity > 0.5

    def _update_stats(self, filter_decisions: List[FilterDecision]):
        """Atualiza estatísticas do filtro."""
        filtered_count = len([d for d in filter_decisions if d.should_exclude])
        self.filter_stats["questions_filtered"] += filtered_count

        # Contar por razão
        for decision in filter_decisions:
            if decision.should_exclude:
                reason = decision.reason.value
                self.filter_stats["filter_reasons"][reason] = (
                    self.filter_stats["filter_reasons"].get(reason, 0) + 1
                )

    def get_filter_explanation(self, filter_decisions: List[FilterDecision]) -> str:
        """Gera explicação detalhada das decisões de filtro."""

        filtered_decisions = [d for d in filter_decisions if d.should_exclude]

        if not filtered_decisions:
            return "✅ Nenhuma pergunta foi filtrada - todas agregam valor."

        explanation_parts = [f"🔄 **Filtradas {len(filtered_decisions)} perguntas redundantes:**\n"]

        # Agrupar por razão
        by_reason = {}
        for decision in filtered_decisions:
            reason = decision.reason.value
            if reason not in by_reason:
                by_reason[reason] = []
            by_reason[reason].append(decision)

        reason_labels = {
            "obvious_from_context": "📋 Óbvias pelo contexto",
            "already_described": "✍️ Já descritas",
            "domain_implication": "🏷️ Implícitas do domínio",
            "redundant_information": "🔄 Informação redundante",
            "low_value_add": "⚖️ Baixo valor agregado",
        }

        for reason, decisions in by_reason.items():
            label = reason_labels.get(reason, reason)
            explanation_parts.append(f"**{label}**: {len(decisions)} perguntas")

            for decision in decisions[:2]:  # Mostrar até 2 exemplos
                explanation_parts.append(f"  • {decision.explanation}")

            if len(decisions) > 2:
                explanation_parts.append(f"  • ... e mais {len(decisions) - 2}")

            explanation_parts.append("")

        return "\n".join(explanation_parts)

    def get_filter_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do filtro."""
        total_evaluations = self.filter_stats["total_evaluations"]
        filtered_count = self.filter_stats["questions_filtered"]

        return {
            **self.filter_stats,
            "filter_rate": filtered_count / total_evaluations if total_evaluations > 0 else 0,
            "supported_domains": list(self.domain_exclusion_rules.keys()),
            "total_keyword_patterns": len(self.keyword_implications),
            "total_redundancy_patterns": len(self.redundancy_patterns),
        }

    def add_custom_exclusion_rule(self, domain: str, rule_type: str, patterns: List[str]):
        """Adiciona regra de exclusão customizada."""
        if domain not in self.domain_exclusion_rules:
            self.domain_exclusion_rules[domain] = {
                "obvious_implications": [],
                "domain_specific_redundant": [],
            }

        if rule_type in self.domain_exclusion_rules[domain]:
            self.domain_exclusion_rules[domain][rule_type].extend(patterns)

        logger.info(f"Added custom exclusion rule for domain {domain}: {len(patterns)} patterns")

    def reset_stats(self):
        """Reseta estatísticas do filtro."""
        self.filter_stats = {"total_evaluations": 0, "questions_filtered": 0, "filter_reasons": {}}
