"""
Project Analysis API endpoint (API 1).
Handles initial project description analysis and question generation.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
import uuid
import logging
from datetime import datetime

from app.models.api_models import (
    ProjectAnalysisRequest,
    ProjectAnalysisResponse,
    Question,
    QuestionChoice,
    ErrorResponse
)
from app.middleware.auth import verify_demandei_api_key
from app.services.question_engine import QuestionEngine
from app.services.ai_factory import get_ai_provider
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)

# Create router without global authentication dependency
router = APIRouter(
    prefix="/v1/project",
    tags=["project"]
)


@router.post("/analyze", 
    response_model=ProjectAnalysisResponse,
    summary="🔍 Análise de Projeto (API 1)",
    description="""
    **API 1 do workflow de 4 etapas**
    
    Analisa a descrição textual do projeto e gera uma sequência inteligente de perguntas
    de múltipla escolha para coletar informações adicionais necessárias.
    
    ### Funcionalidades:
    - ✅ Classificação automática do tipo de projeto (web, mobile, enterprise, etc.)
    - ✅ Análise de complexidade (simples, moderada, complexa, enterprise)
    - ✅ Geração dinâmica de perguntas contextuais
    - ✅ Criação de session ID para rastreamento
    - ✅ Estimativa de tempo de conclusão
    
    ### Validações:
    - `project_description`: Entre 50 e 8000 caracteres
    - `metadata`: Opcional, deve ser um objeto JSON válido
    
    ### Próximo Passo:
    Use o `session_id` retornado para chamar `/v1/questions/respond`
    """,
    responses={
        200: {
            "description": "Projeto analisado com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "session_id": "sess_abc123def456",
                        "questions": [
                            {
                                "code": "Q001",
                                "text": "Qual o tipo principal da aplicação?",
                                "choices": [
                                    {"id": "web_app", "text": "Aplicação Web", "description": "Sistema acessível via navegador"},
                                    {"id": "mobile_app", "text": "Aplicativo Mobile", "description": "App nativo ou híbrido"}
                                ],
                                "required": True,
                                "allow_multiple": False,
                                "category": "business"
                            }
                        ],
                        "total_questions": 5,
                        "estimated_completion_time": 8,
                        "project_classification": {
                            "type": "web_application",
                            "complexity": "moderate",
                            "domain": "healthcare",
                            "confidence": 0.85
                        }
                    }
                }
            }
        },
        401: {"description": "🔒 API key ausente ou inválida"},
        422: {"description": "📝 Erro de validação - descrição muito curta/longa"},
        500: {"description": "💥 Erro interno na análise do projeto"}
    }
)
async def analyze_project(
    request: ProjectAnalysisRequest,
    authenticated: bool = Depends(verify_demandei_api_key)
) -> ProjectAnalysisResponse:
    """
    **🔍 Analisa descrição do projeto e gera perguntas inteligentes**
    
    Esta é a **API 1** do workflow de 4 etapas. Recebe uma descrição de projeto,
    analisa usando IA, e retorna uma sequência de perguntas de múltipla escolha
    com códigos únicos para o cliente apresentar aos usuários.
    
    **Fluxo:**
    1. Recebe descrição do projeto
    2. Classifica tipo e complexidade 
    3. Gera perguntas contextuais
    4. Retorna session_id + perguntas
    
    **Args:**
        - request: Dados do projeto com descrição e metadados
        - authenticated: Verificação de autenticação (injetada)
        
    **Returns:**
        - ProjectAnalysisResponse: Session ID e sequência de perguntas geradas
        
    **Raises:**
        - HTTPException: Se análise falhar ou entrada inválida
    """
    try:
        logger.info("Starting project analysis for new session")
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Initialize question engine
        question_engine = QuestionEngine()
        
        # Generate questions dynamically using AI with enhanced context
        session_context = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "request_metadata": request.metadata if hasattr(request, 'metadata') else {}
        }
        
        questions = await question_engine.generate_questions_for_project(
            project_description=request.project_description,
            max_questions=5  # Start with 5 questions
        )
        
        # If no questions generated, return error
        if not questions:
            logger.error("AI failed to generate questions")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate questions for the project"
            )
        
        # Use AI to classify the project
        ai_provider = get_ai_provider()
        classification_prompt = f"""
        Analyze this project and return a JSON with:
        - type: main project type (web_app, mobile_app, api, system, automation, other)
        - complexity: simple, moderate, complex, or enterprise
        - confidence: 0.0 to 1.0
        - key_aspects: list of 3-5 key technical aspects
        - estimated_effort: rough estimate (e.g., "2-3 months", "6-12 months")
        
        Project: {request.project_description}
        
        Return ONLY valid JSON.
        """
        
        try:
            classification_response = await ai_provider.generate_json_response(
                messages=[
                    {"role": "system", "content": "You are a project analyst. Return only JSON."},
                    {"role": "user", "content": classification_prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # Ensure proper structure
            project_classification = {
                "type": classification_response.get("type", "system"),
                "complexity": classification_response.get("complexity", "moderate"),
                "domain": "dynamic",  # No fixed domains anymore
                "confidence": classification_response.get("confidence", 0.8),
                "key_technologies": classification_response.get("key_aspects", []),
                "estimated_duration": classification_response.get("estimated_effort", "3-6 months")
            }
        except Exception as e:
            logger.warning(f"Classification failed, using defaults: {e}")
            project_classification = {
                "type": "system",
                "complexity": "moderate",
                "domain": "dynamic",
                "confidence": 0.7,
                "key_technologies": [],
                "estimated_duration": "To be determined"
            }
        
        # Build response
        response = ProjectAnalysisResponse(
            session_id=session_id,
            questions=questions,
            total_questions=len(questions),
            estimated_completion_time=len(questions) * 2,  # ~2 min per question
            project_classification=project_classification
        )
        
        # Store session context for future use
        from app.api.v1.questions import session_storage
        session_storage[session_id] = {
            "project_description": request.project_description,
            "project_classification": project_classification,
            "questions": questions,
            "answers": [],
            "question_count": len(questions),
            "total_answered": 0,
            "timestamp": datetime.now().isoformat(),
            "status": "active"
        }
        
        logger.info(f"Project analysis completed for session {session_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error in project analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="ANALYSIS_FAILED",
                message="Failed to analyze project description",
                details={"error": str(e)}
            ).dict()
        )


@router.get("/health", 
    tags=["Health"],
    summary="🏥 Health Check - Serviço de Análise de Projetos",
    description="Verifica o status do serviço de análise de projetos (API 1). **Não requer autenticação.**"
)
async def project_health_check():
    """
    **🏥 Health check para o serviço de análise de projetos**
    
    Endpoint público para monitoramento da saúde da API 1.
    
    **Returns:**
        - status: "healthy" se o serviço está funcionando
        - service: Nome do serviço
        - version: Versão do serviço
    """
    return {
        "status": "healthy",
        "service": "project-analysis",
        "version": "1.0.0"
    }