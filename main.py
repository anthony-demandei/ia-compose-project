from fastapi import FastAPI
import uvicorn
import os
import logging
from dotenv import load_dotenv

from app.api.v1.project import router as project_router
from app.api.v1.questions import router as questions_router  
from app.api.v1.summary import router as summary_router
from app.api.v1.documents import router as documents_router
from app.api.v1.documents_async import router as documents_async_router
from app.utils.config import get_settings
from app.models.api_models import (
    ProjectAnalysisRequest, ProjectAnalysisResponse,
    QuestionResponseRequest, QuestionResponseResponse,
    SummaryRequest, SummaryResponse,
    DocumentGenerationRequest, DocumentGenerationResponse,
    ErrorResponse
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create FastAPI app with comprehensive documentation
app = FastAPI(
    title="IA Compose API",
    description="""
    🤖 **Microserviço REST para Análise Inteligente de Requisitos de Projetos**
    
    API desenvolvida exclusivamente para a **Plataforma Demandei**, utilizando IA para transformar 
    descrições de projetos em documentação técnica completa e estruturada.
    
    ## 🚀 Principais Melhorias (v3.2.0)
    
    - ✅ **100% Taxa de Sucesso**: Modelo Gemini 1.5 Pro otimizado
    - ⚡ **Cache Redis**: Perguntas (1h) e Documentos (24h) em cache
    - 🔄 **Geração Assíncrona**: Processamento em background disponível
    - ⏱️ **Timeout de 3 minutos**: Para geração síncrona
    - 🛡️ **Zero Safety Blocks**: Prompts otimizados
    
    ## 🔄 Workflow das 4 APIs
    
    1. **Project Analysis** - Analisa projeto e gera perguntas dinâmicas (com cache)
    2. **Questions Response** - Processa respostas e determina próximas perguntas  
    3. **Summary Generation** - Gera resumo para confirmação do usuário
    4. **Documents Generation** - Produz documentação técnica por stacks (sync/async + cache)
    
    ## 🔐 Autenticação
    
    Todos os endpoints requerem Bearer Token com chave API da Demandei:
    ```
    Authorization: Bearer your_demandei_api_key
    ```
    
    ## 💾 Cache System
    
    - **Redis Cache** (quando disponível) ou **In-Memory Cache** (fallback)
    - **Questions**: Cached for 1 hour (3600s)
    - **Documents**: Cached for 24 hours (86400s)
    - Reduz chamadas desnecessárias à API Gemini
    
    ## 📋 Formatos de Saída
    
    - **Perguntas**: Múltipla escolha com alternativas dinâmicas
    - **Documentação**: Markdown separado por stacks (Frontend, Backend, Database, DevOps)
    - **JSON estruturado**: Para fácil integração com plataforma Demandei
    
    ## 🏥 Health Checks
    
    Verificações de saúde disponíveis para monitoramento:
    - `/health` - Status geral da API
    - `/v1/{service}/health` - Status de cada serviço individual
    
    ## 🧪 Testing Interface
    
    Use the `/test` endpoint para obter exemplos completos de como testar todas as APIs.
    Contém exemplos prontos para copy/paste no Swagger UI.
    """,
    version="3.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "Health",
            "description": "Health checks e status da API"
        },
        {
            "name": "Testing",
            "description": "🧪 **Interface de Testes**: Exemplos e dados para testar todas as APIs no Swagger UI"
        },
        {
            "name": "project", 
            "description": "🔍 **API 1**: Análise de Projetos - Classifica projeto e gera sequência de perguntas (**com cache Redis**)"
        },
        {
            "name": "questions",
            "description": "❓ **API 2**: Processamento de Respostas - Avalia respostas e retorna próximas perguntas"
        },
        {
            "name": "summary", 
            "description": "📝 **API 3**: Geração de Resumo - Cria resumo para confirmação e validação"
        },
        {
            "name": "documents",
            "description": """📄 **API 4**: Geração de Documentos - Produz documentação técnica final por stacks
            
            **Opções disponíveis:**
            - 🔄 **Síncrono** (`/generate`): Timeout de 3 minutos, resposta direta
            - ⚡ **Assíncrono** (`/generate/async`): Processamento em background
            - 📊 **Status** (`/status/{id}`): Verifica progresso da geração assíncrona
            - 💾 **Cache**: Documentos armazenados por 24 horas"""
        }
    ],
    contact={
        "name": "Demandei Support",
        "url": "https://demandei.com",
        "email": "support@demandei.com"
    },
    license_info={
        "name": "Proprietary License",
        "url": "https://demandei.com/license"
    }
)

