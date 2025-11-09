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
import asyncio

from pymongo.errors import DuplicateKeyError, PyMongoError

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
from ..utils.llm import summarize_text  # type: ignore[reportMissingImports]

# Optional RAG integration (don’t crash if not present)
try:
    from backend.api.rag.ocr_integration import process_ocr_output_for_rag  # noqa: F401
except Exception:
    process_ocr_output_for_rag = None  # type: ignore

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
    description="Process and store OCR transcription data in MongoDB and trigger background summarization"
)
async def transcribe_document(request: TranscriptionRequest, background_tasks: BackgroundTasks) -> TranscriptionResponse:
    """
    Accepts client-side OCR data, stores it, and schedules summarization.
    """
    try:
        user_id = request.user_id or "guest"
        logger.info(f"Received transcription request from user: {user_id}")

        # Generate unique transcription ID (UUID to match your models)
        transcription_id = str(uuid.uuid4())
        logger.info(f"Generated transcription_id: {transcription_id}")

        # Create MongoDB document from your model helper
        document = create_mongodb_document(transcription_id, request)

        # Ensure the content fields exist so UI polling never breaks
        document.setdefault("content", {})
        document["content"].setdefault("summary", None)
        document["content"].setdefault("key_topics", [])

        # Light metrics logging (guard Nones)
        wc = (request.structured_content.word_count
              if request.structured_content and request.structured_content.word_count is not None else 0)
        conf = (request.ocr_data.confidence
                if request.ocr_data and request.ocr_data.confidence is not None else 0.0)
        doc_type = (request.structured_content.document_type
                    if request.structured_content and request.structured_content.document_type else "unknown")
        logger.info(f"Document stats - Words: {wc}, Confidence: {conf}, Type: {doc_type}")

        # Insert into MongoDB
        mongo_manager = get_mongo_manager()
        collection = mongo_manager.collection
        await insert_transcription(collection, document)

        # Kick off background summarization job (non-blocking)
        # prefer cleaned_text, fallback to raw_text, else empty
        cleaned = (request.ocr_data.cleaned_text or "").strip()
        raw = (request.ocr_data.raw_text or "").strip()
        text_for_summary = cleaned or raw
        try:
            background_tasks.add_task(summarize_and_update, transcription_id, text_for_summary)
        except Exception as e:
            logger.error(f"Failed to schedule summarization for {transcription_id}: {e}")

        # (Optional) RAG post-processing if you want (and module exists)
        # if process_ocr_output_for_rag:
        #     background_tasks.add_task(process_ocr_output_for_rag, transcription_id, document)

        # Create response
        response = TranscriptionResponse(
            success=True,
            transcription_id=transcription_id,
            message="Transcription stored and summarization queued",
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
    """Background task: summarize text using your LLM util and update MongoDB document."""
    logger.info(f"Starting summarization background task for {transcription_id}")
    mongo_manager = get_mongo_manager()
    collection = mongo_manager.collection

    try:
        # Run the potentially blocking LLM call in a thread
        result = await asyncio.to_thread(summarize_text, text or "")

        summary = result.get("summary", "") if isinstance(result, dict) else ""
        key_topics = result.get("key_topics", []) if isinstance(result, dict) else []

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
            await collection.update_one(
                {"transcription_id": transcription_id},
                {"$set": {
                    "content.summary": f"(summary failed: {e})",
                    "content.key_topics": [],
                    "updated_at": datetime.utcnow().isoformat()
                }}
            )
        except Exception:
            logger.exception(f"Failed to record summarization error for {transcription_id}")


@router.post(
    "/transcription/{transcription_id}/summarize",
    summary="Re-run summarization for a transcription",
    description="Enqueue a background job to re-run LLM summarization for the given transcription id"
)
async def rerun_summarization_endpoint(transcription_id: str, background_tasks: BackgroundTasks):
    """Re-run the LLM summarization for an existing transcription."""
    try:
        mongo_manager = get_mongo_manager()
        collection = mongo_manager.collection

        doc = await get_transcription_by_id(collection, transcription_id)
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found")

        # Try to find the best text to summarize
        text = None
        if isinstance(doc.get("content"), dict):
            text = doc["content"].get("cleaned_text") or doc["content"].get("raw_text")
        if not text:
            # Many pipelines put the source text in OCR fields or a denormalized field
            ocr = doc.get("ocr_data") or {}
            text = ocr.get("cleaned_text") or ocr.get("raw_text") or doc.get("searchable_text")

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
    """Fetch a single transcription by UUID id."""
    try:
        logger.info(f"Fetching transcription: {transcription_id}")
        mongo_manager = get_mongo_manager()
        collection = mongo_manager.collection
        transcription = await get_transcription_by_id(collection, transcription_id)
        if transcription is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found")
        return transcription
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching transcription: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch transcription")


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
    """List transcriptions for a given user id."""
    try:
        logger.info(f"Fetching transcriptions for user: {user_id}")
        mongo_manager = get_mongo_manager()
        collection = mongo_manager.collection
        transcriptions = await get_user_transcriptions(collection, user_id, limit=limit, skip=skip, sort_by=sort_by)
        return {
            "user_id": user_id,
            "count": len(transcriptions),
            "limit": limit,
            "skip": skip,
            "transcriptions": transcriptions
        }
    except Exception as e:
        logger.error(f"Error fetching user transcriptions: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch user transcriptions")


@router.get(
    "/transcriptions",
    summary="Public list of transcriptions (guest-friendly)",
    description="List transcriptions by user_id (use user_id=guest for anonymous uploads)"
)
async def list_transcriptions_public(
    user_id: Optional[str] = Query(None, description="User id to filter by (e.g., 'guest')"),
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    sort_by: str = Query("created_at")
):
    """
    Compatibility endpoint for the frontend:
    GET /api/ocr/transcriptions?user_id=guest
    """
    try:
        user = user_id or "guest"
        mongo_manager = get_mongo_manager()
        collection = mongo_manager.collection
        items = await get_user_transcriptions(collection, user, limit=limit, skip=skip, sort_by=sort_by)
        return {"user_id": user, "count": len(items), "limit": limit, "skip": skip, "transcriptions": items}
    except Exception as e:
        logger.error(f"Error listing transcriptions: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list transcriptions")


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
    """Full-text search wrapper."""
    try:
        logger.info(f"Searching transcriptions: '{query}'")
        mongo_manager = get_mongo_manager()
        collection = mongo_manager.collection
        results = await search_transcriptions(collection, search_query=query, user_id=user_id, limit=limit)
        return {"query": query, "user_id": user_id, "count": len(results), "results": results}
    except Exception as e:
        logger.error(f"Error searching transcriptions: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Search failed")


@router.get(
    "/user/{user_id}/statistics",
    summary="Get user statistics",
    description="Get statistics for a user's transcriptions"
)
async def get_user_statistics_endpoint(user_id: str):
    """User-level stats."""
    try:
        logger.info(f"Getting statistics for user: {user_id}")
        mongo_manager = get_mongo_manager()
        collection = mongo_manager.collection
        stats = await get_user_statistics(collection, user_id)
        return stats
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get statistics")


# ============================================================================
# Update / Delete
# ============================================================================

@router.patch(
    "/transcription/{transcription_id}/status",
    summary="Update transcription status",
    description="Update the processing status of a transcription"
)
async def update_status_endpoint(
    transcription_id: str,
    status_value: str = Query(..., pattern="^(processing|processed|failed)$"),
    error_message: Optional[str] = Query(None)
):
    """Update status helper."""
    try:
        logger.info(f"Updating status for {transcription_id}: {status_value}")
        mongo_manager = get_mongo_manager()
        collection = mongo_manager.collection
        success = await update_transcription_status(collection, transcription_id, status_value, error_message)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found")
        return {"success": True, "transcription_id": transcription_id, "status": status_value, "message": "Status updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating status: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update status")


@router.delete(
    "/transcription/{transcription_id}",
    summary="Delete transcription",
    description="Delete a transcription by its ID"
)
async def delete_transcription_endpoint(transcription_id: str):
    """Delete by id."""
    try:
        logger.info(f"Deleting transcription: {transcription_id}")
        mongo_manager = get_mongo_manager()
        collection = mongo_manager.collection
        success = await delete_transcription(collection, transcription_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found")
        return {"success": True, "transcription_id": transcription_id, "message": "Transcription deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting transcription: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete transcription")


# ============================================================================
# Admin / Health
# ============================================================================

@router.post(
    "/admin/create-indexes",
    summary="Create database indexes",
    description="Create necessary indexes for efficient queries (admin only)"
)
async def create_indexes_endpoint():
    """Create indexes once after setup."""
    try:
        logger.info("Creating database indexes...")
        mongo_manager = get_mongo_manager()
        collection = mongo_manager.collection
        success = await create_indexes(collection)
        if success:
            return {"success": True, "message": "Indexes created successfully"}
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create indexes")
    except Exception as e:
        logger.error(f"Error creating indexes: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create indexes: {str(e)}")


@router.get(
    "/health",
    summary="Health check",
    description="Check MongoDB connection health"
)
async def health_check():
    """Simple Mongo health probe."""
    try:
        mongo_manager = get_mongo_manager()
        health = mongo_manager.health_check()
        if health.get("status") == "healthy":
            return health
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=health)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"status": "unhealthy", "error": str(e)})