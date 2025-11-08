"""
MongoDB Operations Module
CRUD operations for OCR transcriptions
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError
from pymongo import ASCENDING, DESCENDING, TEXT

logger = logging.getLogger(__name__)


# ============================================================================
# Index Creation
# ============================================================================

async def create_indexes(collection: Collection) -> bool:
    """
    Create necessary indexes for efficient queries

    Indexes:
    - user_id: For user-specific queries
    - transcription_id: Unique index for lookups
    - created_at: For sorting by date
    - status: For filtering by status
    - searchable_text: Text index for full-text search

    Args:
        collection: MongoDB collection

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("Creating MongoDB indexes...")

        # Create indexes
        indexes_created = []

        # 1. user_id index (for user-specific queries)
        result = collection.create_index(
            [("user_id", ASCENDING)],
            name="user_id_index"
        )
        indexes_created.append(result)
        logger.info(f"Created index: {result}")

        # 2. transcription_id unique index (for unique lookups)
        result = collection.create_index(
            [("transcription_id", ASCENDING)],
            name="transcription_id_unique_index",
            unique=True
        )
        indexes_created.append(result)
        logger.info(f"Created unique index: {result}")

        # 3. created_at index (for sorting by date)
        result = collection.create_index(
            [("created_at", DESCENDING)],
            name="created_at_index"
        )
        indexes_created.append(result)
        logger.info(f"Created index: {result}")

        # 4. status index (for filtering)
        result = collection.create_index(
            [("status", ASCENDING)],
            name="status_index"
        )
        indexes_created.append(result)
        logger.info(f"Created index: {result}")

        # 5. Compound index: user_id + created_at (for user queries with sorting)
        result = collection.create_index(
            [("user_id", ASCENDING), ("created_at", DESCENDING)],
            name="user_created_compound_index"
        )
        indexes_created.append(result)
        logger.info(f"Created compound index: {result}")

        # 6. Text index for full-text search on searchable_text
        result = collection.create_index(
            [("searchable_text", TEXT)],
            name="searchable_text_index"
        )
        indexes_created.append(result)
        logger.info(f"Created text index: {result}")

        # 7. Document type index (for filtering by type)
        result = collection.create_index(
            [("content.structured_content.document_type", ASCENDING)],
            name="document_type_index"
        )
        indexes_created.append(result)
        logger.info(f"Created index: {result}")

        logger.info(f"Successfully created {len(indexes_created)} indexes")
        return True

    except Exception as e:
        logger.error(f"Failed to create indexes: {str(e)}")
        return False


async def list_indexes(collection: Collection) -> List[Dict[str, Any]]:
    """
    List all indexes on the collection

    Args:
        collection: MongoDB collection

    Returns:
        List of index information dictionaries
    """
    try:
        indexes = list(collection.list_indexes())
        logger.info(f"Found {len(indexes)} indexes")
        return indexes
    except Exception as e:
        logger.error(f"Failed to list indexes: {str(e)}")
        return []


# ============================================================================
# Insert Operations
# ============================================================================

async def insert_transcription(
    collection: Collection,
    document: Dict[str, Any]
) -> str:
    """
    Insert a transcription document into MongoDB

    Args:
        collection: MongoDB collection
        document: Document dictionary to insert

    Returns:
        transcription_id of inserted document

    Raises:
        DuplicateKeyError: If transcription_id already exists
        PyMongoError: For other MongoDB errors
    """
    try:
        transcription_id = document.get("transcription_id")

        logger.info(f"Inserting transcription: {transcription_id}")

        # Insert document
        result = collection.insert_one(document)

        logger.info(
            f"Successfully inserted transcription {transcription_id} "
            f"with _id: {result.inserted_id}"
        )

        return transcription_id

    except DuplicateKeyError as e:
        logger.error(f"Duplicate transcription_id: {transcription_id}")
        raise DuplicateKeyError(
            f"Transcription with ID {transcription_id} already exists"
        )

    except PyMongoError as e:
        logger.error(f"Failed to insert transcription: {str(e)}")
        raise PyMongoError(f"Database error: {str(e)}")


async def insert_many_transcriptions(
    collection: Collection,
    documents: List[Dict[str, Any]]
) -> List[str]:
    """
    Insert multiple transcription documents

    Args:
        collection: MongoDB collection
        documents: List of document dictionaries

    Returns:
        List of transcription_ids

    Raises:
        PyMongoError: For MongoDB errors
    """
    try:
        logger.info(f"Inserting {len(documents)} transcriptions...")

        result = collection.insert_many(documents, ordered=False)
        transcription_ids = [doc["transcription_id"] for doc in documents]

        logger.info(f"Successfully inserted {len(result.inserted_ids)} transcriptions")

        return transcription_ids

    except PyMongoError as e:
        logger.error(f"Failed to insert transcriptions: {str(e)}")
        raise PyMongoError(f"Database error: {str(e)}")


