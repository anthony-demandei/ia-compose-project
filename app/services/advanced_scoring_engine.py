"""
Advanced scoring engine for intelligent question selection.
Implements sophisticated scoring algorithms with multi-agent consensus.
"""

import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor
import yaml

from app.models.intake import Question
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


class ScoringCriteria(Enum):
    """Critérios de pontuação para seleção de perguntas."""

    BUSINESS_VALUE = "business_value"
    TECHNICAL_COMPLEXITY = "technical_complexity"
    USER_IMPACT = "user_impact"
    STRATEGIC_ALIGNMENT = "strategic_alignment"
    RESOURCE_REQUIREMENTS = "resource_requirements"
    COMPLIANCE_RELEVANCE = "compliance_relevance"
    INDUSTRY_SPECIFICITY = "industry_specificity"
    RISK_MITIGATION = "risk_mitigation"


@dataclass
class ScoringWeights:
    """Pesos configuráveis para diferentes critérios de pontuação."""

    business_value: float = 0.25
    technical_complexity: float = 0.15
    user_impact: float = 0.20
    strategic_alignment: float = 0.15
    resource_requirements: float = 0.10
    compliance_relevance: float = 0.10
    industry_specificity: float = 0.03
    risk_mitigation: float = 0.02

    def __post_init__(self):
        """Valida que os pesos somam 1.0."""
        total = sum(self.__dict__.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Pesos devem somar 1.0, atual: {total}")


@dataclass
class QuestionScore:
    """Pontuação detalhada de uma pergunta."""

    question_id: str
    total_score: float
    criteria_scores: Dict[str, float] = field(default_factory=dict)
    agent_votes: Dict[str, float] = field(default_factory=dict)
    similarity_score: float = 0.0
    tag_bonus: float = 0.0
    weight_factor: float = 0.0
    complexity_modifier: float = 1.0
    confidence: float = 0.0
    reasoning: List[str] = field(default_factory=list)


@dataclass
class ScoringContext:
    """Contexto para algoritmo de pontuação."""

    intake_text: str
    classified_tags: List[str] = field(default_factory=list)
    detected_industry: Optional[str] = None
    compliance_requirements: List[str] = field(default_factory=list)
    project_complexity: str = "medium"  # low, medium, high
    budget_range: Optional[str] = None
    timeline_constraint: Optional[str] = None
    user_count_estimate: Optional[int] = None
    existing_systems: List[str] = field(default_factory=list)


class AdvancedScoringEngine:
    """
    Motor de pontuação avançado para seleção inteligente de perguntas.

    Implementa múltiplos algoritmos de pontuação e consenso multi-agent.
    """

    def __init__(
        self,
        catalog_path: str = "app/data/question_catalog_v2.yaml",
        weights: Optional[ScoringWeights] = None,
        enable_multi_agent: bool = True,
    ):
        """
        Inicializa o motor de pontuação avançado.

        Args:
            catalog_path: Caminho para catálogo de perguntas
            weights: Pesos personalizados para critérios
            enable_multi_agent: Habilita consenso multi-agent
        """
        self.catalog_path = catalog_path
        self.weights = weights or ScoringWeights()
        self.enable_multi_agent = enable_multi_agent
        self.catalog: List[Question] = []
        self.scoring_matrix = {}
        self.validation_rules = []

        # Thread pool for parallel scoring
        self.executor = ThreadPoolExecutor(max_workers=4)

        # Agent scoring methods
        self.agent_scorers = {
            "business_analyst": self._score_business_relevance,
            "technical_architect": self._score_technical_importance,
            "compliance_expert": self._score_compliance_relevance,
            "industry_expert": self._score_industry_specificity,
            "performance_engineer": self._score_performance_impact,
        }

        self._load_catalog()
        logger.info("Advanced scoring engine initialized")

    def _load_catalog(self):
        """Carrega catálogo de perguntas e configurações."""
        try:
            with open(self.catalog_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            # Carregar perguntas
            self.catalog = []
            for q_data in data.get("catalog", []):
                question = Question(**q_data)
                self.catalog.append(question)

            # Carregar matriz de pontuação
            self.scoring_matrix = data.get("scoring_matrix", {})

            # Carregar regras de validação
            self.validation_rules = data.get("validation_rules", [])

            logger.info(f"Carregado catálogo com {len(self.catalog)} perguntas")

        except Exception as e:
            logger.error(f"Erro ao carregar catálogo: {str(e)}")
            raise

    async def score_questions(
        self, context: ScoringContext, embeddings: Optional[Dict[str, np.ndarray]] = None
    ) -> List[QuestionScore]:
        """
        Pontuação avançada de perguntas baseada em contexto e embeddings.

        Args:
            context: Contexto de pontuação com informações do intake
            embeddings: Embeddings pré-calculados das perguntas

        Returns:
            Lista de QuestionScore ordenada por pontuação total
        """
        try:
            logger.info("Iniciando pontuação avançada de perguntas")

            # 1. Calcular pontuações base
            base_scores = await self._calculate_base_scores(context, embeddings)

            # 2. Aplicar consenso multi-agent (se habilitado)
            if self.enable_multi_agent:
                agent_scores = await self._apply_multi_agent_consensus(context, base_scores)
                final_scores = self._merge_agent_scores(base_scores, agent_scores)
            else:
                final_scores = base_scores

            # 3. Aplicar modificadores de complexidade
            final_scores = self._apply_complexity_modifiers(final_scores, context)

            # 4. Aplicar normalização e diversidade
            final_scores = self._apply_diversity_constraints(final_scores)

            # 5. Validar e ordenar
            validated_scores = self._validate_scores(final_scores, context)

            return sorted(validated_scores, key=lambda x: x.total_score, reverse=True)

        except Exception as e:
            logger.error(f"Erro na pontuação: {str(e)}")
            return []

    async def _calculate_base_scores(
        self, context: ScoringContext, embeddings: Optional[Dict[str, np.ndarray]]
    ) -> List[QuestionScore]:
        """Calcula pontuações base para todas as perguntas."""
        scores = []

        # Parallel scoring for performance
        tasks = []
        for question in self.catalog:
            task = asyncio.create_task(self._score_single_question(question, context, embeddings))
            tasks.append(task)

        # Wait for all scoring tasks
        question_scores = await asyncio.gather(*tasks)

        return question_scores

    async def _score_single_question(
        self,
        question: Question,
        context: ScoringContext,
        embeddings: Optional[Dict[str, np.ndarray]],
    ) -> QuestionScore:
        """Pontuação detalhada de uma pergunta individual."""
        score = QuestionScore(question_id=question.id, total_score=0.0)

        try:
            # 1. Similarity score (embedding-based)
            if embeddings and question.id in embeddings:
                score.similarity_score = self._calculate_similarity_score(
                    question, context, embeddings
                )

            # 2. Tag bonus
            score.tag_bonus = self._calculate_tag_bonus(question, context)

            # 3. Weight factor
            score.weight_factor = question.weight / 10.0  # Normalizar peso

            # 4. Critérios específicos
            criteria_scores = {}

            # Business value
            criteria_scores[ScoringCriteria.BUSINESS_VALUE.value] = self._score_business_value(
                question, context
            )

            # Technical complexity
            criteria_scores[
                ScoringCriteria.TECHNICAL_COMPLEXITY.value
            ] = self._score_technical_complexity(question, context)

            # User impact
            criteria_scores[ScoringCriteria.USER_IMPACT.value] = self._score_user_impact(
                question, context
            )

            # Strategic alignment
            criteria_scores[
                ScoringCriteria.STRATEGIC_ALIGNMENT.value
            ] = self._score_strategic_alignment(question, context)

            # Resource requirements
            criteria_scores[
                ScoringCriteria.RESOURCE_REQUIREMENTS.value
            ] = self._score_resource_requirements(question, context)

            # Compliance relevance
            criteria_scores[
                ScoringCriteria.COMPLIANCE_RELEVANCE.value
            ] = self._score_compliance_relevance(question, context)

            # Industry specificity
            criteria_scores[
                ScoringCriteria.INDUSTRY_SPECIFICITY.value
            ] = self._score_industry_specificity(question, context)

            # Risk mitigation
            criteria_scores[ScoringCriteria.RISK_MITIGATION.value] = self._score_risk_mitigation(
                question, context
            )

            score.criteria_scores = criteria_scores

            # 5. Calcular pontuação total ponderada
            weighted_score = 0.0
            for criterion, value in criteria_scores.items():
                weight = getattr(self.weights, criterion, 0.0)
                weighted_score += value * weight

            # Aplicar componentes adicionais
            score.total_score = (
                weighted_score * 0.6
                + score.similarity_score * 0.25  # 60% critérios específicos
                + score.tag_bonus * 0.10  # 25% similaridade
                + score.weight_factor * 0.05  # 10% tag bonus  # 5% peso da pergunta
            )

            # Garantir score entre 0 e 1
            score.total_score = max(0.0, min(1.0, score.total_score))

            # Calcular confiança
            score.confidence = self._calculate_confidence(score)

            # Reasoning
            score.reasoning = self._generate_reasoning(question, score, context)

        except Exception as e:
            logger.error(f"Erro ao pontuar pergunta {question.id}: {str(e)}")
            score.total_score = 0.0

        return score

    def _calculate_similarity_score(
        self, question: Question, context: ScoringContext, embeddings: Dict[str, np.ndarray]
    ) -> float:
        """Calcula score de similaridade usando embeddings."""
        # Implementação simplificada - na prática usaria embeddings reais
        # Por ora, usar similaridade textual básica
        intake_text = context.intake_text.lower()
        question_text = question.text.lower()

        # Contagem de palavras em comum (substituir por embedding similarity)
        intake_words = set(intake_text.split())
        question_words = set(question_text.split())

        if not intake_words or not question_words:
            return 0.0

        common_words = intake_words.intersection(question_words)
        similarity = len(common_words) / max(len(intake_words), len(question_words))

        return min(1.0, similarity * 2.0)  # Amplificar similaridade

    def _calculate_tag_bonus(self, question: Question, context: ScoringContext) -> float:
        """Calcula bônus baseado em tags classificadas."""
        if not question.tags or not context.classified_tags:
            return 0.0

        matching_tags = set(question.tags).intersection(set(context.classified_tags))
        return len(matching_tags) / len(question.tags) * 0.3  # Máximo 30% bonus

    def _score_business_value(self, question: Question, context: ScoringContext) -> float:
        """Pontua valor de negócio da pergunta."""
        business_keywords = [
            "objetivo",
            "roi",
            "receita",
            "custo",
            "eficiência",
            "competitiv",
            "estratégi",
            "stakeholder",
        ]

        score = 0.0
        question_text = question.text.lower()

        for keyword in business_keywords:
            if keyword in question_text:
                score += 0.15

        # Bonus para perguntas de negócio
        if question.stage == "business":
            score += 0.2

        # Bonus para perguntas críticas
        if hasattr(question, "required") and question.required:
            score += 0.1

        return min(1.0, score)

    def _score_technical_complexity(self, question: Question, context: ScoringContext) -> float:
        """Pontua complexidade técnica relevante."""
        technical_keywords = [
            "arquitetura",
            "tecnolog",
            "integração",
            "api",
            "database",
            "infraestrutura",
            "deployment",
            "escalabilidade",
        ]

        score = 0.0
        question_text = question.text.lower()

        for keyword in technical_keywords:
            if keyword in question_text:
                score += 0.12

        # Ajuste baseado em complexidade do projeto
        if context.project_complexity == "high":
            score *= 1.3
        elif context.project_complexity == "low":
            score *= 0.7

        # Bonus para perguntas técnicas
        if question.stage == "technical":
            score += 0.2

        return min(1.0, score)

    def _score_user_impact(self, question: Question, context: ScoringContext) -> float:
        """Pontua impacto no usuário final."""
        user_keywords = [
            "usuário",
            "interface",
            "experiência",
            "usabilidade",
            "acessibilidade",
            "performance",
            "responsiv",
        ]

        score = 0.0
        question_text = question.text.lower()

        for keyword in user_keywords:
            if keyword in question_text:
                score += 0.15

        # Ajuste baseado em número de usuários
        if context.user_count_estimate:
            if context.user_count_estimate > 10000:
                score *= 1.4
            elif context.user_count_estimate > 1000:
                score *= 1.2

        # Bonus para perguntas funcionais
        if question.stage == "functional":
            score += 0.15

        return min(1.0, score)

    def _score_strategic_alignment(self, question: Question, context: ScoringContext) -> float:
        """Pontua alinhamento estratégico."""
        strategic_tags = ["strategic", "critical", "core-business", "competitive"]

        score = 0.0

        if question.tags:
            matching_strategic = set(question.tags).intersection(set(strategic_tags))
            score += len(matching_strategic) * 0.25

        # Bonus baseado no peso da pergunta
        score += (question.weight / 10.0) * 0.3

        return min(1.0, score)

    def _score_resource_requirements(self, question: Question, context: ScoringContext) -> float:
        """Pontua relevância baseada em recursos disponíveis."""
        resource_keywords = ["orçamento", "prazo", "equipe", "tempo", "cronograma"]

        score = 0.0
        question_text = question.text.lower()

        for keyword in resource_keywords:
            if keyword in question_text:
                score += 0.2

        # Ajuste baseado em orçamento
        if context.budget_range:
            if "under_50k" in context.budget_range:
                # Priorizar perguntas essenciais
                if question.required:
                    score += 0.3
            elif "over_5m" in context.budget_range:
                # Incluir mais perguntas detalhadas
                score += 0.2

        return min(1.0, score)

    def _score_compliance_relevance(self, question: Question, context: ScoringContext) -> float:
        """Pontua relevância de compliance."""
        compliance_keywords = ["lgpd", "gdpr", "segurança", "privacidade", "audit"]

        score = 0.0
        question_text = question.text.lower()

        for keyword in compliance_keywords:
            if keyword in question_text:
                score += 0.2

        # Bonus se compliance foi detectado no contexto
        if context.compliance_requirements:
            score += 0.3

        # Bonus para tags de compliance
        if question.tags and any("compliance" in tag or "security" in tag for tag in question.tags):
            score += 0.2

        return min(1.0, score)

    def _score_industry_specificity(self, question: Question, context: ScoringContext) -> float:
        """Pontua especificidade da indústria."""
        if not context.detected_industry:
            return 0.0

        industry_map = {
            "healthcare": ["saúde", "hipaa", "paciente", "médico"],
            "finance": ["financeiro", "pagamento", "sox", "pci"],
            "ecommerce": ["e-commerce", "produto", "carrinho", "checkout"],
        }

        score = 0.0
        industry_keywords = industry_map.get(context.detected_industry, [])
        question_text = question.text.lower()

        for keyword in industry_keywords:
            if keyword in question_text:
                score += 0.3

        return min(1.0, score)

    def _score_risk_mitigation(self, question: Question, context: ScoringContext) -> float:
        """Pontua capacidade de mitigação de riscos."""
        risk_keywords = ["risco", "backup", "disaster", "recovery", "monitoring"]

        score = 0.0
        question_text = question.text.lower()

        for keyword in risk_keywords:
            if keyword in question_text:
                score += 0.25

        # Bonus para NFRs que mitigam riscos
        if question.stage == "nfr":
            score += 0.15

        return min(1.0, score)

    async def _apply_multi_agent_consensus(
        self, context: ScoringContext, base_scores: List[QuestionScore]
    ) -> Dict[str, List[float]]:
        """Aplica consenso multi-agent às pontuações."""
        agent_scores = {}

        # Executar scoring de cada agent em paralelo
        tasks = []
        for agent_name, scorer_func in self.agent_scorers.items():
            task = asyncio.create_task(
                self._run_agent_scorer(agent_name, scorer_func, context, base_scores)
            )
            tasks.append((agent_name, task))

        # Coletar resultados
        for agent_name, task in tasks:
            try:
                scores = await task
                agent_scores[agent_name] = scores
            except Exception as e:
                logger.error(f"Erro no agent {agent_name}: {str(e)}")
                agent_scores[agent_name] = [0.0] * len(base_scores)

        return agent_scores

    async def _run_agent_scorer(
        self,
        agent_name: str,
        scorer_func,
        context: ScoringContext,
        base_scores: List[QuestionScore],
    ) -> List[float]:
        """Executa scorer de um agent específico."""
        scores = []

        for base_score in base_scores:
            question = next((q for q in self.catalog if q.id == base_score.question_id), None)
            if question:
                agent_score = scorer_func(question, context)
                scores.append(agent_score)
            else:
                scores.append(0.0)

        return scores

    def _score_business_relevance(self, question: Question, context: ScoringContext) -> float:
        """Scoring específico do Business Analyst Agent."""
        # Implementação do agent de negócios
        return self._score_business_value(question, context) * 1.2

    def _score_technical_importance(self, question: Question, context: ScoringContext) -> float:
        """Scoring específico do Technical Architect Agent."""
        # Implementação do agent técnico
        return self._score_technical_complexity(question, context) * 1.3

    def _score_compliance_relevance(self, question: Question, context: ScoringContext) -> float:
        """Scoring específico do Compliance Expert Agent."""
        # Implementação do agent de compliance
        return self._score_compliance_relevance(question, context) * 1.5

    def _score_industry_specificity(self, question: Question, context: ScoringContext) -> float:
        """Scoring específico do Industry Expert Agent."""
        # Implementação do agent de indústria
        return self._score_industry_specificity(question, context) * 1.4

    def _score_performance_impact(self, question: Question, context: ScoringContext) -> float:
        """Scoring específico do Performance Engineer Agent."""
        # Implementação do agent de performance
        nfr_score = 0.0
        if question.stage == "nfr":
            nfr_score = 0.5

        performance_keywords = ["performance", "latência", "throughput", "escalabilidade"]
        question_text = question.text.lower()

        for keyword in performance_keywords:
            if keyword in question_text:
                nfr_score += 0.2

        return min(1.0, nfr_score)

    def _merge_agent_scores(
        self, base_scores: List[QuestionScore], agent_scores: Dict[str, List[float]]
    ) -> List[QuestionScore]:
        """Combina pontuações base com consenso dos agents."""
        merged_scores = []

        for i, base_score in enumerate(base_scores):
            # Coletar votos dos agents
            agent_votes = {}
            for agent_name, scores in agent_scores.items():
                if i < len(scores):
                    agent_votes[agent_name] = scores[i]

            # Calcular consenso (média ponderada)
            if agent_votes:
                consensus_score = np.mean(list(agent_votes.values()))
                # Combinar com score base (70% base + 30% consenso)
                final_score = base_score.total_score * 0.7 + consensus_score * 0.3
            else:
                final_score = base_score.total_score

            # Atualizar score
            base_score.total_score = final_score
            base_score.agent_votes = agent_votes
            merged_scores.append(base_score)

        return merged_scores

    def _apply_complexity_modifiers(
        self, scores: List[QuestionScore], context: ScoringContext
    ) -> List[QuestionScore]:
        """Aplica modificadores baseados na matriz de complexidade."""
        complexity_factors = self.scoring_matrix.get("complexity_factors", [])

        for score in scores:
            question = next((q for q in self.catalog if q.id == score.question_id), None)
            if not question:
                continue

            modifier = 1.0

            # Aplicar modificadores configurados
            for factor in complexity_factors:
                if self._check_complexity_condition(factor, question, context):
                    modifier *= factor.get("weight_modifier", 1.0)

            score.complexity_modifier = modifier
            score.total_score *= modifier

            # Garantir limite
            score.total_score = min(1.0, score.total_score)

        return scores

    def _check_complexity_condition(
        self, factor: Dict[str, Any], question: Question, context: ScoringContext
    ) -> bool:
        """Verifica se condição de complexidade se aplica."""
        condition = factor.get("condition", {})

        # Exemplo de implementação
        field = condition.get("field")
        if field == "integration_complexity":
            return len(context.existing_systems) > 2
        elif field == "scale_complexity":
            return context.user_count_estimate and context.user_count_estimate > 50000
        elif field == "compliance_complexity":
            return len(context.compliance_requirements) >= 2

        return False

    def _apply_diversity_constraints(self, scores: List[QuestionScore]) -> List[QuestionScore]:
        """Aplica constraints de diversidade para garantir cobertura balanceada."""
        # Agrupar por estágio
        stage_groups = {}
        for score in scores:
            question = next((q for q in self.catalog if q.id == score.question_id), None)
            if question:
                stage = question.stage
                if stage not in stage_groups:
                    stage_groups[stage] = []
                stage_groups[stage].append(score)

        # Aplicar boost para diversidade
        for stage, stage_scores in stage_groups.items():
            if len(stage_scores) < 3:  # Se poucos no estágio, boost
                for score in stage_scores:
                    score.total_score *= 1.1

        return scores

    def _validate_scores(
        self, scores: List[QuestionScore], context: ScoringContext
    ) -> List[QuestionScore]:
        """Valida pontuações contra regras de validação."""
        validated_scores = []

        for score in scores:
            # Validar regras configuradas
            is_valid = True
            for rule in self.validation_rules:
                if not self._validate_rule(rule, score, context):
                    is_valid = False
                    break

            if is_valid:
                validated_scores.append(score)
            else:
                # Penalizar score inválido
                score.total_score *= 0.5
                validated_scores.append(score)

        return validated_scores

    def _validate_rule(
        self, rule: Dict[str, Any], score: QuestionScore, context: ScoringContext
    ) -> bool:
        """Valida uma regra específica."""
        rule_type = rule.get("rule_type")

        if rule_type == "dependency_check":
            # Implementar validação de dependências
            return True
        elif rule_type == "consistency_check":
            # Implementar validação de consistência
            return True
        elif rule_type == "completeness_check":
            # Implementar validação de completude
            return True

        return True

    def _calculate_confidence(self, score: QuestionScore) -> float:
        """Calcula confiança na pontuação."""
        confidence = 0.5  # Base confidence

        # Aumentar confiança baseado em evidências
        if score.similarity_score > 0.3:
            confidence += 0.2

        if score.tag_bonus > 0.1:
            confidence += 0.15

        if score.agent_votes and len(score.agent_votes) >= 3:
            # Alta concordância entre agents aumenta confiança
            votes = list(score.agent_votes.values())
            std_dev = np.std(votes)
            if std_dev < 0.2:  # Baixa dispersão = alta concordância
                confidence += 0.15

        return min(1.0, confidence)

    def _generate_reasoning(
        self, question: Question, score: QuestionScore, context: ScoringContext
    ) -> List[str]:
        """Gera explicação do reasoning da pontuação."""
        reasoning = []

        # Similaridade
        if score.similarity_score > 0.3:
            reasoning.append(
                f"Alta similaridade com texto de intake ({score.similarity_score:.2f})"
            )

        # Tags
        if score.tag_bonus > 0:
            reasoning.append(f"Bonus por tags relevantes ({score.tag_bonus:.2f})")

        # Peso da pergunta
        if score.weight_factor > 0.5:
            reasoning.append(f"Pergunta de alta importância (peso {question.weight})")

        # Consenso de agents
        if score.agent_votes:
            avg_vote = np.mean(list(score.agent_votes.values()))
            if avg_vote > 0.7:
                reasoning.append(f"Alto consenso entre agents ({avg_vote:.2f})")

        # Stage relevante
        stage_bonus = score.criteria_scores.get(f"{question.stage}_relevance", 0)
        if stage_bonus > 0.5:
            reasoning.append(f"Alta relevância para estágio {question.stage}")

        return reasoning

    def get_scoring_stats(self, scores: List[QuestionScore]) -> Dict[str, Any]:
        """Retorna estatísticas das pontuações."""
        if not scores:
            return {}

        total_scores = [s.total_score for s in scores]

        return {
            "total_questions": len(scores),
            "avg_score": np.mean(total_scores),
            "std_score": np.std(total_scores),
            "min_score": np.min(total_scores),
            "max_score": np.max(total_scores),
            "high_confidence_count": len([s for s in scores if s.confidence > 0.8]),
            "agent_consensus_count": len([s for s in scores if len(s.agent_votes) >= 3]),
            "stage_distribution": self._get_stage_distribution(scores),
        }

    def _get_stage_distribution(self, scores: List[QuestionScore]) -> Dict[str, int]:
        """Retorna distribuição por estágio."""
        distribution = {}

        for score in scores:
            question = next((q for q in self.catalog if q.id == score.question_id), None)
            if question:
                stage = question.stage
                distribution[stage] = distribution.get(stage, 0) + 1

        return distribution

    async def explain_selection(
        self, selected_scores: List[QuestionScore], context: ScoringContext
    ) -> Dict[str, Any]:
        """Gera explicação detalhada da seleção."""
        explanation = {
            "selection_criteria": {
                "weights_used": self.weights.__dict__,
                "multi_agent_enabled": self.enable_multi_agent,
                "total_evaluated": len(self.catalog),
                "selected_count": len(selected_scores),
            },
            "top_questions": [],
            "reasoning_summary": [],
            "confidence_analysis": {},
            "stage_coverage": self._get_stage_distribution(selected_scores),
        }

        # Top 5 perguntas com detalhes
        for i, score in enumerate(selected_scores[:5]):
            question = next((q for q in self.catalog if q.id == score.question_id), None)
            if question:
                explanation["top_questions"].append(
                    {
                        "rank": i + 1,
                        "question_id": score.question_id,
                        "question_text": question.text,
                        "total_score": score.total_score,
                        "confidence": score.confidence,
                        "reasoning": score.reasoning,
                        "agent_votes": score.agent_votes,
                    }
                )

        # Resumo do reasoning
        all_reasoning = []
        for score in selected_scores:
            all_reasoning.extend(score.reasoning)

        # Contar reasoning mais comuns
        from collections import Counter

        reasoning_counts = Counter(all_reasoning)
        explanation["reasoning_summary"] = list(reasoning_counts.most_common(5))

        # Análise de confiança
        confidences = [s.confidence for s in selected_scores]
        explanation["confidence_analysis"] = {
            "avg_confidence": np.mean(confidences),
            "high_confidence_count": len([c for c in confidences if c > 0.8]),
            "low_confidence_count": len([c for c in confidences if c < 0.5]),
        }

        return explanation
