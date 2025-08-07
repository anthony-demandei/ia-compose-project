"""
Dynamic Question Generator - Gera perguntas contextualmente relevantes usando IA
ao invés de um catálogo fixo.

Integra com o sistema multi-agent para validação e refinamento.
"""

import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from openai import AsyncOpenAI
import uuid

from app.models.intake import Question, QuestionType, QuestionStage, QuestionOption
from app.services.briefing_completeness_analyzer import CompletenessResult
from app.services.universal_project_classifier import (
    UniversalCategory,
    ProjectClassification,
)
from app.utils.pii_safe_logging import get_pii_safe_logger
from app.utils.config import get_settings

logger = get_pii_safe_logger(__name__)


@dataclass
class DynamicQuestion:
    """Pergunta gerada dinamicamente."""

    id: str
    text: str
    type: QuestionType
    stage: QuestionStage
    priority: float  # 0-1, maior = mais importante
    context: str  # Contexto que levou à geração
    options: List[QuestionOption] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    reasoning: str = ""

    def to_standard_question(self) -> Question:
        """Converte para Question padrão do sistema."""
        return Question(
            id=self.id,
            text=self.text,
            type=self.type,
            stage=self.stage,
            options=self.options,
            tags=self.tags,
            priority=int(self.priority * 10),  # Converter para escala 0-10
            required=self.priority > 0.7,  # Alta prioridade = obrigatória
        )


@dataclass
class GenerationContext:
    """Contexto para geração de perguntas universal."""

    briefing_text: str
    completeness_result: CompletenessResult
    missing_areas: List[str]
    project_classification: Optional[ProjectClassification] = None
    domain: Optional[str] = None  # Legado, usar project_classification.domain_context
    existing_info: Dict[str, Any] = field(default_factory=dict)
    max_questions: int = 5
    focus_categories: List[UniversalCategory] = field(default_factory=list)


