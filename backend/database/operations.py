"""
Async MongoDB operations used by OCR router.

Provides minimal implementations of insert/search/update/delete used by the
application. These are intentionally simple to keep the repo self-contained.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Dict, Any


async def insert_transcription(collection, document: Dict[str, Any]) -> None:
    await collection.insert_one(document)


async def get_transcription_by_id(collection, transcription_id: str) -> Optional[Dict[str, Any]]:
    return await collection.find_one({"transcription_id": transcription_id})


async def get_user_transcriptions(collection, user_id: str, limit: int = 50, skip: int = 0, sort_by: str = "created_at") -> List[Dict[str, Any]]:
    cursor = collection.find({"user_id": user_id}).sort(sort_by, -1).skip(skip).limit(limit)
    return [doc async for doc in cursor]


async def search_transcriptions(collection, search_query: str, user_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    filter_q = {"searchable_text": {"$regex": search_query, "$options": "i"}}
    if user_id:
        filter_q["user_id"] = user_id
    cursor = collection.find(filter_q).limit(limit)
    return [doc async for doc in cursor]


async def get_user_statistics(collection, user_id: str) -> Dict[str, Any]:
    count = await collection.count_documents({"user_id": user_id})
    return {"user_id": user_id, "transcription_count": count}


async def update_transcription_status(collection, transcription_id: str, status_value: str, error_message: Optional[str] = None) -> bool:
    update = {"status": status_value, "updated_at": datetime.utcnow().isoformat()}
    if error_message is not None:
        update["error_message"] = error_message
    res = await collection.update_one({"transcription_id": transcription_id}, {"$set": update})
    return res.modified_count > 0


async def delete_transcription(collection, transcription_id: str) -> bool:
    res = await collection.delete_one({"transcription_id": transcription_id})
    return res.deleted_count > 0


async def create_indexes(collection) -> bool:
    try:
        await collection.create_index("transcription_id", unique=True)
        # Text index for searchable_text for simple search
        await collection.create_index([("searchable_text", "text")])
        return True
    except Exception:
        return False
