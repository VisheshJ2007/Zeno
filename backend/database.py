from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

# Load variables from .env (MONGO_URI, DB_NAME)
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "zeno_db")

if not MONGO_URI:
    raise RuntimeError("MONGO_URI missing. Add it to backend/.env")

# Create a single, shared Mongo client + DB handle
client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client[DB_NAME]

