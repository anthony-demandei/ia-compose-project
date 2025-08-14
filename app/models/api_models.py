"""
API Models for the new 4-API workflow.
Defines request and response models for the simplified REST API structure.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class ProjectAnalysisRequest(BaseModel):
    """Request model for initial project analysis (API 1)."""
    
    project_description: str = Field(
        ..., 
        min_length=50, 
        max_length=8000,
        description="Detailed description of the project requirements",
        example="Sistema de gestão para clínica médica com 5 médicos e 300 pacientes/mês. Funcionalidades: agendamento online, prontuários eletrônicos, prescrições digitais, faturamento. Orçamento: R$ 120.000, Prazo: 6 meses"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional metadata about the request",
        example={"source": "demandei_platform", "user_id": "user123", "organization": "clinic_abc"}
    )

    class Config:
        json_schema_extra = {
            "example": {
                "project_description": "Plataforma de e-commerce B2C para venda de produtos de beleza. Funcionalidades: catálogo com filtros avançados, carrinho de compras, múltiplos gateways de pagamento (PIX, cartão, boleto), sistema de avaliações, programa de fidelidade. Orçamento: R$ 200.000, Prazo: 8 meses",
                "metadata": {
                    "source": "demandei_platform",
                    "user_id": "user456",
                    "project_priority": "high"
                }
            }
        }


class QuestionChoice(BaseModel):
    """Individual choice option for a multiple choice question."""
    
    id: str = Field(..., description="Unique identifier for this choice")
    text: str = Field(..., description="Display text for this choice")
    description: Optional[str] = Field(None, description="Additional description if needed")


class Question(BaseModel):
    """Question model for the API workflow."""
    
    code: str = Field(..., description="Unique question code (e.g., Q001)")
    text: str = Field(..., description="Question text to display")
    why_it_matters: str = Field(..., description="Explanation of why this question is critical for project success")
    choices: List[QuestionChoice] = Field(..., description="Available answer choices")
    required: bool = Field(True, description="Whether this question is required")
    allow_multiple: bool = Field(False, description="Whether multiple choices are allowed")
    category: str = Field(..., description="Question category (business, technical, etc.)")


class ProjectAnalysisResponse(BaseModel):
    """Response model for project analysis (API 1)."""
    
    session_id: str = Field(..., description="Unique session identifier")
    questions: List[Question] = Field(..., description="Generated questions sequence")
    total_questions: int = Field(..., description="Total number of questions")
    estimated_completion_time: int = Field(..., description="Estimated completion time in minutes")
    project_classification: Dict[str, Any] = Field(..., description="AI classification of the project")


class QuestionAnswer(BaseModel):
    """Answer to a specific question."""
    
    question_code: str = Field(..., description="Question code being answered")
    selected_choices: List[str] = Field(..., description="List of selected choice IDs")
    custom_text: Optional[str] = Field(None, description="Custom text if question allows it")


class QuestionResponseRequest(BaseModel):
    """Request model for question responses (API 2)."""
    
    session_id: str = Field(..., description="Session identifier from project analysis", example="sess_abc123def456")
    answers: List[QuestionAnswer] = Field(..., description="Answers to the questions")
    request_next_batch: bool = Field(True, description="Whether to request next batch of questions")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123def456",
                "answers": [
                    {
                        "question_code": "Q001",
                        "selected_choices": ["web_app"],
                        "custom_text": None
                    },
                    {
                        "question_code": "Q002", 
                        "selected_choices": ["small"],
                        "custom_text": None
                    },
                    {
                        "question_code": "Q003",
                        "selected_choices": ["react", "python"],
                        "custom_text": None
                    }
                ],
                "request_next_batch": True
            }
        }


class QuestionResponseType(str, Enum):
    """Types of responses from question submission."""
    
    MORE_QUESTIONS = "more_questions"
    READY_FOR_SUMMARY = "ready_for_summary"
    NEEDS_CLARIFICATION = "needs_clarification"


class QuestionResponseResponse(BaseModel):
    """Response model for question responses (API 2)."""
    
    session_id: str = Field(..., description="Session identifier")
    response_type: QuestionResponseType = Field(..., description="Type of response")
    next_questions: Optional[List[Question]] = Field(None, description="Next batch of questions if available")
    completion_percentage: float = Field(..., description="Completion percentage (0-100)")
    message: str = Field(..., description="Status message for the user")


class SummaryRequest(BaseModel):
    """Request model for summary generation (API 3)."""
    
    session_id: str = Field(..., description="Session identifier")
    include_assumptions: bool = Field(True, description="Whether to include AI assumptions")


class SummaryResponse(BaseModel):
    """Response model for summary generation (API 3)."""
    
    session_id: str = Field(..., description="Session identifier")
    summary: str = Field(..., description="Generated summary in markdown format")
    key_points: List[str] = Field(..., description="Key points extracted from the analysis")
    assumptions: List[str] = Field(..., description="AI-made assumptions about the project")
    confidence_score: float = Field(..., description="Confidence score (0-1) for the analysis")
    requires_confirmation: bool = Field(..., description="Whether user confirmation is needed")


class ConfirmationRequest(BaseModel):
    """Request model for summary confirmation."""
    
    session_id: str = Field(..., description="Session identifier")
    confirmed: bool = Field(..., description="Whether the user confirms the summary")
    additional_notes: Optional[str] = Field(None, description="Additional notes or corrections")


class StackDocumentation(BaseModel):
    """Documentation for a specific technology stack."""
    
    stack_type: str = Field(..., description="Type of stack (frontend, backend, database, devops)")
    title: str = Field(..., description="Title for this stack documentation")
    content: str = Field(..., description="Markdown content for this stack")
    technologies: List[str] = Field(..., description="List of technologies covered in this stack")
    estimated_effort: Optional[str] = Field(None, description="Estimated effort for this stack")


class DocumentGenerationRequest(BaseModel):
    """Request model for document generation (API 4)."""
    
    session_id: str = Field(..., description="Session identifier", example="sess_abc123def456")
    format_type: str = Field("markdown", description="Output format type", example="markdown")
    include_implementation_details: bool = Field(True, description="Whether to include implementation details")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123def456",
                "format_type": "markdown",
                "include_implementation_details": True
            }
        }


class DocumentGenerationResponse(BaseModel):
    """Response model for document generation (API 4)."""
    
    session_id: str = Field(..., description="Session identifier")
    stacks: List[StackDocumentation] = Field(..., description="Generated documentation by stack")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Generation timestamp")
    total_estimated_effort: Optional[str] = Field(None, description="Total estimated effort for the project")
    recommended_timeline: Optional[str] = Field(None, description="Recommended implementation timeline")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error_code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    session_id: Optional[str] = Field(None, description="Session ID if applicable")


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    environment: str = Field(..., description="Environment name")