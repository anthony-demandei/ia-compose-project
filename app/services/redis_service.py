from typing import Optional, List, Dict, Any
import json
import logging
from datetime import datetime
import redis.asyncio as redis
from app.models.session import DiscoverySession, Message
from app.utils.config import get_settings

logger = logging.getLogger(__name__)


class RedisService:
    """
    Serviço Redis para cache de conversas e sessões.
    Melhora performance e permite limpeza rápida de conversas.
    """

    def __init__(self, redis_url: str, password: str = None):
        self.redis_url = redis_url
        self.password = password
        self.redis_client = None

        # Prefixos para diferentes tipos de dados
        self.SESSION_PREFIX = "session:"
        self.CONVERSATION_PREFIX = "conversation:"
        self.STAGE_PREFIX = "stage:"

        # TTL padrão (1 hora)
        self.DEFAULT_TTL = 3600

    async def connect(self):
        """Conecta ao Redis."""
        try:
            self.redis_client = redis.from_url(
                self.redis_url, password=self.password, decode_responses=True, encoding="utf-8"
            )

            # Testar conexão
            await self.redis_client.ping()
            logger.info("Conectado ao Redis com sucesso")

        except Exception as e:
            logger.error(f"Erro ao conectar ao Redis: {str(e)}")
            self.redis_client = None

    async def disconnect(self):
        """Desconecta do Redis."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Desconectado do Redis")

    async def is_connected(self) -> bool:
        """Verifica se está conectado ao Redis."""
        if not self.redis_client:
            return False

        try:
            await self.redis_client.ping()
            return True
        except:
            return False

    async def cache_session(self, session: DiscoverySession, ttl: int = None) -> bool:
        """
        Armazena sessão no cache Redis.

        Args:
            session: Sessão a ser cached
            ttl: Time to live em segundos

        Returns:
            True se sucesso
        """
        if not await self.is_connected():
            return False

        try:
            session_key = f"{self.SESSION_PREFIX}{session.id}"

            # Serializar sessão (sem mensagens para economizar espaço)
            session_data = {
                "id": session.id,
                "current_stage": session.current_stage.value,
                "requirements": session.requirements.dict(),
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "version": session.version,
                "is_completed": session.is_completed,
                "document_uris": session.document_uris,
                "message_count": len(session.messages),
            }

            await self.redis_client.set(
                session_key,
                json.dumps(session_data, ensure_ascii=False),
                ex=ttl or self.DEFAULT_TTL,
            )

            logger.debug(f"Sessão cached: {session.id}")
            return True

        except Exception as e:
            logger.error(f"Erro ao fazer cache da sessão {session.id}: {str(e)}")
            return False

    async def get_cached_session(self, session_id: str) -> Optional[Dict]:
        """
        Recupera sessão do cache Redis.

        Args:
            session_id: ID da sessão

        Returns:
            Dados da sessão ou None
        """
        if not await self.is_connected():
            return None

        try:
            session_key = f"{self.SESSION_PREFIX}{session_id}"
            cached_data = await self.redis_client.get(session_key)

            if cached_data:
                return json.loads(cached_data)

            return None

        except Exception as e:
            logger.error(f"Erro ao recuperar sessão do cache {session_id}: {str(e)}")
            return None

    async def cache_conversation(
        self, session_id: str, messages: List[Message], ttl: int = None
    ) -> bool:
        """
        Armazena conversação no cache Redis.

        Args:
            session_id: ID da sessão
            messages: Lista de mensagens
            ttl: Time to live em segundos

        Returns:
            True se sucesso
        """
        if not await self.is_connected():
            return False

        try:
            conv_key = f"{self.CONVERSATION_PREFIX}{session_id}"

            # Serializar mensagens
            messages_data = []
            for msg in messages:
                msg_data = {
                    "id": msg.id,
                    "content": msg.content,
                    "sender": msg.sender.value,
                    "timestamp": msg.timestamp.isoformat(),
                    "stage": msg.stage.value,
                    "metadata": msg.metadata or {},
                }
                messages_data.append(msg_data)

            await self.redis_client.set(
                conv_key, json.dumps(messages_data, ensure_ascii=False), ex=ttl or self.DEFAULT_TTL
            )

            logger.debug(f"Conversação cached: {session_id} ({len(messages)} mensagens)")
            return True

        except Exception as e:
            logger.error(f"Erro ao fazer cache da conversação {session_id}: {str(e)}")
            return False

    async def get_cached_conversation(self, session_id: str) -> List[Dict]:
        """
        Recupera conversação do cache Redis.

        Args:
            session_id: ID da sessão

        Returns:
            Lista de mensagens ou lista vazia
        """
        if not await self.is_connected():
            return []

        try:
            conv_key = f"{self.CONVERSATION_PREFIX}{session_id}"
            cached_data = await self.redis_client.get(conv_key)

            if cached_data:
                return json.loads(cached_data)

            return []

        except Exception as e:
            logger.error(f"Erro ao recuperar conversação do cache {session_id}: {str(e)}")
            return []

    async def clear_conversation(self, session_id: str) -> bool:
        """
        Limpa conversação do cache (para Nova Tarefa).

        Args:
            session_id: ID da sessão

        Returns:
            True se sucesso
        """
        if not await self.is_connected():
            return False

        try:
            conv_key = f"{self.CONVERSATION_PREFIX}{session_id}"
            result = await self.redis_client.delete(conv_key)

            logger.info(f"Conversação limpa do cache: {session_id}")
            return result > 0

        except Exception as e:
            logger.error(f"Erro ao limpar conversação {session_id}: {str(e)}")
            return False

    async def cache_stage_progress(self, session_id: str, stage: str, progress_data: Dict) -> bool:
        """
        Armazena progresso de um estágio específico.

        Args:
            session_id: ID da sessão
            stage: Nome do estágio
            progress_data: Dados do progresso

        Returns:
            True se sucesso
        """
        if not await self.is_connected():
            return False

        try:
            stage_key = f"{self.STAGE_PREFIX}{session_id}:{stage}"

            progress_with_timestamp = {**progress_data, "cached_at": datetime.utcnow().isoformat()}

            await self.redis_client.set(
                stage_key,
                json.dumps(progress_with_timestamp, ensure_ascii=False),
                ex=self.DEFAULT_TTL,
            )

            logger.debug(f"Progresso do estágio cached: {session_id}:{stage}")
            return True

        except Exception as e:
            logger.error(f"Erro ao fazer cache do progresso {session_id}:{stage}: {str(e)}")
            return False

    async def get_stage_progress(self, session_id: str, stage: str) -> Optional[Dict]:
        """
        Recupera progresso de um estágio específico.

        Args:
            session_id: ID da sessão
            stage: Nome do estágio

        Returns:
            Dados do progresso ou None
        """
        if not await self.is_connected():
            return None

        try:
            stage_key = f"{self.STAGE_PREFIX}{session_id}:{stage}"
            cached_data = await self.redis_client.get(stage_key)

            if cached_data:
                return json.loads(cached_data)

            return None

        except Exception as e:
            logger.error(f"Erro ao recuperar progresso do estágio {session_id}:{stage}: {str(e)}")
            return None

    async def delete_session_cache(self, session_id: str) -> bool:
        """
        Remove todos os dados de uma sessão do cache.

        Args:
            session_id: ID da sessão

        Returns:
            True se sucesso
        """
        if not await self.is_connected():
            return False

        try:
            # Buscar todas as chaves relacionadas à sessão
            patterns = [
                f"{self.SESSION_PREFIX}{session_id}",
                f"{self.CONVERSATION_PREFIX}{session_id}",
                f"{self.STAGE_PREFIX}{session_id}:*",
            ]

            keys_to_delete = []
            for pattern in patterns:
                if "*" in pattern:
                    # Buscar chaves com padrão
                    keys = await self.redis_client.keys(pattern)
                    keys_to_delete.extend(keys)
                else:
                    keys_to_delete.append(pattern)

            if keys_to_delete:
                deleted_count = await self.redis_client.delete(*keys_to_delete)
                logger.info(f"Removidas {deleted_count} chaves do cache para sessão {session_id}")
                return deleted_count > 0

            return True

        except Exception as e:
            logger.error(f"Erro ao remover cache da sessão {session_id}: {str(e)}")
            return False

    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do cache Redis.

        Returns:
            Dicionário com estatísticas
        """
        if not await self.is_connected():
            return {"status": "disconnected"}

        try:
            info = await self.redis_client.info()

            # Contar chaves por tipo
            session_keys = await self.redis_client.keys(f"{self.SESSION_PREFIX}*")
            conversation_keys = await self.redis_client.keys(f"{self.CONVERSATION_PREFIX}*")
            stage_keys = await self.redis_client.keys(f"{self.STAGE_PREFIX}*")

            return {
                "status": "connected",
                "total_sessions": len(session_keys),
                "total_conversations": len(conversation_keys),
                "total_stage_progress": len(stage_keys),
                "memory_used": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "uptime": info.get("uptime_in_seconds", 0),
            }

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas do cache: {str(e)}")
            return {"status": "error", "error": str(e)}


# Instância global do serviço Redis
_redis_service = None


async def get_redis_service() -> Optional[RedisService]:
    """Retorna instância global do serviço Redis."""
    global _redis_service

    settings = get_settings()

    if not settings.use_redis_cache:
        return None

    if _redis_service is None:
        _redis_service = RedisService(
            redis_url=settings.redis_url, password=settings.redis_password
        )
        await _redis_service.connect()

    return _redis_service
