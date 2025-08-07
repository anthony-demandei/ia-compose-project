"""
Single Agent With Memory Service - Substitui o sistema multi-agent
por um agente único otimizado com memória persistente ZEP sanitizada.

Esta abordagem simplificada e segura:
- Usa um único agente de IA ao invés de múltiplos agentes
- Integra memória persistente com conhecimento técnico sanitizado
- Remove dados privados e armazena apenas padrões reutilizáveis
- Otimiza uso de tokens através de contexto histórico técnico
- Mantém alta precisão através do aprendizado arquitetural
- Garante compliance e privacidade de dados dos clientes
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from openai import AsyncOpenAI
from app.models.intake import Question
from app.services.zep_memory_service import ZepMemoryService, ContextualInsight
from app.services.universal_project_classifier import (
    UniversalProjectClassifier,
    ProjectClassification,
)
from app.services.dynamic_question_generator import DynamicQuestionGenerator, GenerationContext
from app.services.briefing_completeness_analyzer import BriefingCompletenessAnalyzer
from app.utils.config import get_settings
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


@dataclass
class IntelligentSelectionResult:
    """Resultado da seleção inteligente de perguntas."""

    selected_questions: List[Question]
    context_used: Optional[str]
    insights_applied: List[ContextualInsight]
    token_savings: int  # Tokens economizados através do contexto
    confidence_score: float
    reasoning: str


class SingleAgentWithMemoryService:
    """
    Serviço de agente único com memória persistente.

    Combina:
    - Classificação universal de projetos
    - Análise de completude inteligente
    - Geração dinâmica de perguntas
    - Contexto histórico do ZEP
    - Insights de projetos anteriores
    """

    def __init__(self, openai_api_key: str):
        """
        Inicializa o serviço de agente único.

        Args:
            openai_api_key: Chave da API OpenAI
        """
        settings = get_settings()

        # Componentes principais
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        self.memory_service = ZepMemoryService()
        self.project_classifier = UniversalProjectClassifier(api_key=openai_api_key)
        self.completeness_analyzer = BriefingCompletenessAnalyzer(
            api_key=openai_api_key, threshold=0.85
        )
        self.question_generator = DynamicQuestionGenerator(api_key=openai_api_key)

        # Configurações
        self.model = settings.openai_model
        self.temperature = 0.3  # Baixa para consistência
        self.max_questions = 8

        logger.info("SingleAgentWithMemoryService initialized")

    async def analyze_and_generate_questions(
        self, briefing_text: str, client_identifier: str = None, session_id: str = None
    ) -> IntelligentSelectionResult:
        """
        Análise inteligente e geração de perguntas usando memória histórica universal.

        Args:
            briefing_text: Descrição do projeto
            client_identifier: Identificador do cliente (opcional, para contexto)
            session_id: ID da sessão ZEP

        Returns:
            Resultado da seleção inteligente
        """
        try:
            logger.info("Starting intelligent question generation with memory context")

            # ETAPA 1: Recuperar contexto histórico relevante da memória universal
            historical_context = None
            contextual_insights = []

            if self.memory_service.is_enabled:
                historical_context = await self.memory_service.get_relevant_context(
                    current_project=briefing_text, client_identifier=client_identifier
                )

                contextual_insights = await self.memory_service.extract_contextual_insights(
                    current_project=briefing_text, client_identifier=client_identifier
                )

                logger.info(f"Retrieved historical context and {len(contextual_insights)} insights")

            # ETAPA 2: Classificar projeto com contexto histórico
            enhanced_briefing = briefing_text
            if historical_context:
                enhanced_briefing = f"{briefing_text}\n\nCONTEXTO HISTÓRICO:\n{historical_context}"

            classification = await self.project_classifier.classify_project(enhanced_briefing)
            logger.info(
                f"Project classified: {classification.project_type.value} ({classification.complexity.value})"
            )

            # ETAPA 3: Analisar completude com contexto
            completeness_result = await self.completeness_analyzer.analyze_completeness(
                briefing_text, classification
            )
            logger.info(f"Completeness analyzed: {completeness_result.overall_score:.1f}%")

            # ETAPA 4: Verificar se deve pular perguntas
            if completeness_result.should_skip_questions:
                logger.info("Briefing is complete enough. Skipping questions.")
                return IntelligentSelectionResult(
                    selected_questions=[],
                    context_used=historical_context,
                    insights_applied=contextual_insights,
                    token_savings=self._estimate_token_savings(historical_context),
                    confidence_score=completeness_result.confidence,
                    reasoning="Briefing suficientemente completo. Perguntas desnecessárias.",
                )

            # ETAPA 5: Gerar perguntas inteligentes com contexto
            questions = await self._generate_contextual_questions(
                briefing_text=briefing_text,
                classification=classification,
                completeness_result=completeness_result,
                historical_context=historical_context,
                contextual_insights=contextual_insights,
            )

            # ETAPA 6: Filtrar e otimizar perguntas
            optimized_questions = await self._optimize_questions_with_memory(
                questions=questions,
                contextual_insights=contextual_insights,
                client_identifier=client_identifier,
            )

            # ETAPA 7: Armazenar conhecimento técnico sanitizado no ZEP
            if session_id and self.memory_service.is_enabled:
                # Usar add_project_context que agora sanitiza automaticamente
                await self.memory_service.add_project_context(
                    session_id=session_id,
                    project_description=briefing_text,  # Será sanitizado automaticamente
                    classification={
                        "type": classification.project_type.value,
                        "complexity": classification.complexity.value,
                        "domain_context": classification.domain_context,
                    },
                    client_identifier=None,  # Sistema é completamente anônimo
                )

            # ETAPA 8: Calcular savings de tokens
            token_savings = self._estimate_token_savings(historical_context)

            result = IntelligentSelectionResult(
                selected_questions=optimized_questions,
                context_used=historical_context,
                insights_applied=contextual_insights,
                token_savings=token_savings,
                confidence_score=classification.confidence,
                reasoning=f"Geradas {len(optimized_questions)} perguntas contextualizadas "
                f"baseadas em {len(contextual_insights)} insights históricos.",
            )

            logger.info(
                f"Generated {len(optimized_questions)} optimized questions with {token_savings} token savings"
            )
            return result

        except Exception as e:
            logger.error(f"Error in intelligent question generation: {str(e)}")
            # Fallback para geração padrão
            return await self._fallback_generation(briefing_text)

    async def _generate_contextual_questions(
        self,
        briefing_text: str,
        classification: ProjectClassification,
        completeness_result: Any,
        historical_context: Optional[str],
        contextual_insights: List[ContextualInsight],
    ) -> List[Question]:
        """Gera perguntas contextualizadas usando insights históricos."""

        # Preparar contexto para geração
        generation_context = GenerationContext(
            briefing_text=briefing_text,
            completeness_result=completeness_result,
            missing_areas=completeness_result.missing_critical_areas,
            project_classification=classification,
            max_questions=self.max_questions,
            focus_categories=classification.critical_categories,
        )

        # Gerar perguntas dinâmicas
        dynamic_questions = await self.question_generator.generate_questions(generation_context)

        # Converter para Questions padrão
        standard_questions = self.question_generator.convert_to_standard_questions(
            dynamic_questions
        )

        return standard_questions

    async def _optimize_questions_with_memory(
        self,
        questions: List[Question],
        contextual_insights: List[ContextualInsight],
        client_identifier: Optional[str],
    ) -> List[Question]:
        """Otimiza perguntas baseado nos insights de memória."""

        if not contextual_insights:
            return questions[: self.max_questions]

        # Análise com IA para otimização baseada nos insights
        optimization_prompt = f"""
        Analise estas perguntas e insights históricos para otimizar a seleção:
        
        PERGUNTAS GERADAS:
        {self._format_questions_for_analysis(questions)}
        
        INSIGHTS HISTÓRICOS:
        {self._format_insights_for_analysis(contextual_insights)}
        
        Instrução:
        1. Remova perguntas que já podem ser respondidas pelos insights históricos
        2. Priorize perguntas que complementam o conhecimento histórico
        3. Mantenha máximo {self.max_questions} perguntas mais relevantes
        4. Considere padrões e preferências do cliente
        
        Retorne JSON com IDs das perguntas a manter:
        {{"selected_question_ids": ["id1", "id2", ...], "reasoning": "explicação"}}
        """

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um expert em otimização contextual de perguntas.",
                    },
                    {"role": "user", "content": optimization_prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            selected_ids = result.get("selected_question_ids", [])

            # Filtrar perguntas baseado na seleção IA
            optimized_questions = [q for q in questions if q.id in selected_ids]

            # Se a IA removeu muitas, manter as top-rated
            if len(optimized_questions) < min(3, len(questions)):
                optimized_questions = questions[: min(self.max_questions, len(questions))]

            logger.info(
                f"Optimized {len(questions)} questions to {len(optimized_questions)} using memory insights"
            )
            return optimized_questions[: self.max_questions]

        except Exception as e:
            logger.error(f"Error optimizing questions: {str(e)}")
            return questions[: self.max_questions]

    def _format_questions_for_analysis(self, questions: List[Question]) -> str:
        """Formata perguntas para análise por IA."""
        formatted = []
        for i, q in enumerate(questions):
            formatted.append(f"{i+1}. [{q.id}] {q.text}")
        return "\n".join(formatted)

    def _format_insights_for_analysis(self, insights: List[ContextualInsight]) -> str:
        """Formata insights para análise por IA."""
        formatted = []
        for i, insight in enumerate(insights):
            formatted.append(f"{i+1}. {insight.insight_type}: {insight.description}")
            if insight.suggested_questions:
                formatted.append(f"   Sugestões: {', '.join(insight.suggested_questions[:2])}")
        return "\n".join(formatted)

    def _estimate_token_savings(self, historical_context: Optional[str]) -> int:
        """Estima tokens economizados através do uso de contexto histórico."""
        if not historical_context:
            return 0

        # Estimativa básica: contexto histórico evita regenerar análise similar
        # Aproximadamente 150-300 tokens economizados por contexto relevante
        context_length = len(historical_context.split())
        return min(300, max(150, context_length // 2))

    async def _fallback_generation(self, briefing_text: str) -> IntelligentSelectionResult:
        """Geração de fallback quando há erro no processo principal."""
        try:
            # Classificação básica
            classification = await self.project_classifier.classify_project(briefing_text)

            # Análise de completude básica
            completeness_result = await self.completeness_analyzer.analyze_completeness(
                briefing_text, classification
            )

            # Geração de perguntas sem contexto
            generation_context = GenerationContext(
                briefing_text=briefing_text,
                completeness_result=completeness_result,
                missing_areas=completeness_result.missing_critical_areas,
                project_classification=classification,
                max_questions=self.max_questions,
            )

            dynamic_questions = await self.question_generator.generate_questions(generation_context)
            standard_questions = self.question_generator.convert_to_standard_questions(
                dynamic_questions
            )

            return IntelligentSelectionResult(
                selected_questions=standard_questions[: self.max_questions],
                context_used=None,
                insights_applied=[],
                token_savings=0,
                confidence_score=0.5,
                reasoning="Geração de fallback devido a erro no processo principal.",
            )

        except Exception as e:
            logger.error(f"Error in fallback generation: {str(e)}")
            return IntelligentSelectionResult(
                selected_questions=[],
                context_used=None,
                insights_applied=[],
                token_savings=0,
                confidence_score=0.0,
                reasoning=f"Erro na geração de fallback: {str(e)}",
            )

    async def finalize_session(
        self, session_id: str, final_scope: str, success: bool = True, client_identifier: str = None
    ) -> bool:
        """
        Finaliza sessão e armazena resultado na memória universal.

        Args:
            session_id: ID da sessão ZEP
            final_scope: Escopo final gerado
            success: Se o processo foi bem-sucedido
            client_identifier: Identificador do cliente (opcional)

        Returns:
            True se sucesso, False se erro
        """
        if self.memory_service.is_enabled:
            return await self.memory_service.store_project_completion(
                session_id=session_id,
                final_scope=final_scope,  # Será sanitizado automaticamente
                success=success,
                client_identifier=None,  # Sistema é completamente anônimo
            )
        return True

    def get_service_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do serviço."""
        memory_stats = self.memory_service.get_service_stats()

        return {
            "service_type": "single_agent_with_memory",
            "version": "1.0.0",
            "memory_integration": memory_stats,
            "model": self.model,
            "max_questions": self.max_questions,
            "temperature": self.temperature,
        }
