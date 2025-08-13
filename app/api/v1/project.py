"""
Project Analysis API endpoint (API 1).
Handles initial project description analysis and question generation.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
import uuid
import logging

from app.models.api_models import (
    ProjectAnalysisRequest,
    ProjectAnalysisResponse,
    Question,
    QuestionChoice,
    ErrorResponse
)
from app.middleware.auth import verify_demandei_api_key
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
        
        # TODO: Replace with actual AI analysis service
        # For now, return sample questions to demonstrate the structure
        sample_questions = [
            Question(
                code="Q001",
                text="Qual o tipo principal do seu projeto?",
                choices=[
                    QuestionChoice(id="web_app", text="Aplicação Web"),
                    QuestionChoice(id="mobile_app", text="Aplicativo Mobile"),
                    QuestionChoice(id="desktop_app", text="Software Desktop"),
                    QuestionChoice(id="api_service", text="API/Microserviço"),
                    QuestionChoice(id="ecommerce", text="E-commerce"),
                    QuestionChoice(id="other", text="Outro tipo")
                ],
                required=True,
                allow_multiple=False,
                category="business"
            ),
            Question(
                code="Q002", 
                text="Qual o tamanho estimado da equipe de desenvolvimento?",
                choices=[
                    QuestionChoice(id="solo", text="1 desenvolvedor"),
                    QuestionChoice(id="small", text="2-5 desenvolvedores"),
                    QuestionChoice(id="medium", text="6-15 desenvolvedores"),
                    QuestionChoice(id="large", text="16+ desenvolvedores")
                ],
                required=True,
                allow_multiple=False,
                category="technical"
            ),
            Question(
                code="Q003",
                text="Quais tecnologias você tem preferência ou restrições?",
                choices=[
                    QuestionChoice(id="react", text="React/Next.js"),
                    QuestionChoice(id="vue", text="Vue.js/Nuxt.js"),
                    QuestionChoice(id="angular", text="Angular"),
                    QuestionChoice(id="python", text="Python (Django/FastAPI)"),
                    QuestionChoice(id="nodejs", text="Node.js"),
                    QuestionChoice(id="dotnet", text=".NET"),
                    QuestionChoice(id="java", text="Java/Spring"),
                    QuestionChoice(id="no_preference", text="Sem preferência")
                ],
                required=False,
                allow_multiple=True,
                category="technical"
            )
        ]
        
        # TODO: Replace with actual AI classification
        project_classification = {
            "type": "web_application",
            "complexity": "moderate",
            "domain": "generic",
            "confidence": 0.85,
            "key_technologies": ["web", "database", "api"],
            "estimated_duration": "3-6 months"
        }
        
        response = ProjectAnalysisResponse(
            session_id=session_id,
            questions=sample_questions,
            total_questions=len(sample_questions),
            estimated_completion_time=5,
            project_classification=project_classification
        )
        
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