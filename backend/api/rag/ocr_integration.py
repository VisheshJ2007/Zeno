"""
OCR Integration Module
Hooks into existing OCR pipeline to process documents for RAG
"""

from typing import Optional, Dict
from fastapi import BackgroundTasks
from datetime import datetime
import logging

from .chunking import chunker
from .rag_engine import rag_engine

logger = logging.getLogger(__name__)


async def process_ocr_output_for_rag(
    ocr_text: str,
    course_id: str,
    doc_type: str,
    source_file: str,
    metadata: Optional[Dict] = None,
    background_tasks: Optional[BackgroundTasks] = None
):
    """
    Process OCR output for RAG system
    Called AFTER OCR extraction completes

    This function:
    1. Chunks the text based on document type
    2. Generates embeddings for each chunk
    3. Stores chunks with embeddings in MongoDB

    Args:
        ocr_text: Extracted text from OCR
        course_id: Course identifier (e.g., "CS101_Fall_2024")
        doc_type: Document type (syllabus, lecture_notes, textbook, exam)
        source_file: Original filename or storage path
        metadata: Optional additional metadata
        background_tasks: Optional FastAPI background tasks handler

    Usage:
        # In your OCR endpoint, add this after successful OCR:
        await process_ocr_output_for_rag(
            ocr_text=extracted_text,
            course_id="CS101_Fall_2024",
            doc_type="lecture_notes",
            source_file=filename,
            metadata={"topic": "Introduction to Algorithms"},
            background_tasks=background_tasks  # Optional: for async processing
        )
    """

    logger.info(f"Starting RAG processing for {source_file} (course: {course_id}, type: {doc_type})")

    if background_tasks:
        # Process in background to not block response
        background_tasks.add_task(
            _embed_and_store,
            ocr_text,
            course_id,
            doc_type,
            source_file,
            metadata
        )
        logger.info("RAG processing queued as background task")
    else:
        # Process immediately
        await _embed_and_store(
            ocr_text,
            course_id,
            doc_type,
            source_file,
            metadata
        )


async def _embed_and_store(
    text: str,
    course_id: str,
    doc_type: str,
    source_file: str,
    metadata: Optional[Dict]
):
    """
    Internal function to chunk, embed, and store document

    Args:
        text: Document text
        course_id: Course identifier
        doc_type: Document type
        source_file: Source filename
        metadata: Optional metadata
    """

    try:
        logger.info(f"Chunking document: {source_file}")

        # 1. Chunk the document
        chunks = chunker.chunk_document(text, doc_type, metadata)

        logger.info(f"Created {len(chunks)} chunks for {source_file}")

        # 2. Generate embeddings and store each chunk
        successful_chunks = 0
        failed_chunks = 0

        for i, chunk in enumerate(chunks):
            try:
                # Generate embedding
                embedding = await rag_engine.generate_embedding(chunk["text"])

                # Store in MongoDB
                document = {
                    "course_id": course_id,
                    "doc_type": doc_type,
                    "source_file": source_file,
                    "chunk_index": chunk["metadata"]["chunk_index"],
                    "content": chunk["text"],
                    "content_vector": embedding,
                    "metadata": chunk["metadata"],
                    "created_at": datetime.utcnow()
                }

                rag_engine.course_materials.insert_one(document)
                successful_chunks += 1

                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1}/{len(chunks)} chunks for {source_file}")

            except Exception as e:
                logger.error(f"Failed to process chunk {i} of {source_file}: {e}")
                failed_chunks += 1

        # Log summary
        logger.info(
            f"✓ RAG processing completed for {source_file}: "
            f"{successful_chunks} successful, {failed_chunks} failed"
        )

        if failed_chunks > 0:
            logger.warning(f"Some chunks failed for {source_file}. Check logs for details.")

    except Exception as e:
        logger.error(f"❌ RAG processing failed for {source_file}: {e}", exc_info=True)
        raise


def extract_course_id_from_metadata(metadata: Dict) -> Optional[str]:
    """
    Extract course ID from document metadata

    Attempts to extract course identifier from various metadata fields.
    You should customize this based on your metadata structure.

    Args:
        metadata: Document metadata

    Returns:
        Course ID string or None
    """

    # Try various field names
    for field in ["course_id", "courseId", "course", "subject", "class_name"]:
        if field in metadata and metadata[field]:
            return str(metadata[field])

    # Try to construct from multiple fields
    if "course_code" in metadata and "semester" in metadata and "year" in metadata:
        return f"{metadata['course_code']}_{metadata['semester']}_{metadata['year']}"

    return None


