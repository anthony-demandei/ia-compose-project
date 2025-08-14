from fastapi import FastAPI
import uvicorn
import os
import logging
from dotenv import load_dotenv

from app.api.v1.project import router as project_router
from app.api.v1.questions import router as questions_router  
from app.api.v1.summary import router as summary_router
from app.api.v1.documents import router as documents_router
from app.utils.config import get_settings

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
    
    ## 🔄 Workflow das 4 APIs
    
    1. **Project Analysis** - Analisa projeto e gera perguntas dinâmicas
    2. **Questions Response** - Processa respostas e determina próximas perguntas  
    3. **Summary Generation** - Gera resumo para confirmação do usuário
    4. **Documents Generation** - Produz documentação técnica por stacks
    
    ## 🔐 Autenticação
    
    Todos os endpoints requerem Bearer Token com chave API da Demandei:
    ```
    Authorization: Bearer your_demandei_api_key
    ```
    
    ## 📋 Formatos de Saída
    
    - **Perguntas**: Múltipla escolha com alternativas dinâmicas
    - **Documentação**: Markdown separado por stacks (Frontend, Backend, Database, DevOps)
    - **JSON estruturado**: Para fácil integração com plataforma Demandei
    
    ## 🏥 Health Checks
    
    Verificações de saúde disponíveis para monitoramento:
    - `/health` - Status geral da API
    - `/v1/{service}/health` - Status de cada serviço individual
    """,
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "Health",
            "description": "Health checks e status da API"
        },
        {
            "name": "project", 
            "description": "🔍 **API 1**: Análise de Projetos - Classifica projeto e gera sequência de perguntas"
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
            "description": "📄 **API 4**: Geração de Documentos - Produz documentação técnica final por stacks"
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
app.include_router(documents_router)  # API 4: Documents Generation


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


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("IA Compose API finalizado")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=settings.environment == "development")
