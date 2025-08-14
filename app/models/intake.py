"""
Modelos de dados para o sistema de intake inteligente.
Define estruturas para sessões de intake, catálogo de perguntas e respostas.
"""

from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from enum import Enum


class QuestionType(str, Enum):
    """Tipos de perguntas suportadas no wizard."""

    SINGLE_CHOICE = "single_choice"
    MULTI_CHOICE = "multi_choice"
    TEXT = "text"
    NUMBER = "number"
    FILE = "file"


class IntakeStatus(str, Enum):
    """Status da sessão de intake."""

    DRAFT = "draft"
    ASKING = "asking"
    SUMMARIZED = "summarized"
    SCOPED = "scoped"


class QuestionStage(str, Enum):
    """Estágios das perguntas para organização."""

    BUSINESS = "business"
    USERS = "users"
    FUNCTIONAL = "functional"
    TECHNICAL = "technical"  # Adicionado para compatibilidade com V2 catalog
    NFR = "nfr"
    SECURITY = "security"
    TECH = "tech"
    DELIVERY = "delivery"


class QuestionOption(BaseModel):
    """Opção para perguntas de escolha."""

    id: str
    label: str


class QuestionCondition(BaseModel):
    """Condição para exibição condicional de perguntas."""

    all: Optional[List[Dict[str, Any]]] = None  # {"q": "Q1", "op": "in", "v": ["value"]}
    any: Optional[List[Dict[str, Any]]] = None


class Question(BaseModel):
    """Modelo de uma pergunta do catálogo."""

    id: str
    text: str
    type: QuestionType
    stage: QuestionStage
    options: Optional[List[QuestionOption]] = None
    tags: List[str] = Field(default_factory=list)
    required: bool = False
    weight: int = 0
    condition: Optional[QuestionCondition] = None
    version: int = 1
    embedding: Optional[List[float]] = None  # Vetor de embedding para similaridade


class IntakeRequest(BaseModel):
    """Request para iniciar uma sessão de intake."""

    text: str = Field(..., min_length=10, max_length=5000)
    metadata: Optional[Dict[str, Any]] = None


class IntakeSession(BaseModel):
    """Sessão de intake com texto inicial e perguntas selecionadas."""

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    intake_text: str
    question_ids: List[str] = Field(default_factory=list)
    version: int = 1
    status: IntakeStatus = IntakeStatus.DRAFT
    metadata: Optional[Dict[str, Any]] = None

    # Dados derivados
    answers: Dict[str, Any] = Field(default_factory=dict)  # question_id -> value
    summary: Optional[str] = None
    final_note: Optional[str] = None
    scope_document: Optional[str] = None


class Answer(BaseModel):
    """Resposta a uma pergunta do wizard."""

    session_id: UUID
    question_id: str
    value: Any  # Pode ser string, lista, número, etc.
    answered_at: datetime = Field(default_factory=datetime.utcnow)


class AnswersRequest(BaseModel):
    """Request para enviar respostas do wizard."""

    answers: List[Dict[str, Any]]  # [{"questionId": "Q1", "value": "..."}]


class IntakeArtifact(BaseModel):
    """Artefato gerado (resumo, escopo, etc.)."""

    session_id: UUID
    kind: Literal["summary", "scope_md"]
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


class QuestionSelectionResult(BaseModel):
    """Resultado da seleção inteligente de perguntas."""

    selected_ids: List[str]
    selection_metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "selected_ids": ["Q_FUNC_TIPO", "Q_FINALIDADE", "Q_PAGTO_GATEWAY"],
                "selection_metadata": {
                    "tags_identified": ["ecommerce", "pagamento"],
                    "similarity_scores": {"Q_FUNC_TIPO": 0.95},
                    "total_candidates": 50,
                },
            }
        }


class WizardState(BaseModel):
    """Estado atual do wizard para uma sessão."""

    session_id: UUID
    current_question_index: int = 0
    answered_questions: List[str] = Field(default_factory=list)
    remaining_questions: List[str] = Field(default_factory=list)
    conditional_questions: List[str] = Field(default_factory=list)

    def get_next_questions(self, batch_size: int = 3) -> List[str]:
        """Retorna próximas perguntas a serem exibidas."""
        return self.remaining_questions[:batch_size]

    def mark_answered(self, question_ids: List[str]):
        """Marca perguntas como respondidas."""
        for qid in question_ids:
            if qid in self.remaining_questions:
                self.remaining_questions.remove(qid)
                self.answered_questions.append(qid)


class SummaryResponse(BaseModel):
    """Response com resumo das respostas."""

    summary: str
    ask_for_more: bool = True
    completion_percentage: float

    class Config:
        json_schema_extra = {
            "example": {
                "summary": "## Resumo do Projeto\n\n**Objetivo:** E-commerce B2B...",
                "ask_for_more": True,
                "completion_percentage": 85.0,
            }
        }


class ScopeDocument(BaseModel):
    """Documento de escopo gerado."""

    session_id: UUID
    content: str  # Markdown
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1
    assumptions: List[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "content": "# Escopo do Projeto\n\n## 1. Objetivo de Negócio...",
                "assumptions": [
                    "Assumido uso de PostgreSQL como banco principal",
                    "Inferido prazo de 3 meses baseado na complexidade",
                ],
            }
        }
