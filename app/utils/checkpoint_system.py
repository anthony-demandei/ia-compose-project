"""
Sistema de checkpoints avançados para salvar e restaurar estado da descoberta.
Permite recuperação de falhas e rollback para pontos específicos.
"""

import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

from app.models.base import DiscoveryStage, ValidationResult
from app.models.session import DiscoverySession
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


class CheckpointType(str, Enum):
    """Tipos de checkpoint."""

    STAGE_COMPLETE = "stage_complete"
    VALIDATION_PASSED = "validation_passed"
    USER_CONFIRMATION = "user_confirmation"
    AUTO_SAVE = "auto_save"
    MANUAL_SAVE = "manual_save"
    ERROR_RECOVERY = "error_recovery"


@dataclass
class Checkpoint:
    """Representa um ponto de checkpoint na descoberta."""

    id: str
    session_id: str
    timestamp: datetime
    checkpoint_type: CheckpointType
    stage: DiscoveryStage

    # Estado da sessão no checkpoint
    session_state: Dict[str, Any]
    requirements_data: Dict[str, Any]
    conversation_messages: List[Dict[str, Any]]

    # Metadados do checkpoint
    validation_score: float
    completion_percentage: float
    user_message_count: int
    ai_message_count: int

    # Dados de contexto
    stage_transition: Optional[Tuple[str, str]] = None  # (from, to)
    user_action: Optional[str] = None
    error_context: Optional[str] = None

    # Hash para verificar integridade
    data_hash: str = ""

    def __post_init__(self):
        """Calcula hash dos dados após inicialização."""
        if not self.data_hash:
            self.data_hash = self._calculate_hash()

    def _calculate_hash(self) -> str:
        """Calcula hash dos dados críticos do checkpoint."""
        critical_data = {
            "session_id": self.session_id,
            "stage": self.stage.value,
            "requirements_data": self.requirements_data,
            "validation_score": self.validation_score,
        }

        data_str = json.dumps(critical_data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(data_str.encode()).hexdigest()

    def verify_integrity(self) -> bool:
        """Verifica integridade do checkpoint."""
        return self.data_hash == self._calculate_hash()


class CheckpointManager:
    """
    Gerenciador de checkpoints para sistema de descoberta.
    """

    def __init__(self, storage_path: str = "/tmp/discovery_checkpoints"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True, parents=True)

        # Configurações
        self.auto_save_interval = timedelta(minutes=5)
        self.max_checkpoints_per_session = 50
        self.checkpoint_retention_days = 30

        # Cache em memória
        self._checkpoint_cache: Dict[str, List[Checkpoint]] = {}

        # Estatísticas
        self.stats = {
            "checkpoints_created": 0,
            "checkpoints_restored": 0,
            "auto_saves": 0,
            "error_recoveries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

    def create_checkpoint(
        self,
        session: DiscoverySession,
        checkpoint_type: CheckpointType,
        validation_result: Optional[ValidationResult] = None,
        user_action: Optional[str] = None,
        error_context: Optional[str] = None,
    ) -> Checkpoint:
        """
        Cria um novo checkpoint do estado atual.
        """
        try:
            # Gerar ID único para o checkpoint
            checkpoint_id = self._generate_checkpoint_id(session.id, checkpoint_type)

            # Capturar estado atual
            session_state = self._capture_session_state(session)
            requirements_data = self._serialize_requirements(session.requirements)
            conversation_messages = self._serialize_messages(session.messages)

            # Calcular métricas
            completion_percentage = self._calculate_completion_percentage(session)
            validation_score = validation_result.completeness_score if validation_result else 0.0

            user_msg_count = len([m for m in session.messages if m.sender == "user"])
            ai_msg_count = len([m for m in session.messages if m.sender == "ai"])

            # Detectar transição de estágio
            stage_transition = self._detect_stage_transition(session.id, session.current_stage)

            # Criar checkpoint
            checkpoint = Checkpoint(
                id=checkpoint_id,
                session_id=session.id,
                timestamp=datetime.utcnow(),
                checkpoint_type=checkpoint_type,
                stage=session.current_stage,
                session_state=session_state,
                requirements_data=requirements_data,
                conversation_messages=conversation_messages,
                validation_score=validation_score,
                completion_percentage=completion_percentage,
                user_message_count=user_msg_count,
                ai_message_count=ai_msg_count,
                stage_transition=stage_transition,
                user_action=user_action,
                error_context=error_context,
            )

            # Salvar checkpoint
            self._save_checkpoint(checkpoint)

            # Atualizar cache
            if session.id not in self._checkpoint_cache:
                self._checkpoint_cache[session.id] = []
            self._checkpoint_cache[session.id].append(checkpoint)

            # Limpar checkpoints antigos se necessário
            self._cleanup_old_checkpoints(session.id)

            # Atualizar estatísticas
            self.stats["checkpoints_created"] += 1
            if checkpoint_type == CheckpointType.AUTO_SAVE:
                self.stats["auto_saves"] += 1
            elif checkpoint_type == CheckpointType.ERROR_RECOVERY:
                self.stats["error_recoveries"] += 1

            logger.info(f"Checkpoint criado: {checkpoint_id} ({checkpoint_type.value})")

            return checkpoint

        except Exception as e:
            logger.error("Erro ao criar checkpoint: {}", str(e))
            raise

    def restore_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        Restaura estado de um checkpoint específico.
        """
        try:
            checkpoint = self._load_checkpoint(checkpoint_id)
            if not checkpoint:
                logger.error(f"Checkpoint não encontrado: {checkpoint_id}")
                return None

            # Verificar integridade
            if not checkpoint.verify_integrity():
                logger.error(f"Checkpoint corrompido: {checkpoint_id}")
                return None

            # Preparar dados de restauração
            restore_data = {
                "session_state": checkpoint.session_state,
                "requirements_data": checkpoint.requirements_data,
                "conversation_messages": checkpoint.conversation_messages,
                "stage": checkpoint.stage,
                "checkpoint_info": {
                    "id": checkpoint.id,
                    "timestamp": checkpoint.timestamp,
                    "type": checkpoint.checkpoint_type,
                    "validation_score": checkpoint.validation_score,
                    "completion_percentage": checkpoint.completion_percentage,
                },
            }

            self.stats["checkpoints_restored"] += 1

            logger.info(f"Checkpoint restaurado: {checkpoint_id}")

            return restore_data

        except Exception as e:
            logger.error("Erro ao restaurar checkpoint {}: {}", checkpoint_id, str(e))
            return None

    def list_checkpoints(
        self, session_id: str, checkpoint_type: Optional[CheckpointType] = None
    ) -> List[Dict[str, Any]]:
        """
        Lista checkpoints disponíveis para uma sessão.
        """
        try:
            checkpoints = self._get_session_checkpoints(session_id)

            # Filtrar por tipo se especificado
            if checkpoint_type:
                checkpoints = [cp for cp in checkpoints if cp.checkpoint_type == checkpoint_type]

            # Retornar resumo dos checkpoints
            checkpoint_list = []
            for cp in sorted(checkpoints, key=lambda x: x.timestamp, reverse=True):
                checkpoint_list.append(
                    {
                        "id": cp.id,
                        "timestamp": cp.timestamp.isoformat(),
                        "type": cp.checkpoint_type.value,
                        "stage": cp.stage.value,
                        "validation_score": cp.validation_score,
                        "completion_percentage": cp.completion_percentage,
                        "message_count": cp.user_message_count + cp.ai_message_count,
                        "stage_transition": cp.stage_transition,
                        "user_action": cp.user_action,
                    }
                )

            return checkpoint_list

        except Exception as e:
            logger.error("Erro ao listar checkpoints para sessão {}: {}", session_id, str(e))
            return []

    def should_auto_save(self, session: DiscoverySession) -> bool:
        """
        Verifica se deve criar um auto-save baseado em critérios.
        """
        try:
            checkpoints = self._get_session_checkpoints(session.id)

            if not checkpoints:
                return True  # Primeiro checkpoint

            # Último checkpoint
            last_checkpoint = max(checkpoints, key=lambda x: x.timestamp)

            # Critérios para auto-save
            time_since_last = datetime.utcnow() - last_checkpoint.timestamp

            # Auto-save se:
            # 1. Passou do intervalo configurado
            if time_since_last >= self.auto_save_interval:
                return True

            # 2. Houve mudança significativa no progresso
            current_completion = self._calculate_completion_percentage(session)
            if current_completion - last_checkpoint.completion_percentage >= 0.1:  # 10%
                return True

            # 3. Houve transição de estágio
            if session.current_stage != last_checkpoint.stage:
                return True

            # 4. Muitas mensagens novas
            current_msg_count = len(session.messages)
            last_msg_count = last_checkpoint.user_message_count + last_checkpoint.ai_message_count
            if current_msg_count - last_msg_count >= 5:
                return True

            return False

        except Exception as e:
            logger.error("Erro ao verificar auto-save para sessão {}: {}", session.id, str(e))
            return False

    def find_recovery_checkpoint(
        self, session_id: str, target_stage: Optional[DiscoveryStage] = None
    ) -> Optional[Checkpoint]:
        """
        Encontra o melhor checkpoint para recuperação de erro.
        """
        try:
            checkpoints = self._get_session_checkpoints(session_id)

            if not checkpoints:
                return None

            # Se estágio específico, encontrar último checkpoint desse estágio
            if target_stage:
                stage_checkpoints = [cp for cp in checkpoints if cp.stage == target_stage]
                if stage_checkpoints:
                    return max(stage_checkpoints, key=lambda x: x.timestamp)

            # Senão, encontrar último checkpoint válido
            valid_checkpoints = [
                cp
                for cp in checkpoints
                if cp.checkpoint_type
                in [CheckpointType.STAGE_COMPLETE, CheckpointType.VALIDATION_PASSED]
                and cp.verify_integrity()
            ]

            if valid_checkpoints:
                return max(valid_checkpoints, key=lambda x: x.timestamp)

            # Último recurso: qualquer checkpoint válido
            valid_any = [cp for cp in checkpoints if cp.verify_integrity()]
            if valid_any:
                return max(valid_any, key=lambda x: x.timestamp)

            return None

        except Exception as e:
            logger.error("Erro ao encontrar checkpoint de recuperação: {}", str(e))
            return None

    def _generate_checkpoint_id(self, session_id: str, checkpoint_type: CheckpointType) -> str:
        """Gera ID único para checkpoint."""
        timestamp = datetime.utcnow().isoformat()
        data = f"{session_id}_{checkpoint_type.value}_{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _capture_session_state(self, session: DiscoverySession) -> Dict[str, Any]:
        """Captura estado atual da sessão."""
        return {
            "id": session.id,
            "current_stage": session.current_stage.value,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "total_messages": len(session.messages),
        }

    def _serialize_requirements(self, requirements) -> Dict[str, Any]:
        """Serializa objeto de requirements para JSON."""
        return requirements.dict()

    def _serialize_messages(self, messages) -> List[Dict[str, Any]]:
        """Serializa mensagens para JSON."""
        return [
            {
                "sender": msg.sender,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "metadata": msg.metadata,
            }
            for msg in messages
        ]

    def _calculate_completion_percentage(self, session: DiscoverySession) -> float:
        """Calcula percentual de conclusão geral."""
        from app.core.validation_engine import ValidationEngine

        validation_engine = ValidationEngine()
        stage_scores = []

        for stage in DiscoveryStage:
            if stage == DiscoveryStage.FINALIZE_DOCS:
                continue

            validation = validation_engine.validate_stage(stage, session.requirements)
            stage_scores.append(validation.completeness_score)

        return sum(stage_scores) / len(stage_scores) if stage_scores else 0.0

    def _detect_stage_transition(
        self, session_id: str, current_stage: DiscoveryStage
    ) -> Optional[Tuple[str, str]]:
        """Detecta transição de estágio comparando com checkpoint anterior."""
        checkpoints = self._get_session_checkpoints(session_id)

        if not checkpoints:
            return None

        last_checkpoint = max(checkpoints, key=lambda x: x.timestamp)
        if last_checkpoint.stage != current_stage:
            return (last_checkpoint.stage.value, current_stage.value)

        return None

    def _save_checkpoint(self, checkpoint: Checkpoint):
        """Salva checkpoint no disco."""
        file_path = self.storage_path / f"{checkpoint.session_id}" / f"{checkpoint.id}.json"
        file_path.parent.mkdir(exist_ok=True, parents=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(asdict(checkpoint), f, indent=2, ensure_ascii=False, default=str)

    def _load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Carrega checkpoint do disco."""
        # Procurar arquivo em todas as sessões
        for session_dir in self.storage_path.iterdir():
            if session_dir.is_dir():
                checkpoint_file = session_dir / f"{checkpoint_id}.json"
                if checkpoint_file.exists():
                    try:
                        with open(checkpoint_file, "r", encoding="utf-8") as f:
                            data = json.load(f)

                        # Converter strings de data para datetime
                        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                        data["checkpoint_type"] = CheckpointType(data["checkpoint_type"])
                        data["stage"] = DiscoveryStage(data["stage"])

                        return Checkpoint(**data)

                    except Exception as e:
                        logger.error("Erro ao carregar checkpoint {}: {}", checkpoint_id, str(e))

        return None

    def _get_session_checkpoints(self, session_id: str) -> List[Checkpoint]:
        """Obtém todos os checkpoints de uma sessão (com cache)."""
        # Verificar cache primeiro
        if session_id in self._checkpoint_cache:
            self.stats["cache_hits"] += 1
            return self._checkpoint_cache[session_id]

        self.stats["cache_misses"] += 1

        # Carregar do disco
        checkpoints = []
        session_dir = self.storage_path / session_id

        if session_dir.exists() and session_dir.is_dir():
            for checkpoint_file in session_dir.glob("*.json"):
                try:
                    with open(checkpoint_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # Converter para objetos
                    data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                    data["checkpoint_type"] = CheckpointType(data["checkpoint_type"])
                    data["stage"] = DiscoveryStage(data["stage"])

                    checkpoint = Checkpoint(**data)
                    checkpoints.append(checkpoint)

                except Exception as e:
                    logger.error("Erro ao carregar checkpoint {}: {}", checkpoint_file.name, str(e))

        # Atualizar cache
        self._checkpoint_cache[session_id] = checkpoints

        return checkpoints

    def _cleanup_old_checkpoints(self, session_id: str):
        """Remove checkpoints antigos para evitar acúmulo."""
        checkpoints = self._get_session_checkpoints(session_id)

        # Remover checkpoints muito antigos
        cutoff_date = datetime.utcnow() - timedelta(days=self.checkpoint_retention_days)
        expired_checkpoints = [cp for cp in checkpoints if cp.timestamp < cutoff_date]

        for cp in expired_checkpoints:
            self._delete_checkpoint(cp.id)

        # Manter apenas N checkpoints mais recentes
        remaining_checkpoints = [cp for cp in checkpoints if cp not in expired_checkpoints]
        if len(remaining_checkpoints) > self.max_checkpoints_per_session:
            # Ordenar por timestamp e manter os mais recentes
            sorted_checkpoints = sorted(
                remaining_checkpoints, key=lambda x: x.timestamp, reverse=True
            )
            excess_checkpoints = sorted_checkpoints[self.max_checkpoints_per_session :]

            for cp in excess_checkpoints:
                self._delete_checkpoint(cp.id)

    def _delete_checkpoint(self, checkpoint_id: str):
        """Remove checkpoint do disco e cache."""
        for session_dir in self.storage_path.iterdir():
            if session_dir.is_dir():
                checkpoint_file = session_dir / f"{checkpoint_id}.json"
                if checkpoint_file.exists():
                    checkpoint_file.unlink()

                    # Remover do cache também
                    session_id = session_dir.name
                    if session_id in self._checkpoint_cache:
                        self._checkpoint_cache[session_id] = [
                            cp
                            for cp in self._checkpoint_cache[session_id]
                            if cp.id != checkpoint_id
                        ]
                    break

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do sistema de checkpoints."""
        total_checkpoints = sum(len(checkpoints) for checkpoints in self._checkpoint_cache.values())

        return {
            **self.stats,
            "total_checkpoints": total_checkpoints,
            "cached_sessions": len(self._checkpoint_cache),
            "cache_hit_rate": (
                self.stats["cache_hits"]
                / max(1, self.stats["cache_hits"] + self.stats["cache_misses"])
            ),
        }


# Funções de conveniência
def create_stage_checkpoint(
    session: DiscoverySession,
    validation_result: ValidationResult,
    checkpoint_manager: CheckpointManager,
) -> Checkpoint:
    """Cria checkpoint ao completar um estágio."""
    return checkpoint_manager.create_checkpoint(
        session=session,
        checkpoint_type=CheckpointType.STAGE_COMPLETE,
        validation_result=validation_result,
        user_action="stage_completed",
    )


def create_error_recovery_checkpoint(
    session: DiscoverySession, error_context: str, checkpoint_manager: CheckpointManager
) -> Checkpoint:
    """Cria checkpoint para recuperação de erro."""
    return checkpoint_manager.create_checkpoint(
        session=session, checkpoint_type=CheckpointType.ERROR_RECOVERY, error_context=error_context
    )


# Exemplo de uso
if __name__ == "__main__":
    checkpoint_manager = CheckpointManager()
    print("Sistema de checkpoints inicializado")
    print("Stats:", checkpoint_manager.get_stats())
