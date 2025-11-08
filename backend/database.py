# backend/database.py
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv, find_dotenv
from pathlib import Path
import os

# load .env from common places
dotenv_path = find_dotenv(".env", raise_error_if_not_found=False)
if dotenv_path:
    load_dotenv(dotenv_path, override=True)
else:
    # also try backend/.env explicitly
    p = Path(__file__).resolve().parent / ".env"
    if p.exists():
        load_dotenv(p, override=True)

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "zeno_db")

if not MONGO_URI:
    raise RuntimeError("MONGO_URI missing. Add it to backend/.env")

client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client[DB_NAME]

