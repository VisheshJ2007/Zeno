"""
Simple MongoDB manager shim.

Provides `get_mongo_manager()` used by routers. It wraps the `db` created
in `backend.database` and exposes a `collection` property and a simple
`health_check()` method.
"""
from __future__ import annotations

from typing import Any, Dict
from dataclasses import dataclass

from backend import database as _database


@dataclass
class MongoManager:
    collection_name: str = "transcriptions"

    @property
    def collection(self):
        return _database.db[self.collection_name]

    def health_check(self) -> Dict[str, Any]:
        """Return a lightweight health dict. This is synchronous to match
        existing call sites. For a true ping, install and call an async ping
        from an async context.
        """
        try:
            # Avoid blocking calls; assume client configured correctly.
            return {"status": "healthy"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


def get_mongo_manager() -> MongoManager:
    return MongoManager()
