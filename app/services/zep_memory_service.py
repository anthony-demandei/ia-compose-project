"""
ZEP Memory Service - Serviço principal para gerenciar memória persistente
e contexto inteligente usando a plataforma ZEP.

Este serviço implementa:
- Gestão de usuários e sessões no ZEP
- Armazenamento de contexto de projetos
- Recuperação de contexto relevante para otimizar tokens
- Análise de padrões históricos para melhorar precisão
"""

import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from app.utils.zep_client import get_zep_client, ZepClientWrapper
from app.utils.pii_safe_logging import get_pii_safe_logger
from app.utils.knowledge_sanitizer import create_knowledge_sanitizer, KnowledgeSanitizer
from app.utils.technical_pattern_extractor import (
    create_technical_pattern_extractor,
    TechnicalPatternExtractor,
)
from app.models.intake import IntakeSession

logger = get_pii_safe_logger(__name__)


@dataclass
class ProjectContext:
    """Contexto de projeto para armazenamento no ZEP."""

    project_type: str
    domain: str
    complexity: str
    technologies: List[str]
    requirements: List[str]
    budget_range: Optional[str] = None
    timeline: Optional[str] = None
    similar_projects: List[str] = None


@dataclass
class ContextualInsight:
    """Insight contextual extraído da memória histórica."""

    insight_type: str  # "pattern", "preference", "requirement"
    description: str
    confidence: float
    project_examples: List[str]
    suggested_questions: List[str]