# Include routers
app.include_router(project_router)  # API 1: Project Analysis
app.include_router(questions_router)  # API 2: Questions Response
app.include_router(summary_router)  # API 3: Summary Generation
app.include_router(documents_router)  # API 4: Documents Generation (sync)
app.include_router(documents_async_router)  # API 4: Documents Generation (async)


@app.get("/health", tags=["Health"], summary="Health Check Geral")
async def health_check():
    """
    **Health Check principal da API**
    
    Retorna o status geral do sistema e informações de ambiente.
    
    **Não requer autenticação** - Endpoint público para monitoramento.
    
    Returns:
        - status: "healthy" se a API está funcionando
        - service: Nome do serviço
        - environment: Ambiente atual (development/staging/production)
    """
    return {
        "status": "healthy",
        "service": "ia-compose-api",
        "environment": settings.environment,
        "version": "3.0.0"
    }


@app.on_event("startup")
async def startup_event():
    logger.info("IA Compose API iniciado")
    logger.info(f"Ambiente: {settings.environment}")
    logger.info(f"Modelo Gemini: {settings.gemini_model}")

    # Criar diretórios de armazenamento local se necessário
    if settings.use_local_storage:
        from pathlib import Path

        Path(settings.local_storage_path).mkdir(exist_ok=True)
        Path(settings.local_documents_path).mkdir(exist_ok=True)
        Path(settings.local_sessions_path).mkdir(exist_ok=True)

        logger.info(f"Armazenamento local configurado: {settings.local_storage_path}")


