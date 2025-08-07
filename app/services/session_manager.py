from typing import Dict, Optional, List
import logging
from datetime import datetime, timedelta
from google.cloud import firestore
from app.models.session import DiscoverySession, SessionStatus, Message, MessageSender
from app.models.base import DiscoveryStage
from app.models.discovery import Requirements

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Gerencia o ciclo de vida das sessões de descoberta,
    incluindo persistência no Firestore e cache em memória.
    """

    def __init__(self, project_id: str, max_session_duration: int = 3600):
        self.project_id = project_id
        self.max_session_duration = max_session_duration  # segundos
        self.db = firestore.Client(project=project_id)

        # Cache em memória para sessões ativas
        self._active_sessions: Dict[str, DiscoverySession] = {}

        # Coleções Firestore
        self.sessions_collection = "discovery_sessions"
        self.messages_collection = "discovery_messages"

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
            # Salvar no Firestore
            session_data = {
                "id": session.id,
                "current_stage": session.current_stage.value,
                "requirements": session.requirements.dict(),
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "version": session.version,
                "is_completed": session.is_completed,
                "document_uris": session.document_uris,
                "project_id": project_id,
            }

            self.db.collection(self.sessions_collection).document(session.id).set(session_data)

            # Adicionar ao cache
            self._active_sessions[session.id] = session

            logger.info(f"Sessão criada: {session.id}")
            return session

        except Exception as e:
            logger.error(f"Erro ao criar sessão: {str(e)}")
            raise

    async def get_session(self, session_id: str) -> Optional[DiscoverySession]:
        """
        Recupera uma sessão pelo ID.

        Args:
            session_id: ID da sessão

        Returns:
            Sessão encontrada ou None
        """
        # Verificar cache primeiro
        if session_id in self._active_sessions:
            session = self._active_sessions[session_id]

            # Verificar se não expirou
            if not self._is_session_expired(session):
                return session
            else:
                # Remover do cache se expirou
                del self._active_sessions[session_id]

        # Buscar no Firestore
        try:
            doc = self.db.collection(self.sessions_collection).document(session_id).get()

            if not doc.exists:
                logger.warning(f"Sessão não encontrada: {session_id}")
                return None

            session_data = doc.to_dict()

            # Reconstruir objeto da sessão
            session = self._reconstruct_session(session_data)

            # Verificar se não expirou
            if self._is_session_expired(session):
                logger.warning(f"Sessão expirada: {session_id}")
                return None

            # Carregar mensagens
            await self._load_session_messages(session)

            # Adicionar ao cache
            self._active_sessions[session_id] = session

            return session

        except Exception as e:
            logger.error(f"Erro ao recuperar sessão {session_id}: {str(e)}")
            return None

    async def update_session(self, session: DiscoverySession) -> bool:
        """
        Atualiza uma sessão existente.

        Args:
            session: Sessão a ser atualizada

        Returns:
            True se atualizada com sucesso
        """
        try:
            session.updated_at = datetime.utcnow()

            # Atualizar no Firestore
            session_data = {
                "current_stage": session.current_stage.value,
                "requirements": session.requirements.dict(),
                "updated_at": session.updated_at,
                "version": session.version,
                "is_completed": session.is_completed,
                "document_uris": session.document_uris,
            }

            self.db.collection(self.sessions_collection).document(session.id).update(session_data)

            # Atualizar cache
            self._active_sessions[session.id] = session

            logger.debug(f"Sessão atualizada: {session.id}")
            return True

        except Exception as e:
            logger.error(f"Erro ao atualizar sessão {session.id}: {str(e)}")
            return False

    async def add_message(
        self, session_id: str, content: str, sender: MessageSender, metadata: Optional[Dict] = None
    ) -> Optional[Message]:
        """
        Adiciona uma mensagem à sessão.

        Args:
            session_id: ID da sessão
            content: Conteúdo da mensagem
            sender: Remetente da mensagem
            metadata: Metadados opcionais

        Returns:
            Mensagem criada ou None se erro
        """
        session = await self.get_session(session_id)
        if not session:
            logger.error(f"Sessão não encontrada para adicionar mensagem: {session_id}")
            return None

        try:
            # Criar mensagem
            message = session.add_message(content, sender, metadata)

            # Salvar mensagem no Firestore
            message_data = {
                "id": message.id,
                "session_id": message.session_id,
                "content": message.content,
                "sender": message.sender.value,
                "timestamp": message.timestamp,
                "stage": message.stage.value,
                "metadata": message.metadata or {},
            }

            self.db.collection(self.messages_collection).document(message.id).set(message_data)

            # Atualizar sessão
            await self.update_session(session)

            logger.debug(f"Mensagem adicionada à sessão {session_id}: {message.id}")
            return message

        except Exception as e:
            logger.error(f"Erro ao adicionar mensagem à sessão {session_id}: {str(e)}")
            return None

    async def get_session_status(self, session_id: str) -> Optional[SessionStatus]:
        """
        Retorna o status atual de uma sessão.

        Args:
            session_id: ID da sessão

        Returns:
            Status da sessão ou None
        """
        session = await self.get_session(session_id)
        if not session:
            return None

        # Calcular progresso por estágio (implementação simplificada)
        stage_progress = {}
        all_stages = list(DiscoveryStage)
        current_index = all_stages.index(session.current_stage)

        for i, stage in enumerate(all_stages):
            if i < current_index:
                stage_progress[stage] = 1.0
            elif i == current_index:
                stage_progress[stage] = 0.5  # Estágio atual
            else:
                stage_progress[stage] = 0.0

        overall_progress = sum(stage_progress.values()) / len(all_stages)

        return SessionStatus(
            session_id=session.id,
            current_stage=session.current_stage,
            stage_progress=stage_progress,
            overall_progress=overall_progress,
            is_completed=session.is_completed,
            total_messages=len(session.messages),
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    async def list_active_sessions(self, limit: int = 50) -> List[DiscoverySession]:
        """
        Lista sessões ativas recentes.

        Args:
            limit: Número máximo de sessões

        Returns:
            Lista de sessões ativas
        """
        try:
            # Buscar sessões recentes no Firestore
            cutoff_time = datetime.utcnow() - timedelta(seconds=self.max_session_duration)

            docs = (
                self.db.collection(self.sessions_collection)
                .where("updated_at", ">=", cutoff_time)
                .order_by("updated_at", direction=firestore.Query.DESCENDING)
                .limit(limit)
                .stream()
            )

            sessions = []
            for doc in docs:
                session_data = doc.to_dict()
                session = self._reconstruct_session(session_data)
                sessions.append(session)

            return sessions

        except Exception as e:
            logger.error(f"Erro ao listar sessões ativas: {str(e)}")
            return []

    async def cleanup_expired_sessions(self) -> int:
        """
        Remove sessões expiradas do cache e marca como inativas no Firestore.

        Returns:
            Número de sessões limpas
        """
        cleaned_count = 0

        try:
            # Limpar cache
            expired_session_ids = []
            for session_id, session in self._active_sessions.items():
                if self._is_session_expired(session):
                    expired_session_ids.append(session_id)

            for session_id in expired_session_ids:
                del self._active_sessions[session_id]
                cleaned_count += 1

            logger.info(f"Limpas {cleaned_count} sessões expiradas do cache")
            return cleaned_count

        except Exception as e:
            logger.error(f"Erro na limpeza de sessões: {str(e)}")
            return 0

    def _is_session_expired(self, session: DiscoverySession) -> bool:
        """Verifica se uma sessão expirou."""
        expiry_time = session.updated_at + timedelta(seconds=self.max_session_duration)
        return datetime.utcnow() > expiry_time

    def _reconstruct_session(self, session_data: Dict) -> DiscoverySession:
        """Reconstrói objeto de sessão a partir dos dados do Firestore."""
        requirements_data = session_data.get("requirements", {})
        requirements = Requirements(**requirements_data)

        return DiscoverySession(
            id=session_data["id"],
            current_stage=DiscoveryStage(session_data["current_stage"]),
            requirements=requirements,
            messages=[],  # Serão carregadas separadamente
            created_at=session_data["created_at"],
            updated_at=session_data["updated_at"],
            version=session_data.get("version", 1),
            is_completed=session_data.get("is_completed", False),
            document_uris=session_data.get("document_uris", {}),
        )

    async def _load_session_messages(self, session: DiscoverySession):
        """Carrega mensagens da sessão do Firestore."""
        try:
            docs = (
                self.db.collection(self.messages_collection)
                .where("session_id", "==", session.id)
                .order_by("timestamp")
                .stream()
            )

            messages = []
            for doc in docs:
                msg_data = doc.to_dict()
                message = Message(
                    id=msg_data["id"],
                    session_id=msg_data["session_id"],
                    content=msg_data["content"],
                    sender=MessageSender(msg_data["sender"]),
                    timestamp=msg_data["timestamp"],
                    stage=DiscoveryStage(msg_data["stage"]),
                    metadata=msg_data.get("metadata"),
                )
                messages.append(message)

            session.messages = messages

        except Exception as e:
            logger.error(f"Erro ao carregar mensagens da sessão {session.id}: {str(e)}")
            session.messages = []