class ZepMemoryService:
    """
    Serviço principal para integração com ZEP Memory.

    Responsabilidades:
    - Gerenciar memória de usuários e sessões
    - Extrair contexto relevante para otimizar geração de perguntas
    - Identificar padrões em projetos similares
    - Armazenar e recuperar insights de projetos anteriores
    """

    def __init__(self):
        """Inicializa o serviço de memória ZEP com sanitização de conhecimento."""
        from app.utils.config import get_settings

        settings = get_settings()

        self.zep_client: ZepClientWrapper = get_zep_client()
        self.is_enabled = self.zep_client.is_available()

        # Configurar usuário universal
        self.universal_user_id = settings.zep_universal_user_id
        self.universal_user_email = settings.zep_universal_user_email
        self.universal_user_name = settings.zep_universal_user_name

        # Inicializar sistemas de sanitização
        self.knowledge_sanitizer: KnowledgeSanitizer = create_knowledge_sanitizer()
        self.pattern_extractor: TechnicalPatternExtractor = create_technical_pattern_extractor(
            settings.openai_api_key
        )

        if self.is_enabled:
            logger.info(
                f"ZepMemoryService initialized with universal user and knowledge sanitization: {self.universal_user_id}"
            )
        else:
            logger.warning("ZepMemoryService initialized without ZEP (fallback mode)")

    async def initialize_universal_session(self, project_identifier: str = None) -> Optional[str]:
        """
        Inicializa uma sessão usando o usuário universal do ZEP.

        Args:
            project_identifier: Identificador opcional do projeto (usado apenas para logs)

        Returns:
            ID da sessão ZEP ou None se erro
        """
        if not self.is_enabled:
            return None

        try:
            # Sempre usar o usuário universal configurado
            user = await self.zep_client.create_or_get_user(
                user_id=self.universal_user_id,
                email=self.universal_user_email,
                first_name=self.universal_user_name.split()[0],
                last_name=" ".join(self.universal_user_name.split()[1:])
                if len(self.universal_user_name.split()) > 1
                else "",
            )

            if user:
                # Gerar ID de sessão única para este intake
                project_suffix = f"_{project_identifier}" if project_identifier else ""
                session_id = f"intake{project_suffix}_{uuid.uuid4().hex[:8]}"
                logger.info(f"Initialized universal ZEP session: {session_id}")
                return session_id

            return None

        except Exception as e:
            logger.error(f"Error initializing universal session: {str(e)}")
            return None

    async def add_project_context(
        self,
        session_id: str,
        project_description: str,
        classification: Optional[Dict[str, Any]] = None,
        intake_session: Optional[IntakeSession] = None,
        client_identifier: str = None,
    ) -> bool:
        """
        Adiciona contexto técnico sanitizado à memória ZEP universal.
        Remove dados sensíveis e armazena apenas conhecimento reutilizável.

        Args:
            session_id: ID da sessão ZEP
            project_description: Descrição original do projeto (será sanitizada)
            classification: Classificação do projeto
            intake_session: Sessão de intake com respostas (serão sanitizadas)
            client_identifier: NÃO USADO - sistema é completamente anônimo

        Returns:
            True se sucesso, False se erro
        """
        if not self.is_enabled:
            return False

        try:
            # ETAPA 1: Sanitizar descrição do projeto
            sanitized_knowledge = self.knowledge_sanitizer.sanitize_project_description(
                project_description
            )

            if not sanitized_knowledge:
                logger.info(
                    "No technical knowledge to store - description too generic or insufficient"
                )
                return True  # Não é erro, apenas não há o que armazenar

            # ETAPA 2: Sanitizar respostas do wizard se disponível
            sanitized_answers = {}
            if intake_session and intake_session.answers:
                sanitized_answers = self.knowledge_sanitizer.sanitize_wizard_answers(
                    intake_session.answers
                )

            # ETAPA 3: Extrair padrões técnicos avançados
            technical_patterns = await self.pattern_extractor.extract_advanced_patterns(
                sanitized_text=project_description,  # Usar texto original para análise IA (será sanitizado internamente)
                domain=sanitized_knowledge.domain.value,
            )

            # ETAPA 4: Gerar insights arquiteturais
            architectural_insights = await self.pattern_extractor.extract_architectural_insights(
                patterns=technical_patterns, project_context=sanitized_knowledge.to_dict()
            )

            # ETAPA 5: Preparar mensagens técnicas sanitizadas para ZEP
            messages = []

            # Conhecimento técnico base
            knowledge_summary = (
                f"Padrão técnico identificado: Domínio={sanitized_knowledge.domain.value}, "
                f"Stack={', '.join(sanitized_knowledge.tech_stack[:3])}, "
                f"Complexidade={sanitized_knowledge.complexity_level}"
            )
            messages.append(
                {
                    "role_type": "assistant",
                    "role": "technical_analyzer",
                    "content": knowledge_summary,
                }
            )

            # Padrões técnicos identificados
            if technical_patterns:
                patterns_text = "Padrões: " + ", ".join(
                    [
                        f"{p.pattern_name} ({p.pattern_type})"
                        for p in technical_patterns[:5]  # Top 5 padrões
                    ]
                )
                messages.append(
                    {
                        "role_type": "assistant",
                        "role": "pattern_extractor",
                        "content": patterns_text,
                    }
                )

            # Insights arquiteturais
            if architectural_insights:
                for insight in architectural_insights[:3]:  # Top 3 insights
                    messages.append(
                        {
                            "role_type": "assistant",
                            "role": "architect",
                            "content": f"Insight {insight.insight_type}: {insight.description}",
                        }
                    )

            # Padrões das respostas sanitizadas
            if sanitized_answers:
                for category, patterns in sanitized_answers.items():
                    if patterns:
                        pattern_text = f"{category.title()}: {', '.join(patterns[:3])}"
                        messages.append(
                            {
                                "role_type": "assistant",
                                "role": "pattern_analyzer",
                                "content": pattern_text,
                            }
                        )

            # ETAPA 6: Armazenar na memória ZEP (sem dados sensíveis)
            success = await self.zep_client.add_memory(session_id, messages, self.universal_user_id)

            # ETAPA 7: Adicionar conhecimento estruturado ao grafo
            if success:
                # Dados completamente sanitizados para o grafo
                technical_data = sanitized_knowledge.to_dict()
                technical_data.update(
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "patterns_count": len(technical_patterns),
                        "insights_count": len(architectural_insights),
                        "session_type": "anonymous_technical_knowledge",
                    }
                )

                # IMPORTANTE: Não incluir client_identifier ou dados específicos
                await self.zep_client.add_business_data(self.universal_user_id, technical_data)

            if success:
                logger.info(
                    f"Added sanitized technical knowledge to ZEP: {sanitized_knowledge.domain.value} domain, {len(technical_patterns)} patterns"
                )

            return success

        except Exception as e:
            logger.error(f"Error adding project context: {str(e)}")
            return False

    async def get_relevant_context(
        self,
        current_project: str,
        classification: Optional[Dict[str, Any]] = None,
        client_identifier: str = None,
    ) -> Optional[str]:
        """
        Recupera contexto técnico relevante da memória histórica universal.
        Retorna apenas conhecimento sanitizado e reutilizável.

        Args:
            current_project: Descrição do projeto atual
            classification: Classificação do projeto atual
            client_identifier: IGNORADO - busca é anônima

        Returns:
            Contexto técnico sanitizado ou None se não disponível
        """
        if not self.is_enabled:
            return None

        try:
            # Buscar projetos similares na memória
            search_terms = current_project
            if classification:
                search_terms += (
                    f" {classification.get('type', '')} {classification.get('domain_context', '')}"
                )

            # Buscar na memória ZEP usando usuário universal
            memory_results = await self.zep_client.search_memory(
                text=search_terms, user_id=self.universal_user_id, limit=5
            )

            if not memory_results:
                return None

            # Construir contexto técnico sanitizado
            context_parts = []
            context_parts.append("CONHECIMENTO TÉCNICO HISTÓRICO:")

            # Filtrar apenas resultados com conteúdo técnico
            technical_results = []
            for result in memory_results[:5]:
                content = result.get("content", "")
                # Verificar se contém padrões técnicos
                if any(
                    keyword in content.lower()
                    for keyword in [
                        "padrão",
                        "stack",
                        "arquitetura",
                        "integração",
                        "tecnologia",
                        "insight",
                    ]
                ):
                    technical_results.append(content)

            for i, content in enumerate(technical_results[:3]):  # Top 3 resultados técnicos
                context_parts.append(f"{i+1}. {content[:150]}")

            # Adicionar resumo técnico do grafo universal
            graph_summary = await self.zep_client.get_user_graph_summary(self.universal_user_id)
            if graph_summary:
                context_parts.append(f"\nPADRÕES IDENTIFICADOS: {graph_summary}")

            # Se não há contexto técnico, retornar None
            if len(context_parts) <= 1:
                logger.info("No relevant technical context found in universal memory")
                return None

            context = "\n".join(context_parts)
            logger.info(
                f"Retrieved {len(technical_results)} relevant technical contexts from universal memory"
            )
            return context

        except Exception as e:
            logger.error(f"Error retrieving relevant context: {str(e)}")
            return None

    async def extract_contextual_insights(
        self, current_project: str, client_identifier: str = None
    ) -> List[ContextualInsight]:
        """
        Extrai insights técnicos da memória histórica universal sanitizada.
        Retorna apenas padrões e conhecimento reutilizável.

        Args:
            current_project: Descrição do projeto atual
            client_identifier: IGNORADO - análise é anônima

        Returns:
            Lista de insights técnicos contextuais
        """
        if not self.is_enabled:
            return []

        try:
            # Buscar projetos históricos usando usuário universal
            memory_results = await self.zep_client.search_memory(
                text=current_project, user_id=self.universal_user_id, limit=10
            )

            if not memory_results:
                return []

            insights = []

            # Analisar padrões técnicos nos projetos históricos
            # Focar em insights técnicos reutilizáveis, não em dados específicos do cliente

            if len(memory_results) >= 2:
                insights.append(
                    ContextualInsight(
                        insight_type="technical_pattern",
                        description=f"Encontrados {len(memory_results)} projetos similares com padrões técnicos relacionados",
                        confidence=0.8,
                        project_examples=[],  # Não incluir IDs específicos
                        suggested_questions=[
                            "Este projeto pode se beneficiar dos padrões técnicos já validados?",
                            "Há lições arquiteturais dos projetos similares que devemos considerar?",
                        ],
                    )
                )

            # Identificar tendências tecnológicas (sem vincular a clientes específicos)
            tech_mentions = self._extract_technology_mentions(memory_results)
            if tech_mentions:
                insights.append(
                    ContextualInsight(
                        insight_type="technology_trend",
                        description=f"Tecnologias frequentes em projetos similares: {', '.join(tech_mentions[:3])}",
                        confidence=0.7,
                        project_examples=[],
                        suggested_questions=[
                            f"Considerar usar {tech_mentions[0]} baseado em experiência anterior?",
                            "Há vantagem em seguir padrões tecnológicos já validados?",
                        ],
                    )
                )

            logger.info(f"Extracted {len(insights)} technical insights from universal memory")
            return insights

        except Exception as e:
            logger.error(f"Error extracting contextual insights: {str(e)}")
            return []

    def _format_sanitized_answers(self, sanitized_answers: Dict[str, List[str]]) -> str:
        """Formata padrões técnicos extraídos das respostas para memória."""
        formatted = []
        for category, patterns in sanitized_answers.items():
            if patterns:
                patterns_str = ", ".join(patterns[:3])  # Top 3 por categoria
                formatted.append(f"{category}: {patterns_str}")

        return "; ".join(formatted)

    def _extract_technology_mentions(self, memory_results: List[Dict[str, Any]]) -> List[str]:
        """Extrai menções de tecnologias dos resultados da memória."""
        # Lista básica de tecnologias para detectar
        technologies = [
            "React",
            "Vue",
            "Angular",
            "Laravel",
            "Django",
            "Node.js",
            "Python",
            "PHP",
            "JavaScript",
            "Java",
            "C#",
            "MySQL",
            "PostgreSQL",
            "MongoDB",
            "Redis",
            "Docker",
            "AWS",
            "GCP",
        ]

        found_technologies = []

        for result in memory_results:
            content = result.get("content", "").lower()
            for tech in technologies:
                if tech.lower() in content and tech not in found_technologies:
                    found_technologies.append(tech)

        return found_technologies

    async def store_project_completion(
        self, session_id: str, final_scope: str, success: bool = True, client_identifier: str = None
    ) -> bool:
        """
        Armazena insights arquiteturais sanitizados do projeto finalizado.
        Remove dados sensíveis do escopo e armazena apenas conhecimento técnico.

        Args:
            session_id: ID da sessão ZEP
            final_scope: Escopo final gerado (será sanitizado)
            success: Se o processo foi concluído com sucesso
            client_identifier: IGNORADO - sistema é completamente anônimo

        Returns:
            True se sucesso, False se erro
        """
        if not self.is_enabled:
            return False

        try:
            # ETAPA 1: Sanitizar escopo final para extrair apenas insights arquiteturais
            sanitized_scope_insights = self.knowledge_sanitizer.sanitize_project_scope(final_scope)

            if not sanitized_scope_insights:
                logger.info("No architectural insights to store from project completion")
                return True

            # ETAPA 2: Criar mensagens com insights sanitizados
            messages = []

            # Status de conclusão (sem dados do cliente)
            completion_message = {
                "role_type": "assistant",
                "role": "project_completion",
                "content": f"Projeto técnico finalizado {'com sucesso' if success else 'com problemas'}. "
                f"Insights arquiteturais extraídos: {len(sanitized_scope_insights)} categorias.",
            }
            messages.append(completion_message)

            # ETAPA 3: Adicionar insights específicos
            for insight_type, insights in sanitized_scope_insights.items():
                if insights:
                    insight_message = {
                        "role_type": "assistant",
                        "role": "architectural_insight",
                        "content": f"{insight_type}: {', '.join(insights[:3])}",
                    }
                    messages.append(insight_message)

            # ETAPA 4: Armazenar conhecimento final sanitizado
            success_result = await self.zep_client.add_memory(
                session_id, messages, self.universal_user_id
            )

            # ETAPA 5: Adicionar dados estruturados de conclusão
            if success_result:
                completion_data = {
                    "event_type": "project_completion",
                    "success": success,
                    "insights_extracted": list(sanitized_scope_insights.keys()),
                    "insights_count": sum(
                        len(insights) for insights in sanitized_scope_insights.values()
                    ),
                    "timestamp": datetime.utcnow().isoformat(),
                    "completion_type": "anonymous_technical_completion",
                }

                await self.zep_client.add_business_data(self.universal_user_id, completion_data)
                logger.info(
                    f"Stored sanitized project completion insights: {len(sanitized_scope_insights)} categories"
                )

            return success_result

        except Exception as e:
            logger.error(f"Error storing project completion: {str(e)}")
            return False

    def get_service_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do serviço de memória."""
        return {
            "zep_enabled": self.is_enabled,
            "client_available": self.zep_client.is_available() if self.zep_client else False,
            "service_version": "1.0.0",
        }
