"""
Summary Generation API endpoint (API 3).
Handles summary generation and confirmation from collected responses.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
import logging

from app.models.api_models import (
    SummaryRequest,
    SummaryResponse,
    ConfirmationRequest,
    ConfirmationResponse,
    Question,
    QuestionChoice,
    ErrorResponse
)
from app.middleware.auth import verify_demandei_api_key
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)

# Create router without global authentication dependency
router = APIRouter(
    prefix="/v1/summary",
    tags=["summary"]
)

# External session storage reference (would be proper session management in production)
from app.api.v1.questions import session_storage


@router.post("/generate", response_model=SummaryResponse)
async def generate_summary(
    request: SummaryRequest,
    authenticated: bool = Depends(verify_demandei_api_key)
) -> SummaryResponse:
    """
    Generate project summary from collected responses.
    
    This is API 3 of the 4-API workflow. It analyzes all collected responses
    and generates a comprehensive summary for user confirmation.
    
    Args:
        request: Summary generation request with session ID
        authenticated: Authentication verification (injected)
        
    Returns:
        SummaryResponse: Generated summary with key points and assumptions
        
    Raises:
        HTTPException: If session not found or summary generation fails
    """
    try:
        logger.info(f"Generating summary for session {request.session_id}")
        
        # Validate session exists
        if request.session_id not in session_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="SESSION_NOT_FOUND",
                    message="Session not found or expired",
                    session_id=request.session_id
                ).dict()
            )
        
        session_data = session_storage[request.session_id]
        answers = session_data["answers"]
        
        # TODO: Replace with actual AI summary generation
        # This is a placeholder showing the expected structure
        
        # Analyze answers to generate summary
        summary_text = _generate_summary_from_answers(answers)
        key_points = _extract_key_points(answers)
        assumptions = _generate_assumptions(answers) if request.include_assumptions else []
        
        # Calculate confidence based on completeness of answers
        confidence_score = min(1.0, len(answers) / 5.0)  # Assuming 5 is the ideal number
        
        response = SummaryResponse(
            session_id=request.session_id,
            summary=summary_text,
            key_points=key_points,
            assumptions=assumptions,
            confidence_score=confidence_score,
            requires_confirmation=True
        )
        
        # Store summary in session for later use
        session_data["summary"] = response.dict()
        
        logger.info(f"Summary generated for session {request.session_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="SUMMARY_GENERATION_FAILED",
                message="Failed to generate project summary",
                details={"error": str(e)},
                session_id=request.session_id
            ).dict()
        )


@router.post("/confirm", response_model=ConfirmationResponse)
async def confirm_summary(
    request: ConfirmationRequest,
    authenticated: bool = Depends(verify_demandei_api_key)
) -> ConfirmationResponse:
    """
    Confirm or reject the generated summary.
    
    Args:
        request: Confirmation request with session ID and confirmation status
        authenticated: Authentication verification (injected)
        
    Returns:
        Dict with confirmation status and next steps
        
    Raises:
        HTTPException: If session not found or confirmation fails
    """
    try:
        logger.info(f"Processing summary confirmation for session {request.session_id}")
        
        # Validate session exists
        if request.session_id not in session_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="SESSION_NOT_FOUND",
                    message="Session not found or expired",
                    session_id=request.session_id
                ).dict()
            )
        
        session_data = session_storage[request.session_id]
        
        # Store confirmation and additional notes
        session_data["confirmation"] = {
            "confirmed": request.confirmed,
            "additional_notes": request.additional_notes,
            "confirmed_at": "2025-01-06T12:00:00Z"  # TODO: Use actual timestamp
        }
        
        if request.confirmed:
            # Mark session as ready for document generation
            session_data["status"] = "confirmed_ready_for_documents"
            message = "Resumo confirmado. Pronto para gerar documentação técnica."
            next_step = "document_generation"
            refinement_questions = None
        else:
            # Mark session as needing revision
            session_data["status"] = "needs_refinement"
            message = "Resumo rejeitado. Por favor, responda às perguntas de refinamento para melhorar o entendimento."
            next_step = "answer_refinement_questions"
            
            # Generate refinement questions based on feedback
            refinement_questions = await _generate_refinement_questions(
                session_data,
                request.feedback or request.additional_notes
            )
            
            # Store refinement questions in session for tracking
            session_data["refinement_questions"] = [q.dict() for q in refinement_questions]
            session_data["refinement_cycle"] = session_data.get("refinement_cycle", 0) + 1
        
        response = ConfirmationResponse(
            session_id=request.session_id,
            confirmation_status="confirmed" if request.confirmed else "rejected",
            message=message,
            next_step=next_step,
            ready_for_documents=request.confirmed,
            refinement_questions=refinement_questions
        )
        
        logger.info(f"Summary confirmation processed for session {request.session_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="CONFIRMATION_FAILED",
                message="Failed to process summary confirmation",
                details={"error": str(e)},
                session_id=request.session_id
            ).dict()
        )


def _generate_summary_from_answers(answers) -> str:
    """Generate markdown summary from collected answers."""
    # TODO: Replace with actual AI summary generation
    
    summary = """# Resumo do Projeto

