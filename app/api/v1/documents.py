"""
Documents Generation API endpoint (API 4).
Handles final document generation with separated technology stacks.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from datetime import datetime
import logging

from app.models.api_models import (
    DocumentGenerationRequest,
    DocumentGenerationResponse,
    StackDocumentation,
    ErrorResponse
)
from app.middleware.auth import verify_demandei_api_key
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)

# Create router without global authentication dependency
router = APIRouter(
    prefix="/v1/documents",
    tags=["documents"]
)

# External session storage reference
from app.api.v1.questions import session_storage
from app.services.document_generator import DocumentGeneratorService
from app.services.redis_cache import get_redis_cache


@router.post("/generate", response_model=DocumentGenerationResponse)
async def generate_documents(
    request: DocumentGenerationRequest,
    authenticated: bool = Depends(verify_demandei_api_key)
) -> DocumentGenerationResponse:
    """
    Generate final project documentation separated by technology stacks.
    
    This is API 4 of the 4-API workflow. It generates comprehensive
    technical documentation organized by technology stacks (Frontend,
    Backend, Database, DevOps) based on confirmed project requirements.
    
    Args:
        request: Document generation request with session ID and options
        authenticated: Authentication verification (injected)
        
    Returns:
        DocumentGenerationResponse: Generated documentation by stack
        
    Raises:
        HTTPException: If session not found or document generation fails
    """
    try:
        logger.info(f"Generating documents for session {request.session_id}")
        
        # Check Redis cache first
        cache = get_redis_cache()
        cached_document = await cache.get_cached_document(request.session_id)
        
        if cached_document:
            logger.info(f"📦 Using cached documents for session {request.session_id}")
            # Return cached response
            return DocumentGenerationResponse(**cached_document)
        
        # Validate session exists and is confirmed
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
        
        # Check if summary was confirmed
        if session_data.get("status") != "confirmed_ready_for_documents":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code="SUMMARY_NOT_CONFIRMED",
                    message="Summary must be confirmed before generating documents",
                    session_id=request.session_id
                ).dict()
            )
        
        # Initialize document generator service
        doc_generator = DocumentGeneratorService()
        
        # Generate comprehensive documentation using the service
        project_classification = session_data.get("project_classification", {})
        answers = session_data.get("answers", [])
        
        # Set 3-minute timeout for document generation
        import asyncio
        try:
            stacks = await asyncio.wait_for(
                doc_generator.generate_documents(
                    session_data=session_data,
                    include_implementation=request.include_implementation_details
                ),
                timeout=180.0  # 3 minutes
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=ErrorResponse(
                    error_code="GENERATION_TIMEOUT",
                    message="Document generation timed out after 3 minutes",
                    details={"suggestion": "Use /v1/documents/generate/async for long-running generations"},
                    session_id=request.session_id
                ).dict()
            )
        
        # Calculate total effort based on generated stacks
        total_effort = doc_generator.calculate_total_effort(stacks)
        timeline = doc_generator.calculate_timeline(stacks)
        
        response = DocumentGenerationResponse(
            session_id=request.session_id,
            stacks=stacks,
            generated_at=datetime.utcnow(),
            total_estimated_effort=total_effort,
            recommended_timeline=timeline
        )
        
        # Cache the generated documents
        await cache.cache_document(request.session_id, response.dict())
        logger.info(f"💾 Cached documents for session {request.session_id} (24h TTL)")
        
        # Store generated documents in session
        session_data["generated_documents"] = response.dict()
        session_data["status"] = "completed"
        
        logger.info(f"Documents generated successfully for session {request.session_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="DOCUMENT_GENERATION_FAILED",
                message="Failed to generate project documents",
                details={"error": str(e)},
                session_id=request.session_id
            ).dict()
        )




@router.get("/health")
async def documents_health_check():
    """Health check for documents service."""
    return {
        "status": "healthy",
        "service": "document-generation",
        "version": "1.0.0"
    }