from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid
from enum import Enum


class MessageSender(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    content: str
    sender: MessageSender
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict] = None


class SimpleSession(BaseModel):
    """Simple session model for intake system"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    messages: List[Message] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1
    is_completed: bool = False
    metadata: Dict[str, Any] = {}

    def add_message(self, content: str, sender: MessageSender, metadata: Optional[Dict] = None):
        message = Message(session_id=self.id, content=content, sender=sender, metadata=metadata)
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
        return message

    def get_conversation_history(self, limit: Optional[int] = None) -> List[Message]:
        messages = self.messages
        if limit:
            messages = messages[-limit:]
        return messages


class SessionStatus(BaseModel):
    session_id: str
    overall_progress: float
    is_completed: bool
    total_messages: int
    created_at: datetime
    updated_at: datetime


class MessageRequest(BaseModel):
    session_id: str
    content: str
    metadata: Optional[Dict] = None


class MessageResponse(BaseModel):
    message_id: str
    content: str
    timestamp: datetime
    metadata: Optional[Dict] = None


# Discovery-specific models
class StageData(BaseModel):
    """Base class for stage data"""
    # Business context fields
    objetivo: Optional[str] = None
    personas: Optional[List[str]] = []
    kpis: Optional[List[str]] = []
    riscos_principais: Optional[List[str]] = []
    
    # Users and journeys fields
    perfis: Optional[List[str]] = []
    jornadas_criticas: Optional[List[str]] = []
    idiomas: Optional[List[str]] = []
    acessibilidade: Optional[str] = None
    
    # Functional scope fields
    features_must: Optional[List[str]] = []
    features_should: Optional[List[str]] = []
    integracoes: Optional[List[str]] = []
    webhooks: Optional[List[str]] = []
    
    # Constraints and policies fields
    lgpd_pii: Optional[bool] = None
    seguranca: Optional[str] = None
    auditoria: Optional[str] = None
    compliance: Optional[str] = None
    
    # Non-functional fields
    slos: Optional[Dict] = {}
    disponibilidade: Optional[str] = None
    custo_alvo: Optional[float] = None
    escalabilidade: Optional[str] = None
    
    # Tech preferences fields
    stacks_permitidas: Optional[List[str]] = []
    stacks_vedadas: Optional[List[str]] = []
    legado: Optional[str] = None
    infraestrutura_preferida: Optional[str] = None
    
    # Delivery budget fields
    marcos: Optional[List[str]] = []
    prazos: Optional[Dict] = {}
    budget: Optional[float] = None
    prazo_semanas: Optional[int] = None
    governanca: Optional[str] = None
    
    # Review gaps fields
    lacunas_identificadas: Optional[List[str]] = []
    trade_offs: Optional[List[str]] = []
    decisoes_pendentes: Optional[List[str]] = []
    riscos_aceitos: Optional[List[str]] = []
    
    def dict(self):
        return super().dict(exclude_none=True)


class DiscoveryRequirements(BaseModel):
    """Container for all discovery requirements across stages"""
    business_context: StageData = Field(default_factory=StageData)
    users_and_journeys: StageData = Field(default_factory=StageData)
    functional_scope: StageData = Field(default_factory=StageData)
    constraints_policies: StageData = Field(default_factory=StageData)
    non_functional: StageData = Field(default_factory=StageData)
    tech_preferences: StageData = Field(default_factory=StageData)
    delivery_budget: StageData = Field(default_factory=StageData)
    review_gaps: StageData = Field(default_factory=StageData)
    
    def get_stage_data(self, stage) -> Optional[StageData]:
        """Get data for a specific stage"""
        stage_name = stage.value if hasattr(stage, 'value') else stage
        return getattr(self, stage_name, StageData())
    
    def update_stage_data(self, stage: str, data: Dict):
        """Update data for a specific stage"""
        stage_name = stage.value if hasattr(stage, 'value') else stage
        current_data = getattr(self, stage_name, {})
        current_data.update(data)
        setattr(self, stage_name, current_data)


class DiscoverySession(BaseModel):
    """Session model for discovery process"""
    
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_description: str
    current_stage: str = "business_context"  # Using string to avoid circular import
    messages: List[Message] = []
    requirements: DiscoveryRequirements = Field(default_factory=DiscoveryRequirements)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_completed: bool = False
    generated_documents: Dict[str, str] = {}
    
    def add_message(self, content: str, sender: str, metadata: Optional[Dict] = None):
        message = Message(
            session_id=self.session_id,
            content=content,
            sender=MessageSender(sender),
            metadata=metadata
        )
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
        return message
    
    def get_conversation_history(self, limit: Optional[int] = None) -> List[Message]:
        messages = self.messages
        if limit:
            messages = messages[-limit:]
        return messages
