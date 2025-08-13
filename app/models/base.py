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


class DiscoveryStage(str, Enum):
    """Stages in the discovery process"""
    
    BUSINESS_CONTEXT = "business_context"
    USERS_AND_JOURNEYS = "users_and_journeys"
    FUNCTIONAL_SCOPE = "functional_scope"
    CONSTRAINTS_POLICIES = "constraints_policies"
    NON_FUNCTIONAL = "non_functional"
    TECH_PREFERENCES = "tech_preferences"
    DELIVERY_BUDGET = "delivery_budget"
    REVIEW_GAPS = "review_gaps"
    FINALIZE_DOCS = "finalize_docs"


class MessageSender(str, Enum):
    USER = "user"
    AI = "ai"


class ValidationResult(BaseModel):
    is_complete: bool = False
    completeness_score: float = Field(ge=0.0, le=1.0)
    missing_items: List[str] = []
    suggestions: List[str] = []
    validated_data: Dict[str, Any] = {}


class StageChecklist(BaseModel):
    """Checklist for stage validation"""
    stage: str
    required_items: List[str] = []
    optional_items: List[str] = []
    min_completeness: float = 0.8


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
