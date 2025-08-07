"""
Base models and enums for the Intelligent Intake System.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class SystemRole(str, Enum):
    """Roles in the system"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    AGENT = "agent"


class MessageSender(str, Enum):
    USER = "user"
    AI = "ai"


class ValidationResult(BaseModel):
    is_complete: bool = False
    completeness_score: float = Field(ge=0.0, le=1.0)
    missing_items: List[str] = []
    suggestions: List[str] = []
    validated_data: Dict[str, Any] = {}


class ErrorResponse(BaseModel):
    error_code: str
    error_message: str
    error_details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None


class BaseEntity(BaseModel):
    """Base entity with common fields"""

    id: str = Field(..., description="Unique identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