def infer_doc_type(filename: str, text: str) -> str:
    """
    Infer document type from filename and content

    Args:
        filename: Document filename
        text: Document text

    Returns:
        Document type string
    """

    filename_lower = filename.lower()

    # Check filename
    if "syllabus" in filename_lower:
        return "syllabus"
    elif "lecture" in filename_lower or "notes" in filename_lower:
        return "lecture_notes"
    elif "exam" in filename_lower or "test" in filename_lower or "quiz" in filename_lower:
        return "exam"
    elif "textbook" in filename_lower or "chapter" in filename_lower:
        return "textbook"

    # Check content
    text_lower = text.lower()
    if "syllabus" in text_lower and "course" in text_lower:
        return "syllabus"
    elif any(word in text_lower for word in ["exam", "test questions", "name:", "score:"]):
        return "exam"

    # Default
    return "lecture_notes"


async def reprocess_document(
    transcription_id: str,
    course_id: str,
    doc_type: Optional[str] = None
):
    """
    Reprocess an existing OCR transcription for RAG

    Useful if you want to add RAG support to existing transcriptions.

    Args:
        transcription_id: Transcription ID from MongoDB
        course_id: Course identifier
        doc_type: Optional document type (will be inferred if not provided)
    """

    try:
        # Get transcription from MongoDB
        from backend.database.mongodb import get_mongo_manager
        from backend.database.operations import get_transcription_by_id

        mongo_manager = get_mongo_manager()
        collection = mongo_manager.collection

        transcription = await get_transcription_by_id(collection, transcription_id)

        if not transcription:
            logger.error(f"Transcription not found: {transcription_id}")
            return False

        # Extract text
        ocr_text = transcription.get("content", {}).get("structured_content", {}).get("full_text", "")
        filename = transcription.get("filename", "unknown")

        if not ocr_text:
            logger.error(f"No text found in transcription: {transcription_id}")
            return False

        # Infer doc_type if not provided
        if not doc_type:
            doc_type = infer_doc_type(filename, ocr_text)

        logger.info(f"Reprocessing transcription {transcription_id} as {doc_type}")

        # Process for RAG
        await _embed_and_store(
            text=ocr_text,
            course_id=course_id,
            doc_type=doc_type,
            source_file=filename,
            metadata={"transcription_id": transcription_id}
        )

        logger.info(f"✓ Reprocessed transcription {transcription_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to reprocess transcription {transcription_id}: {e}")
        return False


# Utility function for batch processing
async def batch_process_transcriptions(
    course_id: str,
    user_id: Optional[str] = None,
    limit: int = 100
):
    """
    Batch process existing transcriptions for RAG

    Useful for adding RAG support to existing data.

    Args:
        course_id: Course identifier to use for all transcriptions
        user_id: Optional user ID to filter transcriptions
        limit: Maximum number of transcriptions to process
    """

    try:
        from backend.database.mongodb import get_mongo_manager
        from backend.database.operations import get_user_transcriptions

        mongo_manager = get_mongo_manager()
        collection = mongo_manager.collection

        # Get transcriptions
        if user_id:
            transcriptions = await get_user_transcriptions(
                collection, user_id, limit=limit
            )
        else:
            # Get all transcriptions
            cursor = collection.find({}).limit(limit)
            transcriptions = list(cursor)

        logger.info(f"Batch processing {len(transcriptions)} transcriptions")

        successful = 0
        failed = 0

        for transcription in transcriptions:
            transcription_id = transcription.get("transcription_id")

            try:
                result = await reprocess_document(transcription_id, course_id)
                if result:
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Failed to process {transcription_id}: {e}")
                failed += 1

        logger.info(
            f"Batch processing complete: {successful} successful, {failed} failed"
        )

        return {
            "total": len(transcriptions),
            "successful": successful,
            "failed": failed
        }

    except Exception as e:
        logger.error(f"Batch processing error: {e}")
        return {
            "error": str(e)
        }