# ============================================================================
# Query Operations
# ============================================================================

async def get_transcription_by_id(
    collection: Collection,
    transcription_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get a transcription by its ID

    Args:
        collection: MongoDB collection
        transcription_id: Transcription UUID

    Returns:
        Document dictionary if found, None otherwise
    """
    try:
        logger.info(f"Querying transcription: {transcription_id}")

        document = collection.find_one({"transcription_id": transcription_id})

        if document:
            logger.info(f"Found transcription: {transcription_id}")
            # Remove MongoDB _id from response
            document.pop("_id", None)
        else:
            logger.warning(f"Transcription not found: {transcription_id}")

        return document

    except PyMongoError as e:
        logger.error(f"Failed to query transcription: {str(e)}")
        return None


async def get_user_transcriptions(
    collection: Collection,
    user_id: str,
    limit: int = 50,
    skip: int = 0,
    sort_by: str = "created_at",
    sort_order: int = DESCENDING
) -> List[Dict[str, Any]]:
    """
    Get all transcriptions for a specific user

    Args:
        collection: MongoDB collection
        user_id: User ID
        limit: Maximum number of results
        skip: Number of documents to skip (for pagination)
        sort_by: Field to sort by
        sort_order: Sort order (ASCENDING or DESCENDING)

    Returns:
        List of transcription documents
    """
    try:
        logger.info(
            f"Querying transcriptions for user {user_id} "
            f"(limit: {limit}, skip: {skip})"
        )

        cursor = collection.find({"user_id": user_id}) \
            .sort(sort_by, sort_order) \
            .skip(skip) \
            .limit(limit)

        documents = list(cursor)

        # Remove MongoDB _id from all documents
        for doc in documents:
            doc.pop("_id", None)

        logger.info(f"Found {len(documents)} transcriptions for user {user_id}")

        return documents

    except PyMongoError as e:
        logger.error(f"Failed to query user transcriptions: {str(e)}")
        return []


async def search_transcriptions(
    collection: Collection,
    search_query: str,
    user_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Full-text search on transcriptions

    Args:
        collection: MongoDB collection
        search_query: Text to search for
        user_id: Optional user ID to filter results
        limit: Maximum number of results

    Returns:
        List of matching transcription documents
    """
    try:
        logger.info(f"Searching transcriptions: '{search_query}'")

        # Build query
        query: Dict[str, Any] = {
            "$text": {"$search": search_query}
        }

        if user_id:
            query["user_id"] = user_id

        # Execute search with text score
        cursor = collection.find(
            query,
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).limit(limit)

        documents = list(cursor)

        # Remove MongoDB _id
        for doc in documents:
            doc.pop("_id", None)

        logger.info(f"Found {len(documents)} matching transcriptions")

        return documents

    except PyMongoError as e:
        logger.error(f"Failed to search transcriptions: {str(e)}")
        return []


async def get_transcriptions_by_document_type(
    collection: Collection,
    document_type: str,
    user_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get transcriptions filtered by document type

    Args:
        collection: MongoDB collection
        document_type: Document type to filter by
        user_id: Optional user ID to filter results
        limit: Maximum number of results

    Returns:
        List of transcription documents
    """
    try:
        query: Dict[str, Any] = {
            "content.structured_content.document_type": document_type
        }

        if user_id:
            query["user_id"] = user_id

        cursor = collection.find(query) \
            .sort("created_at", DESCENDING) \
            .limit(limit)

        documents = list(cursor)

        for doc in documents:
            doc.pop("_id", None)

        logger.info(
            f"Found {len(documents)} transcriptions with type '{document_type}'"
        )

        return documents

    except PyMongoError as e:
        logger.error(f"Failed to query by document type: {str(e)}")
        return []


# ============================================================================
# Update Operations
# ============================================================================

async def update_transcription_status(
    collection: Collection,
    transcription_id: str,
    status: str,
    error_message: Optional[str] = None
) -> bool:
    """
    Update transcription processing status

    Args:
        collection: MongoDB collection
        transcription_id: Transcription UUID
        status: New status ('processing', 'processed', 'failed')
        error_message: Optional error message if status is 'failed'

    Returns:
        True if updated, False otherwise
    """
    try:
        logger.info(f"Updating status for {transcription_id}: {status}")

        update_doc = {
            "$set": {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
        }

        if error_message:
            update_doc["$set"]["error_message"] = error_message

        result = collection.update_one(
            {"transcription_id": transcription_id},
            update_doc
        )

        if result.matched_count > 0:
            logger.info(f"Successfully updated status for {transcription_id}")
            return True
        else:
            logger.warning(f"No document found with ID {transcription_id}")
            return False

    except PyMongoError as e:
        logger.error(f"Failed to update status: {str(e)}")
        return False


# ============================================================================
# Delete Operations
# ============================================================================

async def delete_transcription(
    collection: Collection,
    transcription_id: str
) -> bool:
    """
    Delete a transcription by ID

    Args:
        collection: MongoDB collection
        transcription_id: Transcription UUID

    Returns:
        True if deleted, False otherwise
    """
    try:
        logger.info(f"Deleting transcription: {transcription_id}")

        result = collection.delete_one({"transcription_id": transcription_id})

        if result.deleted_count > 0:
            logger.info(f"Successfully deleted transcription {transcription_id}")
            return True
        else:
            logger.warning(f"No document found with ID {transcription_id}")
            return False

    except PyMongoError as e:
        logger.error(f"Failed to delete transcription: {str(e)}")
        return False


async def delete_user_transcriptions(
    collection: Collection,
    user_id: str
) -> int:
    """
    Delete all transcriptions for a user

    Args:
        collection: MongoDB collection
        user_id: User ID

    Returns:
        Number of documents deleted
    """
    try:
        logger.info(f"Deleting all transcriptions for user {user_id}")

        result = collection.delete_many({"user_id": user_id})

        logger.info(
            f"Deleted {result.deleted_count} transcriptions for user {user_id}"
        )

        return result.deleted_count

    except PyMongoError as e:
        logger.error(f"Failed to delete user transcriptions: {str(e)}")
        return 0


# ============================================================================
# Statistics Operations
# ============================================================================

async def get_user_statistics(
    collection: Collection,
    user_id: str
) -> Dict[str, Any]:
    """
    Get statistics for a user's transcriptions

    Args:
        collection: MongoDB collection
        user_id: User ID

    Returns:
        Dictionary with statistics
    """
    try:
        logger.info(f"Getting statistics for user {user_id}")

        # Count total transcriptions
        total_count = collection.count_documents({"user_id": user_id})

        # Count by status
        status_counts = {}
        for status in ["processing", "processed", "failed"]:
            count = collection.count_documents({
                "user_id": user_id,
                "status": status
            })
            status_counts[status] = count

        # Get average confidence score
        pipeline = [
            {"$match": {"user_id": user_id}},
            {
                "$group": {
                    "_id": None,
                    "avg_confidence": {
                        "$avg": "$ocr_metadata.confidence_score"
                    },
                    "avg_word_count": {
                        "$avg": "$content.structured_content.word_count"
                    }
                }
            }
        ]

        aggregation_result = list(collection.aggregate(pipeline))

        stats = {
            "user_id": user_id,
            "total_transcriptions": total_count,
            "status_counts": status_counts,
            "avg_confidence_score": 0.0,
            "avg_word_count": 0
        }

        if aggregation_result:
            stats["avg_confidence_score"] = round(
                aggregation_result[0].get("avg_confidence", 0.0), 2
            )
            stats["avg_word_count"] = int(
                aggregation_result[0].get("avg_word_count", 0)
            )

        logger.info(f"Statistics for user {user_id}: {stats}")

        return stats

    except PyMongoError as e:
        logger.error(f"Failed to get user statistics: {str(e)}")
        return {
            "user_id": user_id,
            "total_transcriptions": 0,
            "status_counts": {},
            "error": str(e)
        }


# ============================================================================
# Example Usage
# ============================================================================

"""
# Example 1: Create indexes
from backend.database.mongodb import get_mongo_manager
from backend.database.operations import create_indexes

manager = get_mongo_manager()
collection = manager.collection
await create_indexes(collection)

# Example 2: Insert transcription
from backend.models.transcription import create_mongodb_document
import uuid

transcription_id = str(uuid.uuid4())
document = create_mongodb_document(transcription_id, request)
await insert_transcription(collection, document)

# Example 3: Query transcriptions
transcription = await get_transcription_by_id(collection, transcription_id)
user_transcriptions = await get_user_transcriptions(collection, "user123", limit=10)

# Example 4: Search transcriptions
results = await search_transcriptions(collection, "calculus derivatives", user_id="user123")

# Example 5: Update status
await update_transcription_status(collection, transcription_id, "processed")

# Example 6: Get statistics
stats = await get_user_statistics(collection, "user123")
print(f"Total transcriptions: {stats['total_transcriptions']}")
print(f"Average confidence: {stats['avg_confidence_score']}%")
"""
