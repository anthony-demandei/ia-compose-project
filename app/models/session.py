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
