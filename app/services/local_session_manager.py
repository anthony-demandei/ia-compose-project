from typing import Dict, Optional
import json
import logging
import aiofiles
from datetime import datetime
from pathlib import Path
from app.models.session import DiscoverySession, SessionStatus, Message, MessageSender
from app.models.base import DiscoveryStage
from app.models.discovery import Requirements

logger = logging.getLogger(__name__)


class LocalSessionManager:
    """
    Gerencia o ciclo de vida das sessões de descoberta usando armazenamento local.
    Para desenvolvimento e testes sem necessidade de Firestore.
    """

    def __init__(self, storage_path: str = "storage/sessions", max_session_duration: int = 3600):
        self.storage_path = Path(storage_path)
        self.max_session_duration = max_session_duration  # segundos

        # Criar diretório se não existir
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Cache em memória para sessões ativas
        self._active_sessions: Dict[str, DiscoverySession] = {}

        # Carregar sessões existentes
        self._load_existing_sessions()

    def _load_existing_sessions(self):
        """Carrega sessões existentes do armazenamento local."""
        try:
            for session_file in self.storage_path.glob("*.json"):
                try:
                    with open(session_file, "r") as f:
                        data = json.load(f)
                        session = self._deserialize_session(data)
                        self._active_sessions[session.id] = session
                except Exception as e:
                    logger.error(f"Erro ao carregar sessão {session_file}: {str(e)}")
        except Exception as e:
            logger.error(f"Erro ao carregar sessões: {str(e)}")

    async def create_session(self, project_id: Optional[str] = None) -> DiscoverySession:
        """
        Cria uma nova sessão de descoberta.

        Args:
            project_id: ID do projeto (opcional)

        Returns:
            Nova sessão criada
        """
        session = DiscoverySession()

        try:
            # Adicionar ao cache
            self._active_sessions[session.id] = session

            # Salvar no armazenamento local
            await self._save_session(session)

            logger.info(f"Sessão criada: {session.id}")
            return session

        except Exception as e:
            logger.error(f"Erro ao criar sessão: {str(e)}")
            raise

    async def get_session(self, session_id: str) -> Optional[DiscoverySession]:
        """
        Recupera uma sessão existente.

        Args:
            session_id: ID da sessão

        Returns:
            Sessão encontrada ou None
        """
        # Verificar cache primeiro
        if session_id in self._active_sessions:
            return self._active_sessions[session_id]

        # Tentar carregar do armazenamento local
        try:
            session_file = self.storage_path / f"{session_id}.json"
            if session_file.exists():
                async with aiofiles.open(session_file, "r") as f:
                    data = json.loads(await f.read())
                    session = self._deserialize_session(data)

                    # Adicionar ao cache
                    self._active_sessions[session_id] = session
                    return session

        except Exception as e:
            logger.error(f"Erro ao recuperar sessão {session_id}: {str(e)}")

        return None

    async def update_session(self, session: DiscoverySession):
        """
        Atualiza uma sessão existente.

        Args:
            session: Sessão atualizada
        """
        try:
            # Atualizar timestamp
            session.updated_at = datetime.utcnow()

            # Atualizar cache
            self._active_sessions[session.id] = session

            # Salvar no armazenamento local
            await self._save_session(session)

            logger.info(f"Sessão atualizada: {session.id}")

        except Exception as e:
            logger.error(f"Erro ao atualizar sessão: {str(e)}")
            raise

    async def add_message(
        self, session_id: str, content: str, sender: MessageSender, metadata: Optional[Dict] = None
    ) -> Optional[Message]:
        """
        Adiciona uma mensagem a uma sessão.

        Args:
            session_id: ID da sessão
            content: Conteúdo da mensagem
            sender: Remetente (USER ou AI)
            metadata: Metadados adicionais

        Returns:
            Mensagem criada ou None
        """
        session = await self.get_session(session_id)
        if not session:
            logger.error(f"Sessão não encontrada: {session_id}")
            return None

        try:
            # Adicionar mensagem à sessão usando o método correto
            message = session.add_message(content, sender, metadata)

            # Salvar sessão atualizada
            await self.update_session(session)

            logger.info(f"Mensagem adicionada à sessão {session_id}: {message.id}")
            return message

        except Exception as e:
            logger.error(f"Erro ao adicionar mensagem: {str(e)}")
            return None

    async def get_session_status(self, session_id: str) -> Optional[SessionStatus]:
        """
        Obtém o status de uma sessão.

        Args:
            session_id: ID da sessão

        Returns:
            Status da sessão ou None
        """
        session = await self.get_session(session_id)
        if not session:
            return None

        return SessionStatus(
            session_id=session.id,
            current_stage=session.current_stage,
            is_completed=session.is_completed,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=len(session.messages),
            active_time=(datetime.utcnow() - session.created_at).total_seconds(),
        )

    async def expire_old_sessions(self):
        """
        Expira sessões antigas baseado em max_session_duration.
        """
        current_time = datetime.utcnow()
        expired_sessions = []

        for session_id, session in self._active_sessions.items():
            session_age = (current_time - session.created_at).total_seconds()

            if session_age > self.max_session_duration and not session.is_completed:
                expired_sessions.append(session_id)
                logger.info(f"Sessão expirada: {session_id} (idade: {session_age}s)")

        # Remover sessões expiradas do cache
        for session_id in expired_sessions:
            del self._active_sessions[session_id]

    async def _save_session(self, session: DiscoverySession):
        """Salva sessão no armazenamento local."""
        try:
            session_file = self.storage_path / f"{session.id}.json"
            session_data = self._serialize_session(session)

            async with aiofiles.open(session_file, "w") as f:
                await f.write(json.dumps(session_data, indent=2, default=str))

        except Exception as e:
            logger.error(f"Erro ao salvar sessão {session.id}: {str(e)}")
            raise

    def _serialize_session(self, session: DiscoverySession) -> Dict:
        """Serializa sessão para JSON."""
        return {
            "id": session.id,
            "current_stage": session.current_stage.value,
            "is_completed": session.is_completed,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "version": session.version,
            "requirements": session.requirements.dict(),
            "messages": [
                {
                    "id": msg.id,
                    "content": msg.content,
                    "sender": msg.sender.value,
                    "stage": msg.stage.value,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": msg.metadata,
                }
                for msg in session.messages
            ],
        }

    def _deserialize_session(self, data: Dict) -> DiscoverySession:
        """Deserializa sessão do JSON."""
        session = DiscoverySession()
        session.id = data["id"]
        session.current_stage = DiscoveryStage(data["current_stage"])
        session.is_completed = data.get("is_completed", False)
        session.created_at = datetime.fromisoformat(data["created_at"])
        session.updated_at = datetime.fromisoformat(data["updated_at"])
        session.version = data.get("version", 1)

        # Restaurar requisitos
        if "requirements" in data:
            session.requirements = Requirements(**data["requirements"])

        # Restaurar mensagens
        if "messages" in data:
            for msg_data in data["messages"]:
                message = Message(
                    session_id=session.id,  # Adicionar session_id
                    content=msg_data["content"],
                    sender=MessageSender(msg_data["sender"]),
                    stage=DiscoveryStage(msg_data["stage"]),
                    metadata=msg_data.get("metadata", {}),
                )
                message.id = msg_data["id"]
                message.timestamp = datetime.fromisoformat(msg_data["timestamp"])
                session.messages.append(message)

        return session

    async def clear_conversation(self, session_id: str) -> bool:
        """
        Limpa histórico de conversas de uma sessão (para 'Nova Tarefa').

        Args:
            session_id: ID da sessão

        Returns:
            True se sucesso, False caso contrário
        """
        session = await self.get_session(session_id)
        if not session:
            return False

        try:
            # Limpar mensagens
            session.messages = []

            # Resetar para o primeiro estágio
            session.current_stage = DiscoveryStage.BUSINESS_CONTEXT
            session.is_completed = False

            # Incrementar versão para indicar nova tarefa
            session.version += 1

            # Salvar sessão atualizada
            await self.update_session(session)

            logger.info(f"Conversação limpa para sessão {session_id}")
            return True

        except Exception as e:
            logger.error(f"Erro ao limpar conversação: {str(e)}")
            return False
