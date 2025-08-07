"""
Dynamic Multi-Agent Selector - Integra perguntas dinâmicas com validação multi-agent.
Combina o melhor dos dois mundos: geração dinâmica + validação especializada.
"""

from typing import List, Dict, Any
from dataclasses import dataclass

from app.models.intake import Question
from app.services.multi_agent_question_selector import MultiAgentQuestionSelector
from app.services.dynamic_question_generator import (
    DynamicQuestionGenerator,
    GenerationContext,
)
from app.services.briefing_completeness_analyzer import CompletenessResult
from app.services.advanced_scoring_engine import ScoringContext
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


@dataclass
class HybridSelectionResult:
    """Resultado da seleção híbrida (dinâmica + multi-agent)."""

    questions: List[Question]
    dynamic_count: int
    catalog_count: int
    agent_validation_score: float
    selection_metadata: Dict[str, Any]


class DynamicMultiAgentSelector:
    """
    Seletor híbrido que combina geração dinâmica com validação multi-agent.

    Fluxo:
    1. Analisa completude do briefing
    2. Gera perguntas dinâmicas para lacunas
    3. Valida com agents especializados
    4. Combina com catálogo se necessário
    5. Retorna conjunto otimizado de perguntas
    """

    def __init__(
        self,
        multi_agent_selector: MultiAgentQuestionSelector,
        dynamic_generator: DynamicQuestionGenerator,
    ):
        """
        Inicializa o seletor híbrido.

        Args:
            multi_agent_selector: Seletor multi-agent existente
            dynamic_generator: Gerador de perguntas dinâmicas
        """
        self.multi_agent_selector = multi_agent_selector
        self.dynamic_generator = dynamic_generator

        logger.info("DynamicMultiAgentSelector initialized")

    async def select_questions_hybrid(
        self, intake_text: str, completeness_result: CompletenessResult, max_questions: int = 10
    ) -> HybridSelectionResult:
        """
        Seleciona perguntas usando abordagem híbrida.

        Args:
            intake_text: Texto do briefing
            completeness_result: Resultado da análise de completude
            max_questions: Máximo de perguntas a retornar

        Returns:
            HybridSelectionResult com perguntas validadas
        """
        try:
            logger.info(
                f"Starting hybrid selection (completeness: {completeness_result.overall_score:.1f}%)"
            )

            # 1. Gerar perguntas dinâmicas baseadas nas lacunas
            generation_context = GenerationContext(
                briefing_text=intake_text,
                completeness_result=completeness_result,
                missing_areas=completeness_result.missing_critical_areas,
                max_questions=min(
                    max_questions, len(completeness_result.missing_critical_areas) * 2
                ),
                focus_technical=True,
            )

            dynamic_questions = await self.dynamic_generator.generate_questions(generation_context)
            logger.info(f"Generated {len(dynamic_questions)} dynamic questions")

            # 2. Converter para formato padrão
            standard_dynamic = self.dynamic_generator.convert_to_standard_questions(
                dynamic_questions
            )

            # 3. Validar com agents especializados
            validated_questions = await self._validate_with_agents(standard_dynamic, intake_text)

            # 4. Se não tiver perguntas suficientes, complementar com catálogo
            final_questions = validated_questions
            catalog_additions = []

            if len(final_questions) < max_questions // 2:  # Menos da metade do desejado
                logger.info("Insufficient dynamic questions, adding from catalog...")

                # Usar seletor multi-agent tradicional para complementar
                scoring_context = ScoringContext(
                    intake_text=intake_text, classified_tags=[], project_complexity="medium"
                )

                catalog_result = await self.multi_agent_selector.select_questions(
                    intake_text, scoring_context, None
                )

                # Adicionar perguntas do catálogo que não conflitam
                catalog_questions = self._get_catalog_questions(catalog_result.selected_questions)

                for cat_q in catalog_questions:
                    if not self._is_duplicate(cat_q, final_questions):
                        catalog_additions.append(cat_q)
                        if len(final_questions) + len(catalog_additions) >= max_questions:
                            break

                final_questions.extend(catalog_additions)

            # 5. Ordenar por prioridade
            final_questions.sort(
                key=lambda q: q.priority if hasattr(q, "priority") else 5, reverse=True
            )

            # 6. Limitar ao máximo
            final_questions = final_questions[:max_questions]

            # 7. Calcular métricas
            agent_score = await self._calculate_agent_validation_score(final_questions, intake_text)

            return HybridSelectionResult(
                questions=final_questions,
                dynamic_count=len(validated_questions),
                catalog_count=len(catalog_additions),
                agent_validation_score=agent_score,
                selection_metadata={
                    "completeness_score": completeness_result.overall_score,
                    "missing_areas": completeness_result.missing_critical_areas,
                    "dynamic_generated": len(dynamic_questions),
                    "dynamic_validated": len(validated_questions),
                    "catalog_added": len(catalog_additions),
                    "total_selected": len(final_questions),
                },
            )

        except Exception as e:
            logger.error(f"Error in hybrid selection: {str(e)}")
            # Fallback para seleção tradicional
            return await self._fallback_selection(intake_text, max_questions)

    async def _validate_with_agents(
        self, questions: List[Question], intake_text: str
    ) -> List[Question]:
        """Valida perguntas dinâmicas com agents especializados."""
        validated = []

        for question in questions:
            # Simular validação com agents
            # Em produção, isso consultaria cada agent especializado
            validation_score = await self._simulate_agent_validation(question, intake_text)

            if validation_score > 0.6:  # Threshold de validação
                validated.append(question)
                logger.debug(
                    f"Question validated: {question.text[:50]}... (score: {validation_score:.2f})"
                )
            else:
                logger.debug(
                    f"Question rejected: {question.text[:50]}... (score: {validation_score:.2f})"
                )

        return validated

    async def _simulate_agent_validation(self, question: Question, intake_text: str) -> float:
        """
        Simula validação de uma pergunta pelos agents.
        Em produção, consultaria os 5 agents especializados.
        """
        # Por ora, usar heurísticas simples
        score = 0.7  # Base score

        # Aumentar score se pergunta é específica ao contexto
        if any(word in question.text.lower() for word in intake_text.lower().split()[:10]):
            score += 0.1

        # Aumentar score se tem opções (mais estruturada)
        if question.options and len(question.options) > 2:
            score += 0.1

        # Diminuir score se muito genérica
        generic_terms = ["projeto", "sistema", "aplicação", "software"]
        if any(term in question.text.lower() for term in generic_terms):
            score -= 0.1

        return min(1.0, max(0.0, score))

    def _get_catalog_questions(self, question_ids: List[str]) -> List[Question]:
        """Recupera perguntas do catálogo pelos IDs."""
        catalog_questions = []

        if hasattr(self.multi_agent_selector, "question_selector"):
            catalog = getattr(self.multi_agent_selector.question_selector, "catalog", [])
            for q_id in question_ids:
                question = next((q for q in catalog if q.id == q_id), None)
                if question:
                    catalog_questions.append(question)

        return catalog_questions

    def _is_duplicate(self, question: Question, existing: List[Question]) -> bool:
        """Verifica se uma pergunta é duplicada."""
        # Verificar por ID
        if any(q.id == question.id for q in existing):
            return True

        # Verificar por texto similar (simplificado)
        question_lower = question.text.lower()
        for q in existing:
            if q.text.lower() == question_lower:
                return True

            # Verificar similaridade parcial
            q_words = set(q.text.lower().split())
            question_words = set(question_lower.split())
            overlap = len(q_words.intersection(question_words))

            if overlap > min(len(q_words), len(question_words)) * 0.7:
                return True

        return False

    async def _calculate_agent_validation_score(
        self, questions: List[Question], intake_text: str
    ) -> float:
        """Calcula score médio de validação dos agents."""
        if not questions:
            return 0.0

        total_score = 0.0
        for q in questions:
            score = await self._simulate_agent_validation(q, intake_text)
            total_score += score

        return total_score / len(questions)

    async def _fallback_selection(
        self, intake_text: str, max_questions: int
    ) -> HybridSelectionResult:
        """Fallback para seleção tradicional se houver erro."""
        logger.warning("Using fallback selection due to error")

        # Usar seletor multi-agent tradicional
        scoring_context = ScoringContext(
            intake_text=intake_text, classified_tags=[], project_complexity="medium"
        )

        result = await self.multi_agent_selector.select_questions(
            intake_text, scoring_context, None
        )

        catalog_questions = self._get_catalog_questions(result.selected_questions[:max_questions])

        return HybridSelectionResult(
            questions=catalog_questions,
            dynamic_count=0,
            catalog_count=len(catalog_questions),
            agent_validation_score=0.7,  # Score padrão
            selection_metadata={"fallback_used": True, "reason": "Error in dynamic generation"},
        )
