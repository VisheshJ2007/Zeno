# backend/database.py
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv, dotenv_values
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / ".env"

print(f"🔍 Looking for .env at: {env_path}")

if not env_path.exists():
    raise RuntimeError(f"❌ .env file not found at: {env_path}")

# 1) Try to load with normal UTF-8 (most cases)
load_dotenv(dotenv_path=env_path, override=True)

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

# 2) If still missing, try UTF-8 with BOM explicitly
if not MONGO_URI or not DB_NAME:
    load_dotenv(dotenv_path=env_path, override=True, encoding="utf-8-sig")
    MONGO_URI = MONGO_URI or os.getenv("MONGO_URI")
    DB_NAME   = DB_NAME   or os.getenv("DB_NAME")

# 3) If *still* missing, parse keys directly and inject
if not MONGO_URI or not DB_NAME:
    values = dotenv_values(dotenv_path=env_path, encoding="utf-8-sig")
    # Note: keys may have BOM if the file had it; dotenv_values handles that.
    if not MONGO_URI and "MONGO_URI" in values:
        os.environ["MONGO_URI"] = values["MONGO_URI"]
        MONGO_URI = values["MONGO_URI"]
    if not DB_NAME and "DB_NAME" in values:
        os.environ["DB_NAME"] = values["DB_NAME"]
        DB_NAME = values["DB_NAME"]

# Final guardrails + helpful debug
debug_sample = ""
try:
    debug_sample = env_path.read_text(encoding="utf-8-sig")[:120].replace("\n", "\\n")
except Exception:
    pass

if not MONGO_URI:
    raise RuntimeError(
        "❌ MONGO_URI missing after trying utf-8, utf-8-sig, and manual parse.\n"
        f"   Check the first lines of your .env:\n   {debug_sample}\n"
        "   Expected lines:\n"
        "   MONGO_URI=mongodb+srv://...\n"
        "   DB_NAME=zeno_db"
    )

if not DB_NAME:
    DB_NAME = "zeno_db"  # safe default

# ✅ Connect to MongoDB
client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client[DB_NAME]

print(f"✅ Connected to MongoDB database: {DB_NAME}")




