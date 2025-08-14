"""
Questions Response API endpoint (API 2).
Handles question responses and returns next batch of questions or completion status.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
import logging

from app.models.api_models import (
    QuestionResponseRequest,
    QuestionResponseResponse,
    QuestionResponseType,
    Question,
    QuestionChoice,
    ErrorResponse
)
from app.middleware.auth import verify_demandei_api_key
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)

# Create router without global authentication dependency
router = APIRouter(
    prefix="/v1/questions",
    tags=["questions"]
)

# In-memory session storage for demo (TODO: replace with proper session management)
session_storage = {}


@router.post("/respond", response_model=QuestionResponseResponse)
async def respond_to_questions(
    request: QuestionResponseRequest,
    authenticated: bool = Depends(verify_demandei_api_key)
) -> QuestionResponseResponse:
    """
    Process question responses and return next batch or completion status.
    
    This is API 2 of the 4-API workflow. It processes answers to questions
    and determines whether to provide more questions or proceed to summary.
    
    Args:
        request: Question responses with session ID and answers
        authenticated: Authentication verification (injected)
        
    Returns:
        QuestionResponseResponse: Next questions or completion status
        
    Raises:
        HTTPException: If session not found or processing fails
    """
    try:
        logger.info(f"Processing question responses for session {request.session_id}")
        
        # Validate session exists
        if request.session_id not in session_storage:
            logger.warning(f"Session {request.session_id} not found in storage, creating minimal session")
            # Initialize minimal session storage for demo
            session_storage[request.session_id] = {
                "answers": [],
                "question_count": 0,
                "total_answered": 0,
                "project_description": "Not provided",
                "project_classification": {}
            }
        
        # Store answers
        session_data = session_storage[request.session_id]
        session_data["answers"].extend(request.answers)
        session_data["total_answered"] += len(request.answers)
        
        # Calculate completion percentage
        # TODO: Replace with actual logic based on AI analysis
        completion_percentage = min(100.0, (session_data["total_answered"] / 5) * 100)
        
        # Determine if we need more questions or can proceed to summary
        if completion_percentage >= 60:  # Enough information collected
            return QuestionResponseResponse(
                session_id=request.session_id,
                response_type=QuestionResponseType.READY_FOR_SUMMARY,
                next_questions=None,
                completion_percentage=completion_percentage,
                message="Informações suficientes coletadas. Pronto para gerar resumo."
            )
        
        # Generate next batch of questions
        next_questions = _generate_next_questions(session_data["answers"])
        
        if not next_questions:
            # Last question - allow text input for additional details
            next_questions = [
                Question(
                    code="Q_FINAL",
                    text="Há alguma informação adicional importante que não foi coberta pelas perguntas anteriores?",
                    why_it_matters="Informações adicionais podem revelar requisitos críticos ou restrições que impactam significativamente o projeto.",
                    choices=[
                        QuestionChoice(id="none", text="Não, as informações estão completas"),
                        QuestionChoice(id="has_more", text="Sim, tenho informações adicionais", 
                                     description="Será solicitado texto livre na próxima etapa")
                    ],
                    required=True,
                    allow_multiple=False,
                    category="final"
                )
            ]
        
        response = QuestionResponseResponse(
            session_id=request.session_id,
            response_type=QuestionResponseType.MORE_QUESTIONS,
            next_questions=next_questions,
            completion_percentage=completion_percentage,
            message=f"Perguntas processadas. {len(next_questions)} pergunta(s) adicional(is)."
        )
        
        logger.info(f"Question response processed for session {request.session_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error processing question responses: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="RESPONSE_PROCESSING_FAILED",
                message="Failed to process question responses",
                details={"error": str(e)},
                session_id=request.session_id
            ).dict()
        )


def _generate_next_questions(previous_answers: List) -> List[Question]:
    """
    Generate next batch of questions based on previous answers.
    
    Args:
        previous_answers: List of previous answers
        
    Returns:
        List[Question]: Next questions to ask
    """
    # TODO: Replace with actual AI-driven question generation
    # This is a simplified example showing conditional question flow
    
    if len(previous_answers) == 1:
        # Second batch of questions
        return [
            Question(
                code="Q004",
                text="Qual o orçamento estimado para o projeto?",
                why_it_matters="O orçamento define o escopo técnico, tecnologias viáveis e complexidade da solução que pode ser implementada.",
                choices=[
                    QuestionChoice(id="low", text="Até R$ 50.000"),
                    QuestionChoice(id="medium", text="R$ 50.000 - R$ 200.000"),
                    QuestionChoice(id="high", text="R$ 200.000 - R$ 500.000"),
                    QuestionChoice(id="enterprise", text="Acima de R$ 500.000"),
                    QuestionChoice(id="not_defined", text="Ainda não definido")
                ],
                required=True,
                allow_multiple=False,
                category="business"
            )
        ]
    
    elif len(previous_answers) == 2:
        # Third batch of questions
        return [
            Question(
                code="Q005",
                text="Qual o prazo desejado para conclusão?",
                why_it_matters="O prazo impacta diretamente na metodologia de desenvolvimento, tamanho da equipe e priorização de funcionalidades.",
                choices=[
                    QuestionChoice(id="urgent", text="Menos de 2 meses"),
                    QuestionChoice(id="normal", text="2-6 meses"),
                    QuestionChoice(id="extended", text="6-12 meses"),
                    QuestionChoice(id="flexible", text="Mais de 12 meses"),
                    QuestionChoice(id="not_defined", text="Flexível")
                ],
                required=True,
                allow_multiple=False,
                category="business"
            )
        ]
    
    # No more questions after 3 batches
    return []


@router.get("/health")
async def questions_health_check():
    """Health check for questions service."""
    return {
        "status": "healthy",
        "service": "questions-response",
        "version": "1.0.0"
    }