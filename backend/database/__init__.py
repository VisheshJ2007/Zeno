"""
Package initializer for backend.database

This module loads environment variables from `backend/.env` but defers
creating the Motor client until `init_db()` is called from application
startup. This avoids blocking or side-effects during import which can
interfere with fast reloads and make the server appear unresponsive.
"""
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv, dotenv_values
from pathlib import Path
import os
from typing import Optional

# Determine the backend package root (one level up from this file)
PACKAGE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = PACKAGE_DIR.parent
env_path = BACKEND_DIR / ".env"

print(f"🔍 Looking for .env at: {env_path}")

if not env_path.exists():
    raise RuntimeError(f"❌ .env file not found at: {env_path}")

# Load env values (do not create the Motor client at import time)
load_dotenv(dotenv_path=env_path, override=True)

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

if not MONGO_URI or not DB_NAME:
    load_dotenv(dotenv_path=env_path, override=True, encoding="utf-8-sig")
    MONGO_URI = MONGO_URI or os.getenv("MONGO_URI")
    DB_NAME = DB_NAME or os.getenv("DB_NAME")

if not MONGO_URI or not DB_NAME:
    values = dotenv_values(dotenv_path=env_path, encoding="utf-8-sig")
    if not MONGO_URI and "MONGO_URI" in values:
        os.environ["MONGO_URI"] = values["MONGO_URI"]
        MONGO_URI = values["MONGO_URI"]
    if not DB_NAME and "DB_NAME" in values:
        os.environ["DB_NAME"] = values["DB_NAME"]
        DB_NAME = values["DB_NAME"]

if not DB_NAME:
    DB_NAME = "zeno_db"

# Expose client and db variables; initialize them in init_db().
client: Optional[AsyncIOMotorClient] = None
db = None


def init_db(connect_timeout_ms: int = 5000):
    """Initialize the global MongoDB client and database. Safe to call multiple times."""
    global client, db
    if client is not None:
        return
    if not MONGO_URI:
        raise RuntimeError("MONGO_URI is not configured in backend/.env")
    client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=connect_timeout_ms)
    db = client[DB_NAME]
    print(f"✅ Initialized MongoDB connection to {DB_NAME}")


def close_db():
    """Close the MongoDB client if initialized."""
    global client
    if client is not None:
        try:
            client.close()
        except Exception:
            pass
        client = None
