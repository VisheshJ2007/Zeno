# backend/main.py
import os
import sys
import logging
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from bson import ObjectId

# ──────────────────────────────────────────────────────────────────────────────
# Make the project importable when Vercel imports api/index.py
# (api/index.py will do: from backend.main import app)
# ──────────────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(_file_))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Local modules (after sys.path tweak)
import backend.database as database
from backend.routers.auth import router as auth_router
from backend.routers.ocr import router as ocr_router
from backend.routers.azure_chat import router as azure_chat_router
from backend.azure_client import init_azure_client, get_client

# ──────────────────────────────────────────────────────────────────────────────
# App / Logging
# ──────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger("zeno")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Zeno API", version="1.0.0")

# ──────────────────────────────────────────────────────────────────────────────
# CORS (allow local and Vercel)
# ──────────────────────────────────────────────────────────────────────────────
def _cors_origins() -> list[str]:
    origins = [
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ]
    # FRONTEND_ORIGIN (if you keep a separate site)
    fe = os.getenv("FRONTEND_ORIGIN")
    if fe:
        origins.append(fe)

    # If running on Vercel, VERCEL_URL is like "your-app.vercel.app"
    vercel_url = os.getenv("VERCEL_URL")
    if vercel_url:
        origins.append(f"https://{vercel_url}")

    # Also allow the project’s production domain (helpful when calling API from same site)
    # e.g. https://zeno-steel.vercel.app
    public_url = os.getenv("PUBLIC_ORIGIN")
    if public_url:
        origins.append(public_url)

    # De-dup
    return sorted(set(origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def to_public(doc: dict | None):
    """Convert Mongo _id to string id and remove private fields."""
    if not doc:
        return None
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    return doc

# ──────────────────────────────────────────────────────────────────────────────
# Health & Root
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "ok": True,
        "service": "Zeno API",
        "hint": "API is alive. Try /health, /db-ping or /docs",
    }

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/db-ping")
async def db_ping():
    try:
        await database.db.command("ping")
        return {"mongo": "ok"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ──────────────────────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────────────────────
class PlanIn(BaseModel):
    user: Optional[str] = None
    topic: str
    notes: Optional[str] = None

class PlanUpdate(BaseModel):
    topic: Optional[str] = None
    notes: Optional[str] = None

# ──────────────────────────────────────────────────────────────────────────────
# Plans CRUD
# ──────────────────────────────────────────────────────────────────────────────
@app.post("/plans", response_model=dict)
async def create_plan(plan: PlanIn):
    logger.info("Received create_plan request: %s", plan.model_dump())
    payload = plan.model_dump()
    res = await database.db.plans.insert_one(payload)
    doc = await database.db.plans.find_one({"_id": res.inserted_id})
    logger.info("Plan created id=%s", getattr(res, "inserted_id", None))
    return to_public(doc)

@app.get("/plans", response_model=List[dict])
async def list_plans(user: Optional[str] = None):
    logger.info("Listing plans for user=%s", user)
    query = {"user": user} if user else {}
    cursor = database.db.plans.find(query).sort([("_id", -1)]).limit(100)
    results = [to_public(d) async for d in cursor]
    logger.info("Returning %d plans", len(results))
    return results

@app.get("/plans/{plan_id}", response_model=dict)
async def get_plan(plan_id: str):
    try:
        logger.info("Fetching plan id=%s", plan_id)
        doc = await database.db.plans.find_one({"_id": ObjectId(plan_id)})
    except Exception:
        raise HTTPException(400, "Invalid plan id")
    if not doc:
        raise HTTPException(404, "Plan not found")
    return to_public(doc)

@app.patch("/plans/{plan_id}", response_model=dict)
async def update_plan(plan_id: str, updates: PlanUpdate):
    data = {k: v for k, v in updates.model_dump().items() if v is not None}
    try:
        logger.info("Updating plan id=%s data=%s", plan_id, data)
        await database.db.plans.update_one({"_id": ObjectId(plan_id)}, {"$set": data})
        doc = await database.db.plans.find_one({"_id": ObjectId(plan_id)})
    except Exception:
        raise HTTPException(400, "Invalid plan id")
    if not doc:
        raise HTTPException(404, "Plan not found")
    return to_public(doc)

@app.delete("/plans/{plan_id}", response_model=dict)
async def delete_plan(plan_id: str):
    try:
        logger.info("Deleting plan id=%s", plan_id)
        res = await database.db.plans.delete_one({"_id": ObjectId(plan_id)})
    except Exception:
        raise HTTPException(400, "Invalid plan id")
    return {"deleted": res.deleted_count == 1}

# ──────────────────────────────────────────────────────────────────────────────
# Debug / Azure test
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/debug/echo")
async def debug_echo():
    logger.info("/debug/echo called")
    return {"ok": True, "echo": "server alive"}

@app.get("/azure-test")
async def azure_test():
    client = get_client()
    if not client:
        return {"error": "Azure client not initialized (check env vars)"}
    try:
        resp = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
            messages=[{"role": "user", "content": "Say hello from Azure!"}],
        )
        return {"reply": resp.choices[0].message.content}
    except Exception as e:
        return {"error": str(e)}

# ──────────────────────────────────────────────────────────────────────────────
# Startup / Shutdown (idempotent for serverless)
# ──────────────────────────────────────────────────────────────────────────────
_START_DONE = False

@app.on_event("startup")
async def startup():
    global _START_DONE
    if _START_DONE:
        return

    # 1) Azure
    init_azure_client()

    # 2) DB
    try:
        database.init_db()
    except Exception as e:
        logger.exception("Failed to initialize DB: %s", e)
        raise

    # 3) Indexes (safe if already exist)
    try:
        await database.db.users.create_index("email", unique=True)
        await database.db.users.create_index("username", unique=True)
        logger.info("Indexes ensured for users collection")
    except Exception:
        logger.exception("Index ensure failed (continuing)")

    _START_DONE = True

@app.on_event("shutdown")
async def shutdown():
    try:
        database.close_db()
    except Exception:
        logger.exception("Error closing DB")

# ──────────────────────────────────────────────────────────────────────────────
# Routers
# ──────────────────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(ocr_router)
app.include_router(azure_chat_router)