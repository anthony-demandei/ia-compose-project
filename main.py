from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import logging
from dotenv import load_dotenv

from app.api.intake import router as intake_router  # Sistema de intake inteligente
from app.api.multi_agent import router as multi_agent_router  # Sistema multi-agent
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

# Create FastAPI app
app = FastAPI(
    title="Intelligent Intake System",
    description="AI-powered intake system for project requirements with multi-agent architecture",
    version="2.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(intake_router)  # Sistema de intake inteligente
app.include_router(multi_agent_router)  # Sistema multi-agent para intake avançado

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve storage files (for local development)
if settings.use_local_storage:
    from pathlib import Path

    storage_path = Path(settings.local_storage_path)
    if storage_path.exists():
        app.mount("/storage", StaticFiles(directory=str(storage_path)), name="storage")


@app.get("/")
async def root():
    """Serve the intake interface HTML page."""
    return FileResponse("static/index.html")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "intelligent-intake",
        "environment": settings.environment,
    }


@app.on_event("startup")
async def startup_event():
    logger.info("Intelligent Intake System iniciado")
    logger.info(f"Ambiente: {settings.environment}")
    logger.info(f"Modelo OpenAI: {settings.openai_model}")
    logger.info(
        f"Context Inference: {'Enabled' if settings.enable_context_inference else 'Disabled'}"
    )
    logger.info(f"Smart Filtering: {'Enabled' if settings.enable_smart_filtering else 'Disabled'}")
    logger.info(f"Multi-Agent: {'Enabled' if settings.enable_multi_agent else 'Disabled'}")

    # Criar diretórios de armazenamento local se necessário
    if settings.use_local_storage:
        from pathlib import Path

        Path(settings.local_storage_path).mkdir(exist_ok=True)
        Path(settings.local_documents_path).mkdir(exist_ok=True)
        Path(settings.local_sessions_path).mkdir(exist_ok=True)

        # Criar diretórios para uploads
        uploads_path = Path("storage/uploads")
        uploads_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Armazenamento local configurado: {settings.local_storage_path}")
        logger.info(f"Diretório de uploads criado: {uploads_path}")

    # Inicializar Redis se habilitado
    if settings.use_redis_cache:
        try:
            from app.services.redis_service import get_redis_service

            redis_service = await get_redis_service()
            if redis_service:
                logger.info("Cache Redis inicializado")
        except Exception as e:
            logger.warning(f"Redis não disponível: {str(e)}")
            logger.info("Continuando sem cache Redis")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Discovery Chat Microservice finalizado")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=settings.environment == "development")
