"""
Motor principal do sistema de intake.
Orquestra o fluxo completo de intake → wizard → escopo.
"""

from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime

from app.models.intake import (
    IntakeSession,
    IntakeStatus,
    WizardState,
    SummaryResponse,
    IntakeArtifact,
    Question,
)
from app.services.question_selector import QuestionSelector
from app.services.multi_agent_question_selector import MultiAgentQuestionSelector
from app.services.scope_generator import ScopeGenerator
from app.services.context_manager import ContextManager
from app.services.validation_engine_v2 import ValidationEngineV2
from app.services.context_inference_engine import ContextInferenceEngine
from app.services.smart_question_filter import SmartQuestionFilter
from app.services.briefing_completeness_analyzer import (
    BriefingCompletenessAnalyzer,
)
from app.services.dynamic_question_generator import DynamicQuestionGenerator
from app.services.universal_project_classifier import UniversalProjectClassifier
from app.services.single_agent_with_memory import SingleAgentWithMemoryService
from app.services.zep_memory_service import ZepMemoryService
from app.utils.pii_safe_logging import get_pii_safe_logger
from openai import AsyncOpenAI

logger = get_pii_safe_logger(__name__)


class IntakeEngine:
    """
    Motor principal que gerencia o fluxo de intake V2.0:
    1. Recebe texto inicial
    2. Análise de contexto com IA (Context Inference Engine)
    3. Seleção inteligente de perguntas (Multi-Agent + Smart Filter)
    4. Gerencia wizard condicional
    5. Gera resumo e escopo final

    V2.0 Features:
    - Context-aware question selection
    - Redundancy elimination
    - Smart filtering based on domain knowledge
    """

    def __init__(
        self,
        openai_api_key: str,
        db_connection=None,
        enable_multi_agent: bool = False,
        enable_context_inference: bool = True,
        enable_dynamic_questions: bool = True,
        enable_zep_memory: bool = True,
    ):
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        self.scope_generator = ScopeGenerator(openai_api_key)
        self.db = db_connection  # TODO: Implementar conexão Postgres

        # V4.0 Features: Single Agent + ZEP Memory Integration
        self.enable_multi_agent = enable_multi_agent  # Deprecated, mantido para compatibilidade
        self.enable_context_inference = enable_context_inference
        self.enable_dynamic_questions = enable_dynamic_questions
        self.enable_zep_memory = enable_zep_memory

        # V4.0: Sistema de agente único com memória ZEP
        if enable_zep_memory:
            logger.info("Initializing Single Agent with ZEP Memory V4.0")
            self.single_agent_service = SingleAgentWithMemoryService(openai_api_key)
            self.memory_service = ZepMemoryService()
            self.use_single_agent = True
        else:
            logger.info("ZEP Memory disabled, using legacy system")
            self.use_single_agent = False

            # Fallback para sistema V3.0 (manter compatibilidade)
            self.project_classifier = UniversalProjectClassifier(api_key=openai_api_key)
            self.completeness_analyzer = BriefingCompletenessAnalyzer(
                api_key=openai_api_key, threshold=0.9
            )

            if enable_dynamic_questions:
                logger.info("Initializing Dynamic Question Generator V3.0")
                self.dynamic_question_generator = DynamicQuestionGenerator(api_key=openai_api_key)

            if enable_multi_agent:
                logger.info("Initializing Multi-Agent System V2.0 with context awareness")
                self.context_inference_engine = ContextInferenceEngine(api_key=openai_api_key)
                self.smart_question_filter = SmartQuestionFilter()
                self.context_manager = ContextManager()
                self.validation_engine = ValidationEngineV2()
                self.question_selector = MultiAgentQuestionSelector(
                    context_manager=self.context_manager,
                    validation_engine=self.validation_engine,
                    context_inference_engine=self.context_inference_engine,
                    smart_question_filter=self.smart_question_filter,
                )
            else:
                logger.info("Using legacy question selector with V2 catalog")
                self.question_selector = QuestionSelector(openai_api_key)

        # Cache de sessões em memória (temporário)
        self.sessions_cache: Dict[UUID, IntakeSession] = {}
        self.wizard_states: Dict[UUID, WizardState] = {}

        # Sistema de versão
        self.version = "4.0"  # Upgraded for Single Agent + ZEP Memory integration

        logger.info(f"IntakeEngine V{self.version} initialized")
        logger.info(f"ZEP Memory: {enable_zep_memory}, Single Agent: {self.use_single_agent}")
        if not self.use_single_agent:
            logger.info(
                f"Legacy Mode - Multi-Agent: {enable_multi_agent}, Context Inference: {enable_context_inference}, Dynamic Questions: {enable_dynamic_questions}"
            )

    async def create_intake_session(
        self,
        intake_text: str,
        metadata: Optional[Dict] = None,
        user_id: str = None,
        user_email: str = None,
        user_name: str = None,
    ) -> IntakeSession:
        """
        Cria nova sessão de intake e seleciona perguntas.
        V4.0: Usa agente único com memória ZEP para contexto histórico e otimização de tokens.

        Args:
            intake_text: Descrição inicial do projeto
            metadata: Metadados opcionais
            user_id: ID do usuário (para memória ZEP)
            user_email: Email do usuário
            user_name: Nome do usuário

        Returns:
            IntakeSession com perguntas selecionadas ou vazias se briefing completo
        """
        try:
            if self.use_single_agent:
                return await self._create_session_with_single_agent(
                    intake_text, metadata, user_id, user_email, user_name
                )
            else:
                return await self._create_session_legacy_mode(intake_text, metadata)

        except Exception as e:
            logger.error(f"Error creating intake session V{self.version}: {str(e)}")
            raise

    async def _create_session_with_single_agent(
        self,
        intake_text: str,
        metadata: Optional[Dict],
        user_id: Optional[str],
        user_email: Optional[str],
        user_name: Optional[str],
    ) -> IntakeSession:
        """Cria sessão usando o sistema de agente único com ZEP Memory."""
        try:
            logger.info("Creating intake session with Single Agent + ZEP Memory V4.0")

            # ETAPA 1: Inicializar sessão ZEP universal
            zep_session_id = None
            if self.memory_service.is_enabled:
                # Usar identificador do projeto baseado no user_id se disponível
                project_identifier = user_id if user_id else "anonymous"
                zep_session_id = await self.memory_service.initialize_universal_session(
                    project_identifier=project_identifier
                )
                logger.info(f"ZEP universal session initialized: {zep_session_id}")

            # ETAPA 2: Análise inteligente com contexto histórico universal
            selection_result = await self.single_agent_service.analyze_and_generate_questions(
                briefing_text=intake_text, client_identifier=user_id, session_id=zep_session_id
            )

            logger.info(
                f"Single Agent generated {len(selection_result.selected_questions)} questions"
            )
            logger.info(f"Token savings: {selection_result.token_savings}")
            logger.info(f"Applied {len(selection_result.insights_applied)} contextual insights")

            # ETAPA 3: Extrair IDs das perguntas
            question_ids = [q.id for q in selection_result.selected_questions]

            # ETAPA 4: Determinar status baseado nas perguntas
            if not question_ids:
                status = IntakeStatus.SUMMARIZED  # Sem perguntas = ir direto para resumo
                logger.info("No questions needed. Going directly to summary.")
            else:
                status = IntakeStatus.ASKING

            # ETAPA 5: Montar metadados enriquecidos
            enhanced_metadata = (metadata or {}).copy()
            enhanced_metadata.update(
                {
                    "engine_version": self.version,
                    "single_agent_enabled": True,
                    "zep_memory_enabled": self.memory_service.is_enabled,
                    "zep_session_id": zep_session_id,
                    "user_context": {"user_id": user_id, "email": user_email, "name": user_name},
                    "intelligent_selection": {
                        "questions_generated": len(selection_result.selected_questions),
                        "context_used": selection_result.context_used is not None,
                        "insights_applied": len(selection_result.insights_applied),
                        "token_savings": selection_result.token_savings,
                        "confidence_score": selection_result.confidence_score,
                        "reasoning": selection_result.reasoning,
                    },
                }
            )

            # ETAPA 6: Criar sessão
            session = IntakeSession(
                intake_text=intake_text,
                question_ids=question_ids,
                metadata=enhanced_metadata,
                status=status,
            )

            # ETAPA 7: Criar estado do wizard
            wizard_state = WizardState(
                session_id=session.id,
                remaining_questions=question_ids.copy(),
                answered_questions=[],
            )

            # ETAPA 8: Armazenar temporariamente em cache
            self.sessions_cache[session.id] = session
            self.wizard_states[session.id] = wizard_state

            # ETAPA 9: Adicionar perguntas ao catálogo temporário para referência
            if hasattr(self, "question_catalog"):
                self.question_catalog.extend(selection_result.selected_questions)
            else:
                self.question_catalog = selection_result.selected_questions

            logger.info(f"Session created with Single Agent: {session.id}")
            logger.info(
                f"Generated {len(question_ids)} questions with {selection_result.token_savings} token savings"
            )

            return session

        except Exception as e:
            logger.error(f"Error in single agent session creation: {str(e)}")
            # Fallback para modo legado se falhar
            return await self._create_session_legacy_mode(intake_text, metadata)

    async def _create_session_legacy_mode(
        self, intake_text: str, metadata: Optional[Dict]
    ) -> IntakeSession:
        """Fallback para modo legado (V3.0) se ZEP falhar."""
        try:
            logger.info("Creating session in legacy mode (V3.0 fallback)")

            if hasattr(self, "project_classifier") and hasattr(self, "completeness_analyzer"):
                # Sistema V3.0 disponível
                project_classification = await self.project_classifier.classify_project(intake_text)
                completeness_result = await self.completeness_analyzer.analyze_completeness(
                    intake_text, project_classification
                )

                if completeness_result.should_skip_questions:
                    # Criar sessão sem perguntas
                    session = IntakeSession(
                        intake_text=intake_text,
                        question_ids=[],
                        metadata={
                            "engine_version": self.version,
                            "legacy_mode": True,
                            "skipped_questions": True,
                        },
                        status=IntakeStatus.SUMMARIZED,
                    )
                    self.sessions_cache[session.id] = session
                    self.wizard_states[session.id] = WizardState(session.id, [], [])
                    return session

                # Gerar perguntas dinamicamente
                if hasattr(self, "dynamic_question_generator") and self.dynamic_question_generator:
                    from app.services.dynamic_question_generator import GenerationContext

                    generation_context = GenerationContext(
                        briefing_text=intake_text,
                        completeness_result=completeness_result,
                        missing_areas=completeness_result.missing_critical_areas,
                        project_classification=project_classification,
                        max_questions=5,
                    )

                    dynamic_questions = await self.dynamic_question_generator.generate_questions(
                        generation_context
                    )
                    standard_questions = (
                        self.dynamic_question_generator.convert_to_standard_questions(
                            dynamic_questions
                        )
                    )
                    question_ids = [q.id for q in standard_questions]
                    self.question_catalog = standard_questions
                else:
                    question_ids = []

                # Criar sessão com perguntas
                session = IntakeSession(
                    intake_text=intake_text,
                    question_ids=question_ids,
                    metadata={
                        "engine_version": self.version,
                        "legacy_mode": True,
                        "questions_generated": len(question_ids),
                    },
                    status=IntakeStatus.ASKING if question_ids else IntakeStatus.SUMMARIZED,
                )

                self.sessions_cache[session.id] = session
                self.wizard_states[session.id] = WizardState(session.id, question_ids.copy(), [])
                return session

            else:
                # Fallback básico sem perguntas
                logger.warning(
                    "No classification/analysis services available, creating basic session"
                )
                session = IntakeSession(
                    intake_text=intake_text,
                    question_ids=[],
                    metadata={"engine_version": self.version, "basic_fallback": True},
                    status=IntakeStatus.SUMMARIZED,
                )
                self.sessions_cache[session.id] = session
                self.wizard_states[session.id] = WizardState(session.id, [], [])
                return session

        except Exception as e:
            logger.error(f"Error in legacy mode session creation: {str(e)}")
            # Fallback final básico
            session = IntakeSession(
                intake_text=intake_text,
                question_ids=[],
                metadata={"engine_version": self.version, "emergency_fallback": True},
                status=IntakeStatus.SUMMARIZED,
            )
            self.sessions_cache[session.id] = session
            self.wizard_states[session.id] = WizardState(session.id, [], [])
            return session

    async def process_answers(
        self, session_id: UUID, answers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Processa respostas do wizard e retorna próximas perguntas.

        Args:
            session_id: ID da sessão
            answers: Lista de respostas [{"questionId": "Q1", "value": "..."}]

        Returns:
            Dict com próximas perguntas e status
        """
        try:
            # Recuperar sessão e estado
            session = self.sessions_cache.get(session_id)
            wizard_state = self.wizard_states.get(session_id)

            if not session or not wizard_state:
                raise ValueError(f"Sessão não encontrada: {session_id}")

            # Processar cada resposta
            for answer_data in answers:
                question_id = answer_data.get("questionId")
                value = answer_data.get("value")

                # Normalizar valor
                normalized_value = self._normalize_answer(question_id, value)

                # Salvar resposta
                session.answers[question_id] = normalized_value

                # Atualizar estado do wizard
                wizard_state.mark_answered([question_id])

            # Obter próximas perguntas considerando condições
            next_questions = []
            if hasattr(self, "question_selector") and self.question_selector:
                next_questions = self.question_selector.get_next_questions(
                    session.question_ids, session.answers, batch_size=3
                )
            else:
                # Para sistema novo, implementar lógica básica de próximas perguntas
                remaining = [q_id for q_id in session.question_ids if q_id not in session.answers]
                next_questions = []
                for q_id in remaining[:3]:  # Próximas 3 perguntas
                    question = self.get_question_by_id(q_id)
                    if question:
                        next_questions.append(
                            {
                                "id": question.id,
                                "text": question.text,
                                "type": question.type,
                                "options": question.options,
                                "required": question.required,
                            }
                        )

            # Atualizar status se todas respondidas
            if not next_questions and len(session.answers) >= len(session.question_ids) * 0.8:
                session.status = IntakeStatus.SUMMARIZED

            # Calcular progresso
            total = len(session.question_ids)
            answered = len(session.answers)
            progress = (answered / total * 100) if total > 0 else 0

            return {
                "next": next_questions,
                "progress": round(progress, 1),
                "total_questions": total,
                "answered_questions": answered,
                "status": session.status.value,
            }

        except Exception as e:
            logger.error(f"Erro ao processar respostas: {str(e)}")
            raise

    async def generate_summary(self, session_id: UUID) -> SummaryResponse:
        """
        Gera resumo das respostas coletadas.

        Args:
            session_id: ID da sessão

        Returns:
            SummaryResponse com resumo em Markdown
        """
        try:
            session = self.sessions_cache.get(session_id)
            if not session:
                raise ValueError(f"Sessão não encontrada: {session_id}")

            # Preparar dados para resumo
            answers_text = self._format_answers_for_summary(session)

            # Gerar resumo com IA
            prompt = f"""
            Gere um resumo conciso e organizado das seguintes informações do projeto:
            
            Texto inicial do cliente:
            {session.intake_text}
            
            Respostas do formulário:
            {answers_text}
            
            Formato de saída:
            ## Resumo do Projeto
            
            ### Objetivo Principal
            [texto]
            
            ### Funcionalidades Principais
            - Item 1
            - Item 2
            
            ### Requisitos Técnicos
            - Item 1
            - Item 2
            
            ### Integrações Necessárias
            - Item 1
            
            ### Restrições e Considerações
            - Item 1
            
            Seja conciso e direto. Use bullets quando apropriado.
            """

            from app.utils.config import get_settings

            settings = get_settings()

            response = await self.openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um analista de requisitos. Gere resumos claros e estruturados.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1500,
            )

            summary = response.choices[0].message.content

            # Salvar resumo na sessão
            session.summary = summary
            session.status = IntakeStatus.SUMMARIZED

            # Calcular completude
            total = len(session.question_ids)
            answered = len(session.answers)
            completion = (answered / total * 100) if total > 0 else 0

            return SummaryResponse(
                summary=summary, ask_for_more=True, completion_percentage=completion
            )

        except Exception as e:
            logger.error(f"Erro ao gerar resumo: {str(e)}")
            raise

    async def add_final_note(self, session_id: UUID, note: str) -> bool:
        """
        Adiciona nota final do cliente após o resumo.

        Args:
            session_id: ID da sessão
            note: Texto adicional do cliente

        Returns:
            True se sucesso
        """
        try:
            session = self.sessions_cache.get(session_id)
            if not session:
                raise ValueError(f"Sessão não encontrada: {session_id}")

            session.final_note = note
            session.updated_at = datetime.utcnow()

            logger.info(f"Nota final adicionada à sessão {session_id}")
            return True

        except Exception as e:
            logger.error(f"Erro ao adicionar nota final: {str(e)}")
            return False

    async def generate_scope_document(self, session_id: UUID) -> str:
        """
        Gera documento de escopo técnico completo.

        Args:
            session_id: ID da sessão

        Returns:
            Documento de escopo em Markdown
        """
        try:
            session = self.sessions_cache.get(session_id)
            if not session:
                raise ValueError(f"Sessão não encontrada: {session_id}")

            # Gerar escopo usando o ScopeGenerator
            scope_doc = await self.scope_generator.generate_scope(
                intake_text=session.intake_text,
                answers=session.answers,
                question_catalog=self.question_selector.catalog,
                summary=session.summary,
                final_note=session.final_note,
            )

            # Salvar documento na sessão
            session.scope_document = scope_doc.to_markdown()
            session.status = IntakeStatus.SCOPED

            # Criar artefato
            artifact = IntakeArtifact(
                session_id=session_id, kind="scope_md", content=session.scope_document
            )

            # TODO: Salvar no DB

            logger.info(f"Escopo gerado para sessão {session_id}")
            return session.scope_document

        except Exception as e:
            logger.error(f"Erro ao gerar escopo: {str(e)}")
            raise

    def _normalize_answer(self, question_id: str, value: Any) -> Any:
        """
        Normaliza resposta baseado no tipo da pergunta.

        Args:
            question_id: ID da pergunta
            value: Valor bruto da resposta

        Returns:
            Valor normalizado
        """
        # Encontrar pergunta no catálogo
        question = next((q for q in self.question_selector.catalog if q.id == question_id), None)

        if not question:
            return value

        # Normalizar baseado no tipo
        if question.type == "single_choice":
            # Garantir que é string
            return str(value) if value else ""

        elif question.type == "multi_choice":
            # Garantir que é lista
            if isinstance(value, list):
                return value
            elif value:
                return [str(value)]
            else:
                return []

        elif question.type == "text":
            # Limitar tamanho e sanitizar
            text = str(value) if value else ""
            return text[:2000].strip()

        elif question.type == "number":
            # Converter para número
            try:
                return float(value) if value else 0
            except:
                return 0

        return value

    def _format_answers_for_summary(self, session: IntakeSession) -> str:
        """
        Formata respostas da sessão para geração de resumo.

        Args:
            session: Sessão com respostas

        Returns:
            Texto formatado com perguntas e respostas
        """
        lines = []

        for question_id, value in session.answers.items():
            # Encontrar pergunta
            question = next(
                (q for q in self.question_selector.catalog if q.id == question_id), None
            )

            if not question:
                continue

            # Formatar resposta
            if isinstance(value, list):
                value_str = ", ".join(str(v) for v in value)
            else:
                value_str = str(value)

            lines.append(f"**{question.text}**")
            lines.append(f"Resposta: {value_str}")
            lines.append("")

        return "\n".join(lines)

    def get_session(self, session_id: UUID) -> Optional[IntakeSession]:
        """Recupera sessão do cache/DB."""
        return self.sessions_cache.get(session_id)

    def get_question_by_id(self, question_id: str) -> Optional[Question]:
        """Recupera pergunta do catálogo pelo ID."""
        # Verificar no catálogo de perguntas geradas dinamicamente
        if hasattr(self, "question_catalog") and self.question_catalog:
            question = next((q for q in self.question_catalog if q.id == question_id), None)
            if question:
                return question

        # Fallback para catálogo legado se disponível
        if hasattr(self, "question_selector") and hasattr(self.question_selector, "catalog"):
            return next((q for q in self.question_selector.catalog if q.id == question_id), None)

        return None

    def get_engine_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do motor de intake V4.0."""
        stats = {
            "version": self.version,
            "single_agent_enabled": self.use_single_agent
            if hasattr(self, "use_single_agent")
            else False,
            "zep_memory_enabled": self.enable_zep_memory,
            "multi_agent_enabled": self.enable_multi_agent,  # Legacy
            "context_inference_enabled": self.enable_context_inference,  # Legacy
            "total_sessions": len(self.sessions_cache),
            "active_sessions": len(
                [s for s in self.sessions_cache.values() if s.status != IntakeStatus.SCOPED]
            ),
        }

        # Adicionar estatísticas do sistema atual
        if self.use_single_agent and hasattr(self, "single_agent_service"):
            stats["single_agent_stats"] = self.single_agent_service.get_service_stats()

        if hasattr(self, "memory_service") and self.memory_service:
            stats["memory_service_stats"] = self.memory_service.get_service_stats()

        # Estatísticas legadas (se disponíveis)
        if hasattr(self, "question_selector") and isinstance(
            self.question_selector, MultiAgentQuestionSelector
        ):
            stats["multi_agent_stats"] = self.question_selector.get_selection_stats()

        if hasattr(self, "context_inference_engine") and self.context_inference_engine:
            stats["context_inference_stats"] = self.context_inference_engine.get_inference_stats()

        if hasattr(self, "smart_question_filter") and self.smart_question_filter:
            stats["smart_filter_stats"] = self.smart_question_filter.get_filter_stats()

        return stats

    async def explain_question_selection(self, session_id: UUID) -> Optional[str]:
        """Explica como as perguntas foram selecionadas para uma sessão específica."""
        session = self.sessions_cache.get(session_id)
        if not session:
            return None

        selection_metadata = session.metadata.get("selection_metadata", {})

        explanation_parts = []
        explanation_parts.append("# Explicação da Seleção de Perguntas\n")
        explanation_parts.append(f"**Motor**: IntakeEngine V{self.version}\n")

        # Context inference explanation
        if selection_metadata.get("context_inference_used"):
            domain = selection_metadata.get("detected_domain", "N/A")
            explanation_parts.append("## Análise de Contexto")
            explanation_parts.append(f"- **Domínio detectado**: {domain}")

            inference_summary = selection_metadata.get("inference_summary")
            if inference_summary:
                explanation_parts.append(f"- **Resumo da análise**: {inference_summary}")

        # Smart filtering explanation
        if selection_metadata.get("smart_filtering_used"):
            filtered_count = selection_metadata.get("questions_filtered_count", 0)
            explanation_parts.append("## Filtragem Inteligente")
            explanation_parts.append(f"- **Perguntas redundantes removidas**: {filtered_count}")

            filter_explanation = selection_metadata.get("filter_explanation")
            if filter_explanation:
                explanation_parts.append(f"- **Detalhes**: {filter_explanation}")

        # Multi-agent explanation
        if self.enable_multi_agent:
            consensus_count = selection_metadata.get("consensus_reached_count", 0)
            explanation_parts.append("## Consenso Multi-Agent")
            explanation_parts.append(f"- **Perguntas com consenso**: {consensus_count}")

        explanation_parts.append(
            f"\n**Total de perguntas selecionadas**: {len(session.question_ids)}"
        )

        return "\n".join(explanation_parts)