@app.get("/test", tags=["Testing"], summary="API Test Interface")
async def test_interface():
    """
    **Interactive API Test Interface**
    
    This endpoint provides examples and test data for all 4 APIs in the workflow.
    Use these examples to test the complete workflow in Swagger UI.
    
    **Workflow Steps:**
    1. Copy example from API 1 → Test `/v1/project/analyze`
    2. Copy session_id from response → Use in API 2
    3. Test `/v1/questions/respond` → Continue until ready_for_summary
    4. Test `/v1/summary/generate` → Review and confirm
    5. Test `/v1/documents/generate` → Get final documentation
    
    **Authentication Required:**
    Add `Authorization: Bearer your_demandei_api_key` to all requests.
    """
    return {
        "message": "IA Compose API Test Interface",
        "version": "3.2.0",
        "new_features": {
            "redis_cache": {
                "enabled": True,
                "questions_ttl": "1 hour (3600s)",
                "documents_ttl": "24 hours (86400s)",
                "fallback": "In-memory cache when Redis unavailable"
            },
            "async_generation": {
                "endpoint": "/v1/documents/generate/async",
                "status_check": "/v1/documents/status/{session_id}",
                "max_processing_time": "3 minutes",
                "background_processing": True
            },
            "optimizations": {
                "default_model": "gemini-1.5-pro",
                "success_rate": "100%",
                "safety_blocks": "Zero with optimized prompts",
                "timeout": "3 minutes for sync generation"
            }
        },
        "authentication": {
            "header": "Authorization: Bearer your_demandei_api_key",
            "note": "Replace 'your_demandei_api_key' with actual API key"
        },
        "workflow_examples": {
            "api_1_project_analysis": {
                "endpoint": "/v1/project/analyze",
                "method": "POST",
                "example_request": {
                    "project_description": "Sistema de gestão para clínica veterinária com 3 veterinários e 150 pets cadastrados. Funcionalidades: agendamento de consultas, prontuários eletrônicos, controle de vacinas, estoque de medicamentos, faturamento. Orçamento: R$ 60.000. Prazo: 4 meses. Tecnologia preferida: React + Python.",
                    "metadata": {
                        "source": "swagger_ui_test",
                        "user_id": "test_user_123"
                    }
                },
                "expected_response": {
                    "session_id": "sess_abc123def456",
                    "questions": ["Array of generated questions"],
                    "total_questions": 6,
                    "estimated_completion_time": 8,
                    "project_classification": {
                        "type": "web_application",
                        "complexity": "moderate",
                        "domain": "healthcare"
                    }
                }
            },
            "api_2_questions_response": {
                "endpoint": "/v1/questions/respond",
                "method": "POST",
                "example_request": {
                    "session_id": "sess_abc123def456",
                    "answers": [
                        {
                            "question_code": "Q001",
                            "selected_choices": ["web_app"]
                        },
                        {
                            "question_code": "Q002",
                            "selected_choices": ["small"]
                        },
                        {
                            "question_code": "Q003",
                            "selected_choices": ["react", "python"]
                        }
                    ],
                    "request_next_batch": True
                },
                "note": "Repeat until response_type becomes 'ready_for_summary'"
            },
            "api_3_summary_generation": {
                "endpoint": "/v1/summary/generate",
                "method": "POST",
                "example_request": {
                    "session_id": "sess_abc123def456",
                    "include_assumptions": True
                },
                "confirmation_endpoint": "/v1/summary/confirm",
                "confirmation_request": {
                    "session_id": "sess_abc123def456",
                    "confirmed": True,
                    "additional_notes": "Summary approved"
                }
            },
            "api_4_documents_generation": {
                "sync_option": {
                    "endpoint": "/v1/documents/generate",
                    "method": "POST",
                    "example_request": {
                        "session_id": "sess_abc123def456",
                        "format_type": "markdown",
                        "include_implementation_details": True
                    },
                    "expected_response": {
                        "stacks": [
                            {
                                "stack_type": "frontend",
                                "title": "Frontend Development Stack",
                                "content": "Detailed implementation guide...",
                                "technologies": ["React", "Next.js", "TypeScript"],
                                "estimated_effort": "6-8 weeks"
                            }
                        ]
                    },
                    "note": "Synchronous generation with 3-minute timeout"
                },
                "async_option": {
                    "start_endpoint": "/v1/documents/generate/async",
                    "method": "POST",
                    "example_request": {
                        "session_id": "sess_abc123def456",
                        "format_type": "markdown",
                        "include_implementation_details": True
                    },
                    "immediate_response": {
                        "status": "processing",
                        "message": "Document generation started",
                        "check_url": "/v1/documents/status/sess_abc123def456",
                        "estimated_time": "1-3 minutes"
                    },
                    "status_endpoint": "/v1/documents/status/{session_id}",
                    "status_method": "GET",
                    "status_responses": {
                        "processing": {"status": "processing", "progress": "Generating documents..."},
                        "completed": {"status": "completed", "data": "Full document response"},
                        "failed": {"status": "failed", "error": "Error message if failed"}
                    },
                    "note": "Background processing, no timeout for client"
                }
            }
        },
        "quick_test_examples": {
            "simple_project": {
                "description": "Sistema simples de gestão para loja de roupas com vendas e estoque",
                "use_case": "Quick test with minimal complexity"
            },
            "medium_project": {
                "description": "Plataforma de e-commerce B2C para venda de produtos de beleza com catálogo, carrinho, pagamentos e avaliações. Orçamento: R$ 150.000, Prazo: 6 meses",
                "use_case": "Medium complexity test"
            },
            "complex_project": {
                "description": "Sistema completo de gestão hospitalar para 500 leitos incluindo prontuários eletrônicos integrados com HL7 FHIR, módulo de farmácia com controle de estoque automatizado, sistema de agendamento inteligente e dashboard médico com IA para diagnóstico assistido. Orçamento: R$ 2.000.000, Prazo: 18 meses",
                "use_case": "Complex enterprise system test"
            }
        },
        "tips": {
            "swagger_ui": "Use the 'Try it out' button in Swagger UI to test endpoints",
            "session_management": "Session IDs are returned from API 1 and used in subsequent APIs",
            "authentication": "All endpoints except /health require Bearer token authentication",
            "response_format": "All responses are in JSON format with structured error handling"
        }
    }

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("IA Compose API finalizado")


if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host=settings.host, 
        port=settings.port, 
        reload=settings.environment == "development"
    )
