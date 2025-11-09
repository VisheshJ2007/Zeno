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

# ----- import order matters a bit for clean startup -----
# Ensure project root is importable when launched as a module
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Local modules
import backend.database as database
from backend.routers.auth import router as auth_router
from backend.routers.ocr import router as ocr_router

# Azure OpenAI helper
from backend.azure_client import init_azure_client, get_client

# ----------------------------------------------------------------------

app = FastAPI(title="Zeno API")

logger = logging.getLogger("zeno")
logging.basicConfig(level=logging.INFO)

# --- CORS: allow local dev (Live Server / localhost) ---
_allow_origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
_frontend_origin = os.getenv("FRONTEND_ORIGIN")
if _frontend_origin and _frontend_origin not in _allow_origins:
    _allow_origins.append(_frontend_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- small helpers ----------
def to_public(doc: dict | None):
    """Convert Mongo _id to string id and remove private fields."""
    if not doc:
        return None
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    return doc


# ---------- health + ping ----------
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


# ---------- models ----------
class PlanIn(BaseModel):
    user: Optional[str] = None
    topic: str
    notes: Optional[str] = None

class PlanUpdate(BaseModel):
    topic: Optional[str] = None
    notes: Optional[str] = None


# ---------- CRUD: plans ----------
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


# ---------- simple echo (no DB touch) ----------
@app.get("/debug/echo")
async def debug_echo():
    logger.info("/debug/echo called")
    return {"ok": True, "echo": "server alive"}


# ---------- optional: Azure sanity check ----------
@app.get("/azure-test")
async def azure_test():
    client = get_client()
    if not client:
        return {"error": "Azure client not initialized (check .env values)"}
    try:
        resp = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
            messages=[{"role": "user", "content": "Say hello from Azure!"}],
        )
        return {"reply": resp.choices[0].message.content}
    except Exception as e:
        return {"error": str(e)}


# ---------- lifecycle ----------
@app.on_event("startup")
async def startup_indexes():
    # 1) Azure first (so any routes depending on it are ready)
    init_azure_client()

    # 2) DB connection + indexes
    try:
        database.init_db()
    except Exception as e:
        logger.exception("Failed to initialize DB: %s", e)
        raise

    await database.db.users.create_index("email", unique=True)
    await database.db.users.create_index("username", unique=True)
    logger.info("Indexes ensured for users collection")


@app.on_event("shutdown")
async def shutdown_db():
    try:
        database.close_db()
    except Exception:
        logger.exception("Error closing DB")


# ---------- include routers ----------
app.include_router(auth_router)
app.include_router(ocr_router)