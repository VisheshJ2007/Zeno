# backend/database.py
import os
from pathlib import Path
from dotenv import load_dotenv
import logging

from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger("zeno")

# --- Load .env from backend/.env
ENV_PATH = Path(_file_).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)
logger.info(f"🔍 Looking for .env at: {ENV_PATH}")

# --- Read config
MONGO_URI = os.getenv(
    "MONGO_URI",
    # Fallback empty; we will error on init if missing
    ""
)
DB_NAME = os.getenv("DB_NAME", "zeno_db")

# Optional: Azure OpenAI client (if you set it up in main.py you can ignore this)
azure_client = None  # main.py may populate this

# --- Create ONE global async client
_client: AsyncIOMotorClient | None = None
db = None

def _mask_uri(uri: str) -> str:
    # hide password for logs
    # mongodb+srv://user:pass@host/...
    try:
        if "://" in uri and "@" in uri:
            left, right = uri.split("://", 1)[1].split("@", 1)
            if ":" in left:
                user, _pass = left.split(":", 1)
                return f"mongodb+srv://{user}:*@{right}"
    except Exception:
        pass
    return "<hidden>"

async def init_db():
    global _client, db
    if not MONGO_URI:
        raise RuntimeError("MONGO_URI is not set in .env")

    # Use the EXACT URI you tested (with authSource=admin if that’s what worked)
    masked = _mask_uri(MONGO_URI)
    logger.info(f"Connecting to MongoDB with URI: {masked}")
    _client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    # quick ping to validate auth
    await _client.admin.command("ping")
    db = _client[DB_NAME]
    logger.info(f"✅ Initialized MongoDB connection to {DB_NAME}")

def close_db():
    global _client
    try:
        if _client:
            _client.close()
    finally:
        _client = None




