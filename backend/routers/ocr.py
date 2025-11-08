"""
OCR Transcription API Router
FastAPI endpoints for OCR transcription processing
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import JSONResponse

from ..models.transcription import (
    TranscriptionRequest,
    TranscriptionResponse,
    ErrorResponse,
    create_mongodb_document
)
from ..database.mongodb import get_mongo_manager  # type: ignore[reportMissingImports]
from ..database.operations import (  # type: ignore[reportMissingImports]
    insert_transcription,
    get_transcription_by_id,
    get_user_transcriptions,
    search_transcriptions,
    get_user_statistics,
    update_transcription_status,
    delete_transcription,
    create_indexes
)
import asyncio
from ..utils.llm import summarize_text  # type: ignore[reportMissingImports]
from pymongo.errors import DuplicateKeyError, PyMongoError

# Import RAG integration for automatic processing
from backend.api.rag.ocr_integration import process_ocr_output_for_rag

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/ocr", tags=["OCR Transcription"])


# ============================================================================
# Main Transcription Endpoint
# ============================================================================

@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit OCR transcription",
    description="Process and store OCR transcription data in MongoDB and trigger RAG processing"
)
async def transcribe_document(request: TranscriptionRequest, background_tasks: BackgroundTasks) -> TranscriptionResponse:
    """
    Process and store OCR transcription

    This endpoint receives OCR-processed data from the frontend and stores it
    in MongoDB for future retrieval and analysis.

    Args:
        request: TranscriptionRequest containing OCR data and metadata

    Returns:
        TranscriptionResponse with transcription_id

    Raises:
        HTTPException 400: Invalid request data
        HTTPException 409: Duplicate transcription_id
        HTTPException 500: Database error
    """
    try:
        logger.info(f"Received transcription request from user: {request.user_id}")

        # Generate unique transcription ID
        transcription_id = str(uuid.uuid4())
        logger.info(f"Generated transcription_id: {transcription_id}")

        # Create MongoDB document
        document = create_mongodb_document(transcription_id, request)

        # Log document statistics
        logger.info(
            f"Document stats - Words: {request.structured_content.word_count}, "
            f"Confidence: {request.ocr_data.confidence:.2f}%, "
            f"Type: {request.structured_content.document_type}"
        )

        # Get MongoDB collection
        mongo_manager = get_mongo_manager()
        collection = mongo_manager.collection

        # Insert into MongoDB
        await insert_transcription(collection, document)

        # Kick off background summarization job (non-blocking)
        try:
            background_tasks.add_task(summarize_and_update, transcription_id, request.ocr_data.cleaned_text)
        except Exception as e:
            logger.error(f"Failed to schedule summarization for {transcription_id}: {e}")

        # Create response
        response = TranscriptionResponse(
            success=True,
            transcription_id=transcription_id,
            message="Transcription processed successfully and queued for RAG processing",
            created_at=datetime.utcnow().isoformat()
        )

        logger.info(f"Successfully processed transcription: {transcription_id}")

        return response

    except DuplicateKeyError as e:
        logger.error(f"Duplicate transcription_id: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transcription with this ID already exists"
        )

    except PyMongoError as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data: {str(e)}"
        )

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


async def summarize_and_update(transcription_id: str, text: str) -> None:
    """Background task: summarize text using LLM and update MongoDB document."""
    logger.info(f"Starting summarization background task for {transcription_id}")
    mongo_manager = get_mongo_manager()
    collection = mongo_manager.collection

    try:
        # Run the potentially blocking LLM call in a thread
        result = await asyncio.to_thread(summarize_text, text)

        summary = result.get("summary", "")
        key_topics = result.get("key_topics", [])

        update_doc = {
            "content.summary": summary,
            "content.key_topics": key_topics,
            "updated_at": datetime.utcnow().isoformat()
        }

        await collection.update_one({"transcription_id": transcription_id}, {"$set": update_doc})
        logger.info(f"Summarization saved for {transcription_id}")

    except Exception as e:
        logger.exception(f"LLM summarization failed for {transcription_id}: {e}")
        try:
            await collection.update_one({"transcription_id": transcription_id}, {"$set": {"summary_error": str(e), "updated_at": datetime.utcnow().isoformat()}})
        except Exception:
            logger.exception(f"Failed to record summarization error for {transcription_id}")


@router.post(
    "/transcription/{transcription_id}/summarize",
    summary="Re-run summarization for a transcription",
    description="Enqueue a background job to re-run LLM summarization for the given transcription id"
)
async def rerun_summarization_endpoint(transcription_id: str, background_tasks: BackgroundTasks):
    """Admin-friendly endpoint to re-run the LLM summarization for an existing transcription.

    This schedules the same background job used during ingest. It will return 202 if queued.
    """
    try:
        mongo_manager = get_mongo_manager()
        collection = mongo_manager.collection

        doc = await get_transcription_by_id(collection, transcription_id)
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found")

        # Attempt to locate cleaned text
        text = None
        if isinstance(doc.get("content"), dict):
            text = doc["content"].get("cleaned_text") or doc["content"].get("raw_text")
        if not text:
            text = doc.get("searchable_text")

        if not text:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No text available to summarize")

        background_tasks.add_task(summarize_and_update, transcription_id, text)

        return {"queued": True, "transcription_id": transcription_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to enqueue summarization")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================================
# Query Endpoints
# ============================================================================

@router.get(
    "/transcription/{transcription_id}",
    summary="Get transcription by ID",
    description="Retrieve a specific transcription by its ID"
)
async def get_transcription(transcription_id: str):
    """
    Get a transcription by its ID

    Args:
        transcription_id: UUID of the transcription

    Returns:
        Transcription document

    Raises:
        HTTPException 404: Transcription not found
        HTTPException 500: Database error
    """
    try:
        logger.info(f"Fetching transcription: {transcription_id}")

        mongo_manager = get_mongo_manager()
        collection = mongo_manager.collection

        transcription = await get_transcription_by_id(collection, transcription_id)

        if transcription is None:
            logger.warning(f"Transcription not found: {transcription_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transcription with ID {transcription_id} not found"
            )

        return transcription

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching transcription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch transcription"
        )


@router.get(
    "/user/{user_id}/transcriptions",
    summary="Get user transcriptions",
    description="Retrieve all transcriptions for a specific user"
)
async def get_user_transcriptions_endpoint(
    user_id: str,
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    skip: int = Query(0, ge=0, description="Number of documents to skip"),
    sort_by: str = Query("created_at", description="Field to sort by")
):
    """
    Get all transcriptions for a user

    Args:
        user_id: User ID
        limit: Maximum number of results (1-100)
        skip: Number of documents to skip for pagination
        sort_by: Field to sort by

    Returns:
        List of transcription documents
    """
    try:
        logger.info(f"Fetching transcriptions for user: {user_id}")

        mongo_manager = get_mongo_manager()
        collection = mongo_manager.collection

        transcriptions = await get_user_transcriptions(
            collection,
            user_id,
            limit=limit,
            skip=skip,
            sort_by=sort_by
        )

        return {
            "user_id": user_id,
            "count": len(transcriptions),
            "limit": limit,
            "skip": skip,
            "transcriptions": transcriptions
        }

    except Exception as e:
        logger.error(f"Error fetching user transcriptions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user transcriptions"
        )


@router.get(
    "/search",
    summary="Search transcriptions",
    description="Full-text search across transcriptions"
)
async def search_transcriptions_endpoint(
    query: str = Query(..., min_length=1, description="Search query"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results")
):
    """
    Full-text search on transcriptions

    Args:
        query: Search query string
        user_id: Optional user ID to filter results
        limit: Maximum number of results

    Returns:
        List of matching transcriptions
    """
    try:
        logger.info(f"Searching transcriptions: '{query}'")

        mongo_manager = get_mongo_manager()
        collection = mongo_manager.collection

        results = await search_transcriptions(
            collection,
            search_query=query,
            user_id=user_id,
            limit=limit
        )

        return {
            "query": query,
            "user_id": user_id,
            "count": len(results),
            "results": results
        }

    except Exception as e:
        logger.error(f"Error searching transcriptions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )


@router.get(
    "/user/{user_id}/statistics",
    summary="Get user statistics",
    description="Get statistics for a user's transcriptions"
)
async def get_user_statistics_endpoint(user_id: str):
    """
    Get statistics for a user

    Args:
        user_id: User ID

    Returns:
        Statistics dictionary
    """
    try:
        logger.info(f"Getting statistics for user: {user_id}")

        mongo_manager = get_mongo_manager()
        collection = mongo_manager.collection

        stats = await get_user_statistics(collection, user_id)

        return stats

    except Exception as e:
        logger.error(f"Error getting user statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get statistics"
        )


# ============================================================================
# Update Endpoints
# ============================================================================

@router.patch(
    "/transcription/{transcription_id}/status",
    summary="Update transcription status",
    description="Update the processing status of a transcription"
)
async def update_status_endpoint(
    transcription_id: str,
    status_value: str = Query(..., regex="^(processing|processed|failed)$"),
    error_message: Optional[str] = Query(None)
):
    """
    Update transcription status

    Args:
        transcription_id: UUID of the transcription
        status_value: New status ('processing', 'processed', 'failed')
        error_message: Optional error message if status is 'failed'

    Returns:
        Success message
    """
    try:
        logger.info(f"Updating status for {transcription_id}: {status_value}")

        mongo_manager = get_mongo_manager()
        collection = mongo_manager.collection

        success = await update_transcription_status(
            collection,
            transcription_id,
            status_value,
            error_message
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transcription with ID {transcription_id} not found"
            )

        return {
            "success": True,
            "transcription_id": transcription_id,
            "status": status_value,
            "message": "Status updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update status"
        )


# ============================================================================
# Delete Endpoints
# ============================================================================

@router.delete(
    "/transcription/{transcription_id}",
    summary="Delete transcription",
    description="Delete a transcription by its ID"
)
async def delete_transcription_endpoint(transcription_id: str):
    """
    Delete a transcription

    Args:
        transcription_id: UUID of the transcription

    Returns:
        Success message
    """
    try:
        logger.info(f"Deleting transcription: {transcription_id}")

        mongo_manager = get_mongo_manager()
        collection = mongo_manager.collection

        success = await delete_transcription(collection, transcription_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transcription with ID {transcription_id} not found"
            )

        return {
            "success": True,
            "transcription_id": transcription_id,
            "message": "Transcription deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting transcription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete transcription"
        )


# ============================================================================
# Administrative Endpoints
# ============================================================================

@router.post(
    "/admin/create-indexes",
    summary="Create database indexes",
    description="Create necessary indexes for efficient queries (admin only)"
)
async def create_indexes_endpoint():
    """
    Create database indexes

    This endpoint should be called once after database setup to create
    necessary indexes for efficient queries.

    Returns:
        Success message
    """
    try:
        logger.info("Creating database indexes...")

        mongo_manager = get_mongo_manager()
        collection = mongo_manager.collection

        success = await create_indexes(collection)

        if success:
            return {
                "success": True,
                "message": "Indexes created successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create indexes"
            )

    except Exception as e:
        logger.error(f"Error creating indexes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create indexes: {str(e)}"
        )


@router.get(
    "/health",
    summary="Health check",
    description="Check MongoDB connection health"
)
async def health_check():
    """
    Health check endpoint

    Returns:
        Health status of MongoDB connection
    """
    try:
        mongo_manager = get_mongo_manager()
        health = mongo_manager.health_check()

        if health.get("status") == "healthy":
            return health
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=health
            )

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


# ============================================================================
# Example Usage
# ============================================================================

"""
# Example 1: Submit transcription
POST /api/ocr/transcribe
{
    "filename": "lecture_notes.jpg",
    "file_metadata": {...},
    "ocr_data": {...},
    "structured_content": {...},
    "user_id": "user123"
}

# Example 2: Get transcription by ID
GET /api/ocr/transcription/550e8400-e29b-41d4-a716-446655440000

# Example 3: Get user's transcriptions
GET /api/ocr/user/user123/transcriptions?limit=10&skip=0

# Example 4: Search transcriptions
GET /api/ocr/search?query=calculus&user_id=user123&limit=20

# Example 5: Get user statistics
GET /api/ocr/user/user123/statistics

# Example 6: Update status
PATCH /api/ocr/transcription/550e8400.../status?status_value=processed

# Example 7: Delete transcription
DELETE /api/ocr/transcription/550e8400-e29b-41d4-a716-446655440000

# Example 8: Create indexes (run once)
POST /api/ocr/admin/create-indexes

# Example 9: Health check
GET /api/ocr/health
"""
