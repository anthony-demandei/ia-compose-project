"""
Context Manager for Multi-Agent Intelligent Intake System.
Manages session state, cross-agent communication, and context preservation.
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import redis.asyncio as redis
from datetime import datetime

from app.models.intake import IntakeSession
from app.services.advanced_scoring_engine import QuestionScore, ScoringContext
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


class ContextScope(Enum):
    """Escopo do contexto para controle de acesso."""

    SESSION = "session"  # Dados da sessão específica
    AGENT = "agent"  # Dados específicos de um agent
    GLOBAL = "global"  # Dados compartilhados entre agents
    SYSTEM = "system"  # Dados do sistema/configuração


class ContextEventType(Enum):
    """Tipos de eventos de contexto."""

    SESSION_CREATED = "session_created"
    SESSION_UPDATED = "session_updated"
    AGENT_CONSULTED = "agent_consulted"
    QUESTIONS_SELECTED = "questions_selected"
    ANSWER_SUBMITTED = "answer_submitted"
    CONSENSUS_REACHED = "consensus_reached"
    CONTEXT_SYNCHRONIZED = "context_synchronized"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class ContextEvent:
    """Evento de contexto para auditoria e sincronização."""

    event_type: ContextEventType
    session_id: str
    agent_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentContext:
    """Contexto específico de um agent."""

    agent_id: str
    session_id: str
    last_consulted: datetime
    recommendations: List[str] = field(default_factory=list)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    reasoning: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionContext:
    """Contexto completo de uma sessão."""

    session_id: str
    intake_session: IntakeSession
    scoring_context: ScoringContext
    agent_contexts: Dict[str, AgentContext] = field(default_factory=dict)
    question_scores: List[QuestionScore] = field(default_factory=list)
    selected_questions: List[str] = field(default_factory=list)
    consensus_data: Dict[str, Any] = field(default_factory=dict)
    events: List[ContextEvent] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    version: int = 1


class ContextManager:
    """
    Gerenciador de contexto avançado para sistema multi-agent.

    Fornece:
    - Persistência de estado cross-session
    - Comunicação entre agents
    - Sincronização de contexto
    - Auditoria de eventos
    - Cache inteligente
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        encryption_key: Optional[str] = None,
        ttl_hours: int = 24,
    ):
        """
        Inicializa o gerenciador de contexto.

        Args:
            redis_url: URL do Redis para persistência
            encryption_key: Chave para criptografia de dados sensíveis
            ttl_hours: TTL padrão para dados em horas
        """
        self.redis_url = redis_url
        self.encryption_key = encryption_key
        self.ttl_hours = ttl_hours
        self.ttl_seconds = ttl_hours * 3600

        # Connection pool
        self.redis_pool = None
        self.redis_client = None

        # Cache local para performance
        self.local_cache: Dict[str, SessionContext] = {}
        self.cache_ttl = {}

        # Event subscribers
        self.event_subscribers: Dict[ContextEventType, List[callable]] = {}

        # Prefixes para organização no Redis
        self.prefixes = {
            ContextScope.SESSION: "ctx:session:",
            ContextScope.AGENT: "ctx:agent:",
            ContextScope.GLOBAL: "ctx:global:",
            ContextScope.SYSTEM: "ctx:system:",
        }

        logger.info("Context Manager initialized")

    async def initialize(self):
        """Inicializa conexões e recursos."""
        try:
            self.redis_pool = redis.ConnectionPool.from_url(
                self.redis_url, max_connections=20, retry_on_timeout=True
            )
            self.redis_client = redis.Redis(connection_pool=self.redis_pool)

            # Teste de conexão
            await self.redis_client.ping()
            logger.info("Redis connection established")

            # Setup cleanup task
            asyncio.create_task(self._cleanup_expired_contexts())

        except Exception as e:
            logger.error(f"Failed to initialize context manager: {str(e)}")
            # Fallback para cache local apenas
            logger.warning("Falling back to local cache only")

    async def create_session_context(
        self, intake_session: IntakeSession, scoring_context: ScoringContext
    ) -> SessionContext:
        """Cria novo contexto de sessão."""
        try:
            session_context = SessionContext(
                session_id=str(intake_session.id),
                intake_session=intake_session,
                scoring_context=scoring_context,
            )

            # Salvar contexto
            await self._save_context(session_context, ContextScope.SESSION)

            # Registrar evento
            event = ContextEvent(
                event_type=ContextEventType.SESSION_CREATED,
                session_id=session_context.session_id,
                data={"intake_text_length": len(intake_session.intake_text)},
            )
            await self._emit_event(event)

            logger.info(f"Session context created: {session_context.session_id}")
            return session_context

        except Exception as e:
            logger.error(f"Error creating session context: {str(e)}")
            raise

    async def get_session_context(self, session_id: str) -> Optional[SessionContext]:
        """Recupera contexto de sessão."""
        try:
            # Verificar cache local primeiro
            if session_id in self.local_cache:
                if self._is_cache_valid(session_id):
                    return self.local_cache[session_id]
                else:
                    del self.local_cache[session_id]
                    del self.cache_ttl[session_id]

            # Buscar no Redis
            context = await self._load_context(session_id, ContextScope.SESSION)

            if context:
                # Atualizar cache local
                self.local_cache[session_id] = context
                self.cache_ttl[session_id] = time.time() + 300  # 5 min TTL local

                return context

            return None

        except Exception as e:
            logger.error(f"Error getting session context: {str(e)}")
            return None

    async def update_session_context(
        self, session_context: SessionContext, increment_version: bool = True
    ) -> bool:
        """Atualiza contexto de sessão."""
        try:
            if increment_version:
                session_context.version += 1

            session_context.updated_at = datetime.utcnow()

            # Salvar no Redis
            await self._save_context(session_context, ContextScope.SESSION)

            # Atualizar cache local
            self.local_cache[session_context.session_id] = session_context
            self.cache_ttl[session_context.session_id] = time.time() + 300

            # Registrar evento
            event = ContextEvent(
                event_type=ContextEventType.SESSION_UPDATED,
                session_id=session_context.session_id,
                data={"version": session_context.version},
            )
            await self._emit_event(event)

            return True

        except Exception as e:
            logger.error(f"Error updating session context: {str(e)}")
            return False

    async def add_agent_context(
        self,
        session_id: str,
        agent_id: str,
        recommendations: List[str],
        confidence_scores: Dict[str, float],
        reasoning: List[str],
        metadata: Dict[str, Any] = None,
    ) -> bool:
        """Adiciona contexto de um agent."""
        try:
            agent_context = AgentContext(
                agent_id=agent_id,
                session_id=session_id,
                last_consulted=datetime.utcnow(),
                recommendations=recommendations,
                confidence_scores=confidence_scores,
                reasoning=reasoning,
                metadata=metadata or {},
            )

            # Obter contexto da sessão
            session_context = await self.get_session_context(session_id)
            if not session_context:
                logger.error(f"Session context not found: {session_id}")
                return False

            # Adicionar agent context
            session_context.agent_contexts[agent_id] = agent_context

            # Atualizar sessão
            await self.update_session_context(session_context)

            # Salvar agent context separadamente para queries
            agent_key = f"{session_id}:{agent_id}"
            await self._save_context(agent_context, ContextScope.AGENT, agent_key)

            # Registrar evento
            event = ContextEvent(
                event_type=ContextEventType.AGENT_CONSULTED,
                session_id=session_id,
                agent_id=agent_id,
                data={
                    "recommendations_count": len(recommendations),
                    "avg_confidence": sum(confidence_scores.values()) / len(confidence_scores)
                    if confidence_scores
                    else 0,
                },
            )
            await self._emit_event(event)

            logger.info(f"Agent context added: {agent_id} for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error adding agent context: {str(e)}")
            return False

    async def get_agent_context(self, session_id: str, agent_id: str) -> Optional[AgentContext]:
        """Recupera contexto de um agent específico."""
        try:
            # Tentar da sessão primeiro
            session_context = await self.get_session_context(session_id)
            if session_context and agent_id in session_context.agent_contexts:
                return session_context.agent_contexts[agent_id]

            # Tentar busca direta
            agent_key = f"{session_id}:{agent_id}"
            agent_context = await self._load_context(agent_key, ContextScope.AGENT)

            return agent_context

        except Exception as e:
            logger.error(f"Error getting agent context: {str(e)}")
            return None

    async def build_consensus(
        self,
        session_id: str,
        question_scores: List[QuestionScore],
        consensus_threshold: float = 0.7,
    ) -> Dict[str, Any]:
        """Constrói consenso entre agents."""
        try:
            session_context = await self.get_session_context(session_id)
            if not session_context:
                return {}

            agent_contexts = session_context.agent_contexts
            if len(agent_contexts) < 2:
                logger.warning("Insufficient agents for consensus building")
                return {"consensus_reached": False, "reason": "insufficient_agents"}

            # Analisar votos dos agents
            consensus_data = {
                "total_agents": len(agent_contexts),
                "question_consensus": {},
                "consensus_reached": False,
                "confidence": 0.0,
                "disagreements": [],
            }

            # Para cada pergunta, calcular consenso
            for score in question_scores:
                question_id = score.question_id
                agent_votes = score.agent_votes

                if len(agent_votes) >= 2:
                    votes = list(agent_votes.values())
                    avg_vote = sum(votes) / len(votes)
                    vote_std = self._calculate_std(votes)

                    # Consenso se desvio padrão baixo
                    has_consensus = vote_std < (1.0 - consensus_threshold)

                    consensus_data["question_consensus"][question_id] = {
                        "avg_score": avg_vote,
                        "std_dev": vote_std,
                        "has_consensus": has_consensus,
                        "votes": agent_votes,
                    }

                    if not has_consensus:
                        consensus_data["disagreements"].append(
                            {"question_id": question_id, "votes": agent_votes, "std_dev": vote_std}
                        )

            # Calcular consenso geral
            consensus_questions = [
                q for q in consensus_data["question_consensus"].values() if q["has_consensus"]
            ]

            if len(consensus_questions) >= len(question_scores) * consensus_threshold:
                consensus_data["consensus_reached"] = True
                consensus_data["confidence"] = len(consensus_questions) / len(question_scores)

            # Salvar dados de consenso
            session_context.consensus_data = consensus_data
            await self.update_session_context(session_context)

            # Registrar evento
            event = ContextEvent(
                event_type=ContextEventType.CONSENSUS_REACHED,
                session_id=session_id,
                data=consensus_data,
            )
            await self._emit_event(event)

            return consensus_data

        except Exception as e:
            logger.error(f"Error building consensus: {str(e)}")
            return {}

    async def synchronize_contexts(self, session_ids: List[str]) -> bool:
        """Sincroniza contextos entre sessões."""
        try:
            sync_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "session_count": len(session_ids),
                "common_patterns": {},
                "shared_insights": [],
            }

            contexts = []
            for session_id in session_ids:
                context = await self.get_session_context(session_id)
                if context:
                    contexts.append(context)

            if len(contexts) < 2:
                return False

            # Identificar padrões comuns
            common_tags = self._find_common_tags(contexts)
            common_industries = self._find_common_industries(contexts)
            common_questions = self._find_common_questions(contexts)

            sync_data["common_patterns"] = {
                "tags": common_tags,
                "industries": common_industries,
                "questions": common_questions,
            }

            # Gerar insights compartilhados
            insights = self._generate_shared_insights(contexts)
            sync_data["shared_insights"] = insights

            # Salvar sincronização global
            await self._save_context(sync_data, ContextScope.GLOBAL, "synchronization")

            # Registrar evento
            event = ContextEvent(
                event_type=ContextEventType.CONTEXT_SYNCHRONIZED,
                session_id="global",
                data=sync_data,
            )
            await self._emit_event(event)

            logger.info(f"Synchronized {len(contexts)} contexts")
            return True

        except Exception as e:
            logger.error(f"Error synchronizing contexts: {str(e)}")
            return False

    async def get_session_analytics(self, session_id: str) -> Dict[str, Any]:
        """Retorna analytics da sessão."""
        try:
            session_context = await self.get_session_context(session_id)
            if not session_context:
                return {}

            analytics = {
                "session_info": {
                    "session_id": session_id,
                    "created_at": session_context.created_at.isoformat(),
                    "updated_at": session_context.updated_at.isoformat(),
                    "version": session_context.version,
                    "duration": str(session_context.updated_at - session_context.created_at),
                },
                "agent_participation": {},
                "question_analysis": {},
                "consensus_analysis": session_context.consensus_data,
                "events_timeline": [],
            }

            # Análise de participação dos agents
            for agent_id, agent_context in session_context.agent_contexts.items():
                analytics["agent_participation"][agent_id] = {
                    "last_consulted": agent_context.last_consulted.isoformat(),
                    "recommendations_count": len(agent_context.recommendations),
                    "avg_confidence": (
                        sum(agent_context.confidence_scores.values())
                        / len(agent_context.confidence_scores)
                        if agent_context.confidence_scores
                        else 0
                    ),
                    "reasoning_points": len(agent_context.reasoning),
                }

            # Análise das perguntas
            if session_context.question_scores:
                scores = [s.total_score for s in session_context.question_scores]
                analytics["question_analysis"] = {
                    "total_questions": len(session_context.question_scores),
                    "avg_score": sum(scores) / len(scores),
                    "max_score": max(scores),
                    "min_score": min(scores),
                    "high_confidence_count": len(
                        [s for s in session_context.question_scores if s.confidence > 0.8]
                    ),
                }

            # Timeline de eventos
            analytics["events_timeline"] = [
                {
                    "event_type": event.event_type.value,
                    "timestamp": event.timestamp.isoformat(),
                    "agent_id": event.agent_id,
                    "data": event.data,
                }
                for event in session_context.events[-10:]  # Últimos 10 eventos
            ]

            return analytics

        except Exception as e:
            logger.error(f"Error getting session analytics: {str(e)}")
            return {}

    async def subscribe_to_events(self, event_type: ContextEventType, callback: callable):
        """Registra callback para eventos de contexto."""
        if event_type not in self.event_subscribers:
            self.event_subscribers[event_type] = []

        self.event_subscribers[event_type].append(callback)
        logger.info(f"Event subscriber registered for {event_type.value}")

    async def _save_context(self, context: Any, scope: ContextScope, key_suffix: str = None):
        """Salva contexto no Redis."""
        if not self.redis_client:
            return

        try:
            # Gerar chave
            if isinstance(context, SessionContext):
                key = f"{self.prefixes[scope]}{context.session_id}"
            elif key_suffix:
                key = f"{self.prefixes[scope]}{key_suffix}"
            else:
                key = f"{self.prefixes[scope]}{id(context)}"

            # Serializar contexto
            if hasattr(context, "__dict__"):
                data = (
                    asdict(context)
                    if hasattr(context, "__dataclass_fields__")
                    else context.__dict__
                )
            else:
                data = context

            # Criptografar dados sensíveis se necessário
            if self.encryption_key and scope in [ContextScope.SESSION, ContextScope.AGENT]:
                data = self._encrypt_sensitive_data(data)

            serialized = json.dumps(data, default=str)

            # Salvar com TTL
            await self.redis_client.setex(key, self.ttl_seconds, serialized)

        except Exception as e:
            logger.error(f"Error saving context: {str(e)}")

    async def _load_context(self, key: str, scope: ContextScope) -> Any:
        """Carrega contexto do Redis."""
        if not self.redis_client:
            return None

        try:
            # Buscar dados
            redis_key = f"{self.prefixes[scope]}{key}"
            serialized = await self.redis_client.get(redis_key)

            if not serialized:
                return None

            data = json.loads(serialized)

            # Descriptografar se necessário
            if self.encryption_key and scope in [ContextScope.SESSION, ContextScope.AGENT]:
                data = self._decrypt_sensitive_data(data)

            # Reconstruir objeto baseado no scope
            if scope == ContextScope.SESSION:
                return self._reconstruct_session_context(data)
            elif scope == ContextScope.AGENT:
                return self._reconstruct_agent_context(data)
            else:
                return data

        except Exception as e:
            logger.error(f"Error loading context: {str(e)}")
            return None

    def _reconstruct_session_context(self, data: Dict[str, Any]) -> SessionContext:
        """Reconstrói SessionContext a partir dos dados."""
        # Converter timestamps
        if "created_at" in data:
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        # Reconstruir objetos aninhados
        if "agent_contexts" in data:
            agent_contexts = {}
            for agent_id, agent_data in data["agent_contexts"].items():
                agent_contexts[agent_id] = self._reconstruct_agent_context(agent_data)
            data["agent_contexts"] = agent_contexts

        # Reconstruir eventos
        if "events" in data:
            events = []
            for event_data in data["events"]:
                event = ContextEvent(
                    event_type=ContextEventType(event_data["event_type"]),
                    session_id=event_data["session_id"],
                    agent_id=event_data.get("agent_id"),
                    timestamp=datetime.fromisoformat(event_data["timestamp"]),
                    data=event_data.get("data", {}),
                    metadata=event_data.get("metadata", {}),
                )
                events.append(event)
            data["events"] = events

        # Note: IntakeSession e ScoringContext precisariam de reconstrução similar
        # Por simplicidade, mantendo como dict por enquanto

        return SessionContext(**data)

    def _reconstruct_agent_context(self, data: Dict[str, Any]) -> AgentContext:
        """Reconstrói AgentContext a partir dos dados."""
        if "last_consulted" in data:
            data["last_consulted"] = datetime.fromisoformat(data["last_consulted"])

        return AgentContext(**data)

    async def _emit_event(self, event: ContextEvent):
        """Emite evento para subscribers."""
        try:
            # Adicionar ao contexto da sessão
            if event.session_id != "global":
                session_context = await self.get_session_context(event.session_id)
                if session_context:
                    session_context.events.append(event)
                    await self.update_session_context(session_context, increment_version=False)

            # Notificar subscribers
            subscribers = self.event_subscribers.get(event.event_type, [])
            for callback in subscribers:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"Error in event subscriber: {str(e)}")

        except Exception as e:
            logger.error(f"Error emitting event: {str(e)}")

    def _is_cache_valid(self, session_id: str) -> bool:
        """Verifica se cache local é válido."""
        return session_id in self.cache_ttl and time.time() < self.cache_ttl[session_id]

    def _calculate_std(self, values: List[float]) -> float:
        """Calcula desvio padrão."""
        if len(values) <= 1:
            return 0.0

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance**0.5

    def _find_common_tags(self, contexts: List[SessionContext]) -> List[str]:
        """Identifica tags comuns entre contextos."""
        all_tags = []
        for context in contexts:
            if hasattr(context.scoring_context, "classified_tags"):
                all_tags.extend(context.scoring_context.classified_tags)

        # Contar frequência
        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Retornar tags que aparecem em pelo menos 50% dos contextos
        threshold = len(contexts) * 0.5
        return [tag for tag, count in tag_counts.items() if count >= threshold]

    def _find_common_industries(self, contexts: List[SessionContext]) -> List[str]:
        """Identifica indústrias comuns."""
        industries = []
        for context in contexts:
            if (
                hasattr(context.scoring_context, "detected_industry")
                and context.scoring_context.detected_industry
            ):
                industries.append(context.scoring_context.detected_industry)

        # Retornar indústrias únicas
        return list(set(industries))

    def _find_common_questions(self, contexts: List[SessionContext]) -> List[str]:
        """Identifica perguntas comuns selecionadas."""
        all_questions = []
        for context in contexts:
            all_questions.extend(context.selected_questions)

        # Contar frequência
        question_counts = {}
        for question in all_questions:
            question_counts[question] = question_counts.get(question, 0) + 1

        # Retornar top 10 mais comuns
        sorted_questions = sorted(question_counts.items(), key=lambda x: x[1], reverse=True)
        return [q[0] for q in sorted_questions[:10]]

    def _generate_shared_insights(self, contexts: List[SessionContext]) -> List[str]:
        """Gera insights compartilhados entre sessões."""
        insights = []

        # Insight sobre patterns de perguntas
        common_questions = self._find_common_questions(contexts)
        if common_questions:
            insights.append(f"Top 3 perguntas mais selecionadas: {', '.join(common_questions[:3])}")

        # Insight sobre consenso dos agents
        consensus_rates = []
        for context in contexts:
            if context.consensus_data and "consensus_reached" in context.consensus_data:
                if context.consensus_data["consensus_reached"]:
                    consensus_rates.append(context.consensus_data.get("confidence", 0))

        if consensus_rates:
            avg_consensus = sum(consensus_rates) / len(consensus_rates)
            insights.append(f"Taxa média de consenso entre agents: {avg_consensus:.2f}")

        # Insight sobre complexidade
        complexity_distribution = {}
        for context in contexts:
            complexity = getattr(context.scoring_context, "project_complexity", "medium")
            complexity_distribution[complexity] = complexity_distribution.get(complexity, 0) + 1

        if complexity_distribution:
            most_common_complexity = max(complexity_distribution.items(), key=lambda x: x[1])
            insights.append(
                f"Complexidade mais comum: {most_common_complexity[0]} ({most_common_complexity[1]} sessões)"
            )

        return insights

    def _encrypt_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Criptografa dados sensíveis (placeholder)."""
        # Implementação real usaria criptografia adequada
        return data

    def _decrypt_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Descriptografa dados sensíveis (placeholder)."""
        # Implementação real usaria descriptografia adequada
        return data

    async def _cleanup_expired_contexts(self):
        """Task para limpeza de contextos expirados."""
        while True:
            try:
                await asyncio.sleep(3600)  # Rodar a cada hora

                if not self.redis_client:
                    continue

                # Limpar cache local expirado
                current_time = time.time()
                expired_keys = [key for key, ttl in self.cache_ttl.items() if current_time > ttl]

                for key in expired_keys:
                    del self.local_cache[key]
                    del self.cache_ttl[key]

                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

            except Exception as e:
                logger.error(f"Error in cleanup task: {str(e)}")

    async def close(self):
        """Fecha conexões e limpa recursos."""
        try:
            if self.redis_client:
                await self.redis_client.close()

            if self.redis_pool:
                await self.redis_pool.disconnect()

            logger.info("Context Manager closed")

        except Exception as e:
            logger.error(f"Error closing context manager: {str(e)}")

    async def health_check(self) -> Dict[str, Any]:
        """Verifica saúde do gerenciador de contexto."""
        health = {
            "status": "healthy",
            "redis_connected": False,
            "local_cache_size": len(self.local_cache),
            "event_subscribers": len(self.event_subscribers),
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            if self.redis_client:
                await self.redis_client.ping()
                health["redis_connected"] = True
        except Exception as e:
            health["redis_error"] = str(e)
            health["status"] = "degraded"

        return health