class DynamicQuestionGenerator:
    """
    Gerador de perguntas dinâmicas usando IA.

    Features:
    - Gera perguntas contextuais baseadas no que falta
    - Adapta tipo e formato da pergunta ao contexto
    - Integra com sistema de validação multi-agent
    - Mantém consistência com taxonomia existente
    """

    def __init__(self, api_key: str = None):
        """
        Inicializa o gerador de perguntas dinâmicas.

        Args:
            api_key: Chave da OpenAI API (usa ENV se não fornecida)
        """
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)
        self.model = settings.openai_model
        self.temperature = 0.7  # Balanceado para criatividade controlada

        # Mapeamento de categorias universais para stage
        self.category_to_stage = {
            UniversalCategory.OBJECTIVE: QuestionStage.BUSINESS,
            UniversalCategory.FUNCTIONAL: QuestionStage.FUNCTIONAL,
            UniversalCategory.TECHNICAL: QuestionStage.TECHNICAL,
            UniversalCategory.SCOPE: QuestionStage.BUSINESS,
            UniversalCategory.CONSTRAINTS: QuestionStage.TECHNICAL,
            UniversalCategory.RESOURCES: QuestionStage.BUSINESS,
            UniversalCategory.ENVIRONMENT: QuestionStage.TECHNICAL,
            UniversalCategory.SUCCESS_CRITERIA: QuestionStage.BUSINESS,
        }

        # Mapeamento legado para compatibility
        self.context_to_stage = {
            "objective": QuestionStage.BUSINESS,
            "functional": QuestionStage.FUNCTIONAL,
            "technical": QuestionStage.TECHNICAL,
            "scope": QuestionStage.BUSINESS,
            "constraints": QuestionStage.TECHNICAL,
            "resources": QuestionStage.BUSINESS,
            "environment": QuestionStage.TECHNICAL,
            "success": QuestionStage.BUSINESS,
        }

        # Cache de perguntas geradas
        self.question_cache: Dict[str, List[DynamicQuestion]] = {}

        logger.info("DynamicQuestionGenerator initialized")

    async def generate_questions(self, context: GenerationContext) -> List[DynamicQuestion]:
        """
        Gera perguntas dinâmicas baseadas no contexto.

        Args:
            context: Contexto com briefing e análise de completude

        Returns:
            Lista de perguntas dinâmicas priorizadas
        """
        try:
            # Check cache
            cache_key = self._generate_cache_key(context.briefing_text)
            if cache_key in self.question_cache:
                logger.info("Using cached dynamic questions")
                return self.question_cache[cache_key][: context.max_questions]

            logger.info(f"Generating {context.max_questions} dynamic questions")

            # 1. Analisar áreas faltantes e priorizar
            prioritized_areas = self._prioritize_missing_areas(context)

            # 2. Gerar perguntas com IA
            questions_data = await self._generate_with_gpt(context, prioritized_areas)

            # 3. Processar e validar perguntas
            dynamic_questions = self._process_generated_questions(questions_data, context)

            # 4. Ordenar por prioridade
            dynamic_questions.sort(key=lambda q: q.priority, reverse=True)

            # 5. Limitar ao máximo solicitado
            final_questions = dynamic_questions[: context.max_questions]

            # Cache result
            self.question_cache[cache_key] = final_questions

            logger.info(
                f"Generated {len(final_questions)} questions, "
                f"top priority: {final_questions[0].priority if final_questions else 0:.2f}"
            )

            return final_questions

        except Exception as e:
            logger.error(f"Error generating dynamic questions: {str(e)}")
            return self._get_fallback_questions(context)

    def _prioritize_missing_areas(self, context: GenerationContext) -> List[Tuple[str, float]]:
        """Prioriza áreas faltantes baseado na importância."""
        prioritized = []

        # Usar scores das categorias para priorizar
        for category, score_data in context.completeness_result.category_scores.items():
            if score_data.score < 80:  # Área precisa de perguntas
                # Prioridade = peso da categoria * (100 - score) / 100
                priority = score_data.weight * (100 - score_data.score) / 100

                for missing_item in score_data.missing_items[:2]:  # Top 2 de cada categoria
                    prioritized.append((missing_item, priority))

        # Adicionar áreas críticas com alta prioridade
        for area in context.completeness_result.missing_critical_areas[:3]:
            if not any(area in item[0] for item in prioritized):
                prioritized.append((area, 0.9))  # Alta prioridade para gaps críticos

        # Ordenar por prioridade
        prioritized.sort(key=lambda x: x[1], reverse=True)

        return prioritized[: context.max_questions * 2]  # Gerar mais para ter opções

    async def _generate_with_gpt(
        self, context: GenerationContext, prioritized_areas: List[Tuple[str, float]]
    ) -> List[Dict[str, Any]]:
        """Gera perguntas usando GPT."""

        # Preparar lista de áreas para o prompt
        areas_text = "\n".join(
            [f"- {area} (prioridade: {priority:.1f})" for area, priority in prioritized_areas]
        )

        prompt = f"""
        Você é um especialista em levantamento de requisitos de software.
        
        Analise este briefing e gere perguntas ESPECÍFICAS e CONTEXTUAIS para preencher as lacunas.
        
        BRIEFING:
        {context.briefing_text}
        
        ÁREAS QUE PRECISAM DE ESCLARECIMENTO (em ordem de prioridade):
        {areas_text}
        
        INFORMAÇÕES JÁ CONHECIDAS:
        - Score de completude: {context.completeness_result.overall_score:.1f}%
        - Tipo de projeto: {context.project_classification.project_type.value if context.project_classification else 'não especificado'}
        - Complexidade: {context.project_classification.complexity.value if context.project_classification else 'não especificado'}
        - Domínio: {context.project_classification.domain_context if context.project_classification else context.domain or 'não especificado'}
        
        Gere {context.max_questions + 2} perguntas no formato JSON:
        {{
            "questions": [
                {{
                    "text": "pergunta específica e contextual",
                    "type": "single_choice" | "multi_choice" | "text" | "number",
                    "priority": 0.0-1.0,
                    "context_area": "objective" | "functional" | "technical" | "scope" | "constraints" | "resources" | "environment" | "success",
                    "options": ["opção 1", "opção 2", ...] // se for choice, senão null,
                    "tags": ["tag1", "tag2"],
                    "reasoning": "por que esta pergunta é importante para este projeto específico"
                }}
            ]
        }}
        
        DIRETRIZES IMPORTANTES:
        1. Perguntas devem ser ESPECÍFICAS ao contexto do projeto, não genéricas
        2. Se o briefing menciona "plataforma de e-commerce", não pergunte "que tipo de sistema?"
        3. Foque em detalhes técnicos e de implementação quando o briefing é técnico
        4. Para briefings de negócio, foque em objetivos e métricas
        5. Prioridade 1.0 = absolutamente crítico, 0.0 = nice to have
        6. Use single_choice para opções mutuamente exclusivas
        7. Use multi_choice quando múltiplas opções são possíveis
        8. Use text para respostas abertas curtas
        9. Use number para quantidades, valores, etc.
        
        EXEMPLOS DE PERGUNTAS CONTEXTUAIS POR TIPO:
        - Automation: "Qual frequência de execução (horário, diário, sob demanda)?"
        - Website: "Precisa de CMS para edição de conteúdo?"
        - Application: "Quantos usuários simultâneos são esperados?"
        - System: "Quais sistemas legados precisam ser integrados?"
        - Platform: "Qual modelo de pricing (freemium, subscription, usage-based)?"
        - E-commerce: "Qual gateway de pagamento preferido (Stripe, PayPal, PagSeguro)?"
        - Service: "Como os clientes vão agendar horários (online, telefone, presencial)?"
        
        Evite perguntas óbvias já respondidas no briefing!
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um expert em requisitos de software. "
                        "Gere perguntas precisas e contextuais, nunca genéricas.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            return result.get("questions", [])

        except Exception as e:
            logger.error(f"Error generating questions with GPT: {str(e)}")
            return []

    def _process_generated_questions(
        self, questions_data: List[Dict[str, Any]], context: GenerationContext
    ) -> List[DynamicQuestion]:
        """Processa e valida perguntas geradas."""
        dynamic_questions = []

        for q_data in questions_data:
            try:
                # Determinar tipo da pergunta
                type_str = q_data.get("type", "text")
                question_type = self._map_question_type(type_str)

                # Determinar stage
                context_area = q_data.get("context_area", "technical")
                stage = self.context_to_stage.get(context_area, QuestionStage.TECHNICAL)

                # Processar opções se houver
                options = []
                if question_type in [QuestionType.SINGLE_CHOICE, QuestionType.MULTI_CHOICE]:
                    raw_options = q_data.get("options", [])

                    # Se é um tipo boolean, adicionar opções Sim/Não se não houver opções
                    if q_data.get("type", "").lower() == "boolean" and not raw_options:
                        raw_options = ["Sim", "Não"]

                    options = [
                        QuestionOption(id=f"opt_{i}", label=opt)
                        for i, opt in enumerate(raw_options)
                    ]

                # Criar pergunta dinâmica
                question = DynamicQuestion(
                    id=f"DYN_{uuid.uuid4().hex[:8]}",
                    text=q_data.get("text", ""),
                    type=question_type,
                    stage=stage,
                    priority=float(q_data.get("priority", 0.5)),
                    context=context_area,
                    options=options,
                    tags=q_data.get("tags", []),
                    reasoning=q_data.get("reasoning", ""),
                )

                # Validar pergunta
                if self._validate_question(question, context):
                    dynamic_questions.append(question)

            except Exception as e:
                logger.warning(f"Error processing generated question: {str(e)}")
                continue

        return dynamic_questions

    def _map_question_type(self, type_str: str) -> QuestionType:
        """Mapeia string para QuestionType enum."""
        # Normalizar para minúsculo para evitar problemas de case
        type_str = type_str.lower() if type_str else "text"

        mapping = {
            "single_choice": QuestionType.SINGLE_CHOICE,
            "multi_choice": QuestionType.MULTI_CHOICE,
            "text": QuestionType.TEXT,
            "number": QuestionType.NUMBER,
            "boolean": QuestionType.SINGLE_CHOICE,  # Map to single_choice with Yes/No options
            "date": QuestionType.TEXT,  # Map to text input for dates
        }
        return mapping.get(type_str, QuestionType.TEXT)

    def _validate_question(self, question: DynamicQuestion, context: GenerationContext) -> bool:
        """Valida se a pergunta é apropriada."""
        # Verificar se tem texto
        if not question.text or len(question.text) < 10:
            return False

        # Verificar se tem opções quando necessário
        if question.type in [QuestionType.SINGLE_CHOICE, QuestionType.MULTI_CHOICE]:
            if not question.options or len(question.options) < 2:
                return False

        # Verificar se não é redundante (pergunta sobre algo já mencionado)
        briefing_lower = context.briefing_text.lower()

        # Lista de padrões que indicam redundância
        redundancy_patterns = [
            ("que tipo de", "sistema", "aplicação"),  # Se já disse o tipo
            ("qual é o objetivo", "finalidade"),  # Se já explicou o objetivo
            ("quem são os usuários",),  # Se já mencionou usuários
        ]

        question_lower = question.text.lower()
        for pattern_words in redundancy_patterns:
            if any(word in question_lower for word in pattern_words):
                # Verificar se a resposta já está no briefing
                # Isso é simplificado - em produção seria mais sofisticado
                if any(word in briefing_lower for word in pattern_words):
                    logger.debug(f"Skipping redundant question: {question.text[:50]}...")
                    return False

        return True

    def _get_fallback_questions(self, context: GenerationContext) -> List[DynamicQuestion]:
        """Retorna perguntas de fallback se a geração falhar."""
        fallback = []

        # Perguntas básicas baseadas nas áreas faltantes
        for area in context.completeness_result.missing_critical_areas[: context.max_questions]:
            question = DynamicQuestion(
                id=f"FALLBACK_{uuid.uuid4().hex[:8]}",
                text=f"Poderia fornecer mais detalhes sobre {area}?",
                type=QuestionType.TEXT,
                stage=QuestionStage.TECHNICAL,
                priority=0.7,
                context=area,
                reasoning="Pergunta de fallback para área crítica faltante",
            )
            fallback.append(question)

        # Se não houver áreas críticas, usar perguntas genéricas importantes
        if not fallback:
            generic_questions = [
                ("Qual é o prazo desejado para entrega?", QuestionStage.BUSINESS, 0.8),
                ("Qual é o orçamento disponível?", QuestionStage.BUSINESS, 0.7),
                ("Quantos usuários simultâneos são esperados?", QuestionStage.TECHNICAL, 0.7),
                ("Há preferências de tecnologia?", QuestionStage.TECHNICAL, 0.6),
                ("Precisa de suporte pós-lançamento?", QuestionStage.BUSINESS, 0.5),
            ]

            for text, stage, priority in generic_questions[: context.max_questions]:
                question = DynamicQuestion(
                    id=f"GENERIC_{uuid.uuid4().hex[:8]}",
                    text=text,
                    type=QuestionType.TEXT,
                    stage=stage,
                    priority=priority,
                    context="generic",
                    reasoning="Pergunta genérica importante",
                )
                fallback.append(question)

        return fallback

    def _generate_cache_key(self, text: str) -> str:
        """Gera chave única para cache."""
        import hashlib

        return hashlib.md5(text.encode()).hexdigest()

    async def refine_with_agents(
        self, questions: List[DynamicQuestion], agent_feedback: Dict[str, Any]
    ) -> List[DynamicQuestion]:
        """
        Refina perguntas baseado no feedback dos agents.

        Args:
            questions: Perguntas geradas
            agent_feedback: Feedback dos agents especializados

        Returns:
            Perguntas refinadas
        """
        # TODO: Implementar refinamento baseado em feedback multi-agent
        # Por ora, retorna as perguntas sem modificação
        return questions

    def convert_to_standard_questions(
        self, dynamic_questions: List[DynamicQuestion]
    ) -> List[Question]:
        """
        Converte perguntas dinâmicas para formato padrão do sistema.

        Args:
            dynamic_questions: Lista de perguntas dinâmicas

        Returns:
            Lista de Questions padrão
        """
        return [q.to_standard_question() for q in dynamic_questions]

    def get_generator_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do gerador."""
        total_generated = sum(len(questions) for questions in self.question_cache.values())

        return {
            "cached_generations": len(self.question_cache),
            "total_questions_generated": total_generated,
            "model": self.model,
            "temperature": self.temperature,
        }
