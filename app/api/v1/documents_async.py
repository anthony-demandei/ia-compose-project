"""
Async Documents Generation API endpoints.
Handles document generation with background processing and status checking.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from datetime import datetime
import asyncio
import uuid
from typing import Dict, Any, Optional
import logging

from app.models.api_models import (
    DocumentGenerationRequest,
    DocumentGenerationResponse,
    ErrorResponse
)
from app.middleware.auth import verify_demandei_api_key
from app.utils.pii_safe_logging import get_pii_safe_logger
from app.api.v1.questions import session_storage
from app.services.document_generator import DocumentGeneratorService
from app.services.redis_cache import get_redis_cache

logger = get_pii_safe_logger(__name__)

# Create router
router = APIRouter(
    prefix="/v1/documents",
    tags=["documents"]
)

# In-memory storage for generation status (could be Redis in production)
generation_status: Dict[str, Dict[str, Any]] = {}


async def generate_documents_background(
    session_id: str,
    session_data: Dict[str, Any],
    include_implementation: bool
):
    """
    Background task to generate documents asynchronously.
    
    Args:
        session_id: Session identifier
        session_data: Complete session data
        include_implementation: Whether to include implementation details
    """
    try:
        # Update status to processing
        generation_status[session_id] = {
            "status": "processing",
            "started_at": datetime.utcnow().isoformat(),
            "progress": "Initializing document generation..."
        }
        
        # Initialize document generator
        doc_generator = DocumentGeneratorService()
        
        # Set a 3-minute timeout for generation
        try:
            # Generate documents with timeout
            stacks = await asyncio.wait_for(
                doc_generator.generate_documents(
                    session_data=session_data,
                    include_implementation=include_implementation
                ),
                timeout=180.0  # 3 minutes
            )
            
            # Calculate metrics
            total_effort = doc_generator.calculate_total_effort(stacks)
            timeline = doc_generator.calculate_timeline(stacks)
            
            # Create response
            response = DocumentGenerationResponse(
                session_id=session_id,
                stacks=stacks,
                generated_at=datetime.utcnow(),
                total_estimated_effort=total_effort,
                recommended_timeline=timeline
            )
            
            # Cache the generated documents (convert datetime to string for JSON)
            cache = get_redis_cache()
            response_dict = response.dict()
            response_dict['generated_at'] = response_dict['generated_at'].isoformat() if isinstance(response_dict.get('generated_at'), datetime) else str(response_dict.get('generated_at', ''))
            await cache.cache_document(session_id, response_dict)
            
            # Update status to completed
            generation_status[session_id] = {
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat(),
                "data": response.dict()
            }
            
            # Store in session
            session_data["generated_documents"] = response.dict()
            session_data["status"] = "completed"
            
            logger.info(f"Documents generated successfully for session {session_id}")
            
        except asyncio.TimeoutError:
            logger.error(f"Document generation timed out after 3 minutes for session {session_id}")
            generation_status[session_id] = {
                "status": "failed",
                "error": "Generation timed out after 3 minutes",
                "failed_at": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error in background document generation: {str(e)}")
        generation_status[session_id] = {
            "status": "failed",
            "error": str(e),
            "failed_at": datetime.utcnow().isoformat()
        }


@router.post("/generate/async")
async def generate_documents_async(
    request: DocumentGenerationRequest,
    background_tasks: BackgroundTasks,
    authenticated: bool = Depends(verify_demandei_api_key)
) -> Dict[str, Any]:
    """
    Start async document generation in background.
    
    Returns immediately with a status URL to check progress.
    """
    try:
        logger.info(f"Starting async document generation for session {request.session_id}")
        
        # Check Redis cache first
        cache = get_redis_cache()
        cached_document = await cache.get_cached_document(request.session_id)
        
        if cached_document:
            logger.info(f"📦 Returning cached documents for session {request.session_id}")
            return {
                "status": "completed",
                "message": "Documents retrieved from cache",
                "data": cached_document
            }
        
        # Validate session
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
        
        # Check if generation is already in progress
        if request.session_id in generation_status:
            current_status = generation_status[request.session_id]
            if current_status["status"] == "processing":
                return {
                    "status": "processing",
                    "message": "Document generation already in progress",
                    "check_url": f"/v1/documents/status/{request.session_id}"
                }
        
        # Start background generation
        background_tasks.add_task(
            generate_documents_background,
            request.session_id,
            session_data,
            request.include_implementation_details
        )
        
        # Return immediate response with status URL
        return {
            "status": "processing",
            "message": "Document generation started",
            "check_url": f"/v1/documents/status/{request.session_id}",
            "estimated_time": "1-3 minutes"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting async document generation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="ASYNC_GENERATION_FAILED",
                message="Failed to start document generation",
                details={"error": str(e)},
                session_id=request.session_id
            ).dict()
        )


@router.get("/status/{session_id}")
async def get_generation_status(
    session_id: str,
    authenticated: bool = Depends(verify_demandei_api_key)
) -> Dict[str, Any]:
    """
    Check the status of document generation.
    
    Returns:
        - status: "processing", "completed", or "failed"
        - data: Generated documents if completed
        - error: Error message if failed
    """
    # Check if generation status exists
    if session_id not in generation_status:
        # Check if documents are already in session storage
        if session_id in session_storage:
            session_data = session_storage[session_id]
            if "generated_documents" in session_data:
                return {
                    "status": "completed",
                    "message": "Documents already generated",
                    "data": session_data["generated_documents"]
                }
        
        # Check Redis cache
        cache = get_redis_cache()
        cached_document = await cache.get_cached_document(session_id)
        if cached_document:
            return {
                "status": "completed",
                "message": "Documents retrieved from cache",
                "data": cached_document
            }
        
        return {
            "status": "not_found",
            "message": "No generation process found for this session"
        }
    
    # Return current status
    current_status = generation_status[session_id]
    
    # Clean up completed/failed status after returning
    if current_status["status"] in ["completed", "failed"]:
        # Keep status for 5 minutes before cleanup
        pass  # In production, implement TTL-based cleanup
    
    return current_status