## Visão Geral
Com base nas informações coletadas, identificamos um projeto de desenvolvimento de aplicação web com as seguintes características principais:

## Tipo de Projeto
- **Categoria**: Aplicação Web
- **Complexidade**: Moderada
- **Equipe**: Pequena/Média (2-5 desenvolvedores)

## Requisitos Técnicos
- **Frontend**: React/Next.js ou tecnologia similar
- **Backend**: Python (FastAPI/Django) ou Node.js
- **Banco de Dados**: PostgreSQL ou MySQL
- **Hospedagem**: Cloud (AWS/Azure/GCP)

## Cronograma e Orçamento
- **Prazo Estimado**: 3-6 meses
- **Orçamento**: R$ 50.000 - R$ 200.000
- **Metodologia**: Desenvolvimento ágil com entregas incrementais

## Próximos Passos
1. Refinamento dos requisitos funcionais
2. Definição da arquitetura técnica
3. Criação dos protótipos
4. Início do desenvolvimento
"""
    
    return summary


def _extract_key_points(answers) -> list:
    """Extract key points from answers."""
    # TODO: Replace with actual AI extraction
    return [
        "Aplicação web com interface moderna",
        "Necessidade de integração com APIs externas",
        "Requisitos de performance moderados",
        "Equipe experiente em tecnologias web",
        "Cronograma flexível com entregas incrementais"
    ]


def _generate_assumptions(answers) -> list:
    """Generate AI assumptions based on answers."""
    # TODO: Replace with actual AI assumption generation
    return [
        "Assumido uso de banco de dados relacional (PostgreSQL)",
        "Inferido hospedagem em cloud pública",
        "Pressuposto desenvolvimento responsivo para mobile",
        "Considerado uso de metodologia ágil/scrum",
        "Estimado deployment em ambiente de produção separado"
    ]


async def _generate_refinement_questions(
    session_data: dict,
    feedback: Optional[str] = None
) -> List[Question]:
    """
    Generate refinement questions based on rejected summary and user feedback.
    
    Args:
        session_data: Current session data with summary and answers
        feedback: User feedback about what needs improvement
        
    Returns:
        List of refinement questions to clarify project requirements
    """
    from app.services.ai_factory import get_ai_provider
    
    try:
        # Get the AI provider
        ai_provider = get_ai_provider()
        
        # Build context from session data
        project_description = session_data.get("project_description", "")
        previous_answers = session_data.get("answers", [])
        summary = session_data.get("summary", {})
        refinement_cycle = session_data.get("refinement_cycle", 1)
        
        # Create AI prompt for refinement questions
        prompt = f"""
        O resumo do projeto foi rejeitado. Gere 3-4 perguntas de refinamento para esclarecer pontos duvidosos.
        
        Projeto Original: {project_description}
        
        Feedback do Usuário: {feedback or "Não fornecido"}
        
        Ciclo de Refinamento: {refinement_cycle}
        
        Gere perguntas específicas para resolver ambiguidades ou coletar informações faltantes.
        Retorne um JSON com array "questions", cada uma com:
        - code: string (R001, R002, etc.)
        - text: string (pergunta clara e específica)
        - why_it_matters: string (por que esta informação é crítica)
        - choices: array de opções com id, text e description (opcional)
        - required: boolean (sempre true para refinamento)
        - allow_multiple: boolean
        - category: string (sempre "refinement")
        
        Foque em aspectos técnicos não esclarecidos, requisitos de performance, integrações, ou restrições de negócio.
        """
        
        # Generate questions using AI
        response = await ai_provider.generate_json_response(
            messages=[
                {"role": "system", "content": "You are a requirements analyst generating clarification questions. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        # Parse and validate questions
        questions_data = response.get("questions", [])
        questions = []
        
        for idx, q_data in enumerate(questions_data[:4]):  # Limit to 4 questions
            try:
                # Build choices
                choices = []
                for choice_data in q_data.get("choices", []):
                    choices.append(QuestionChoice(
                        id=choice_data.get("id", f"opt_{idx}"),
                        text=choice_data.get("text", "Option"),
                        description=choice_data.get("description")
                    ))
                
                # If no choices provided, add yes/no options
                if not choices:
                    choices = [
                        QuestionChoice(id="yes", text="Sim"),
                        QuestionChoice(id="no", text="Não"),
                        QuestionChoice(id="maybe", text="Talvez/Parcialmente")
                    ]
                
                # Create question
                question = Question(
                    code=q_data.get("code", f"R{str(idx+1).zfill(3)}"),
                    text=q_data.get("text", f"Pergunta de refinamento {idx+1}"),
                    why_it_matters=q_data.get("why_it_matters", "Informação necessária para refinar o entendimento do projeto"),
                    choices=choices,
                    required=True,
                    allow_multiple=q_data.get("allow_multiple", False),
                    category="refinement"
                )
                questions.append(question)
            except Exception as e:
                logger.warning(f"Failed to parse refinement question {idx}: {e}")
                continue
        
        # If AI fails or returns no questions, use fallback questions
        if not questions:
            questions = _get_fallback_refinement_questions(feedback)
        
        return questions
        
    except Exception as e:
        logger.error(f"Error generating refinement questions: {e}")
        # Return fallback questions on error
        return _get_fallback_refinement_questions(feedback)


def _get_fallback_refinement_questions(feedback: Optional[str] = None) -> List[Question]:
    """
    Get fallback refinement questions when AI generation fails.
    
    Args:
        feedback: User feedback to consider
        
    Returns:
        List of standard refinement questions
    """
    questions = [
        Question(
            code="R001",
            text="Qual é o nível de disponibilidade (SLA) esperado para o sistema?",
            why_it_matters="Define a arquitetura de alta disponibilidade e redundância necessária",
            choices=[
                QuestionChoice(id="sla_95", text="95% (18.25 dias de downtime/ano)", description="Adequado para sistemas não-críticos"),
                QuestionChoice(id="sla_99", text="99% (3.65 dias de downtime/ano)", description="Padrão para aplicações comerciais"),
                QuestionChoice(id="sla_999", text="99.9% (8.76 horas de downtime/ano)", description="Alta disponibilidade"),
                QuestionChoice(id="sla_9999", text="99.99% (52.56 minutos de downtime/ano)", description="Muito alta disponibilidade"),
                QuestionChoice(id="sla_not_defined", text="Não definido ainda")
            ],
            required=True,
            allow_multiple=False,
            category="refinement"
        ),
        Question(
            code="R002",
            text="Qual é o volume esperado de usuários simultâneos no pico?",
            why_it_matters="Determina a arquitetura de escalabilidade e recursos necessários",
            choices=[
                QuestionChoice(id="users_100", text="Até 100 usuários"),
                QuestionChoice(id="users_1000", text="100 - 1.000 usuários"),
                QuestionChoice(id="users_10000", text="1.000 - 10.000 usuários"),
                QuestionChoice(id="users_100000", text="10.000 - 100.000 usuários"),
                QuestionChoice(id="users_more", text="Mais de 100.000 usuários")
            ],
            required=True,
            allow_multiple=False,
            category="refinement"
        ),
        Question(
            code="R003",
            text="Existem requisitos específicos de segurança ou compliance?",
            why_it_matters="Impacta diretamente na arquitetura de segurança e escolha de tecnologias",
            choices=[
                QuestionChoice(id="lgpd", text="LGPD (Lei Geral de Proteção de Dados)"),
                QuestionChoice(id="pci_dss", text="PCI-DSS (Pagamentos com cartão)"),
                QuestionChoice(id="hipaa", text="HIPAA (Dados de saúde)"),
                QuestionChoice(id="iso27001", text="ISO 27001"),
                QuestionChoice(id="sox", text="SOX (Sarbanes-Oxley)"),
                QuestionChoice(id="none", text="Nenhum requisito específico")
            ],
            required=True,
            allow_multiple=True,
            category="refinement"
        )
    ]
    
    # Add a question about specific feedback if provided
    if feedback and len(feedback) > 10:
        questions.append(Question(
            code="R004",
            text=f"Com base no seu feedback: '{feedback[:100]}...', qual aspecto precisa ser mais detalhado?",
            why_it_matters="Permite focar no ponto específico de preocupação do cliente",
            choices=[
                QuestionChoice(id="architecture", text="Arquitetura técnica"),
                QuestionChoice(id="features", text="Funcionalidades específicas"),
                QuestionChoice(id="timeline", text="Cronograma e fases"),
                QuestionChoice(id="budget", text="Orçamento e custos"),
                QuestionChoice(id="team", text="Equipe e recursos"),
                QuestionChoice(id="other", text="Outro aspecto")
            ],
            required=True,
            allow_multiple=True,
            category="refinement"
        ))
    
    return questions


@router.get("/health")
async def summary_health_check():
    """Health check for summary service."""
    return {
        "status": "healthy",
        "service": "summary-generation",
        "version": "1.0.0"
    }