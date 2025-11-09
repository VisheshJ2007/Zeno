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

# -------------------------------------------------------------------
# Ensure repo root is importable (run server from repo root):
#   python -m uvicorn backend.main:app --reload --port 8000
# -------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import backend.database as database
from backend.routers.auth import router as auth_router
from backend.routers.ocr import router as ocr_router

# -------------------------------------------------------------------
# App + logging
# -------------------------------------------------------------------
app = FastAPI(title="Zeno API")

logger = logging.getLogger("zeno")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# -------------------------------------------------------------------
# CORS: allow local dev (file://, Live Server 5500, localhost/127.* on 3000/8000)
# -------------------------------------------------------------------
_allow_origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "null",  # <-- IMPORTANT for file:// pages
]
# Optional custom origin from env (e.g., FRONTEND_ORIGIN=http://127.0.0.1:5173)
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

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def to_public(doc: dict | None):
    """Convert Mongo _id to string id and remove private fields for API."""
    if not doc:
        return None
    doc = dict(doc)  # shallow copy to avoid mutating DB doc
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    return doc

# -------------------------------------------------------------------
# Health / Debug
# -------------------------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True}

@app.get("/debug/echo")
async def debug_echo():
    """Extremely fast endpoint to confirm server responsiveness."""
    logger.info("/debug/echo called")
    return {"ok": True, "echo": "server alive"}

@app.get("/db-ping")
async def db_ping():
    try:
        await database.db.command("ping")
        return {"mongo": "ok"}
    except Exception as e:
        logger.exception("Mongo ping failed: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})

# -------------------------------------------------------------------
# Models
# -------------------------------------------------------------------
class PlanIn(BaseModel):
    user: Optional[str] = None
    topic: str
    notes: Optional[str] = None

class PlanUpdate(BaseModel):
    topic: Optional[str] = None
    notes: Optional[str] = None

# -------------------------------------------------------------------
# Plans CRUD
# -------------------------------------------------------------------
@app.post("/plans", response_model=dict)
async def create_plan(plan: PlanIn):
    payload = plan.model_dump()
    logger.info("POST /plans payload=%s", payload)
    res = await database.db.plans.insert_one(payload)
    doc = await database.db.plans.find_one({"_id": res.inserted_id})
    logger.info("Plan created: %s", res.inserted_id)
    return to_public(doc)

@app.get("/plans", response_model=List[dict])
async def list_plans(user: Optional[str] = None):
    logger.info("GET /plans user=%s", user)
    query = {"user": user} if user else {}
    cursor = database.db.plans.find(query).sort([("_id", -1)]).limit(100)
    out = [to_public(d) async for d in cursor]
    logger.info("Returning %d plans", len(out))
    return out

@app.get("/plans/{plan_id}", response_model=dict)
async def get_plan(plan_id: str):
    logger.info("GET /plans/%s", plan_id)
    try:
        doc = await database.db.plans.find_one({"_id": ObjectId(plan_id)})
    except Exception:
        raise HTTPException(400, "Invalid plan id")
    if not doc:
        raise HTTPException(404, "Plan not found")
    return to_public(doc)

@app.patch("/plans/{plan_id}", response_model=dict)
async def update_plan(plan_id: str, updates: PlanUpdate):
    data = {k: v for k, v in updates.model_dump().items() if v is not None}
    logger.info("PATCH /plans/%s data=%s", plan_id, data)
    try:
        await database.db.plans.update_one({"_id": ObjectId(plan_id)}, {"$set": data})
        doc = await database.db.plans.find_one({"_id": ObjectId(plan_id)})
    except Exception:
        raise HTTPException(400, "Invalid plan id")
    if not doc:
        raise HTTPException(404, "Plan not found")
    return to_public(doc)

@app.delete("/plans/{plan_id}", response_model=dict)
async def delete_plan(plan_id: str):
    logger.info("DELETE /plans/%s", plan_id)
    try:
        res = await database.db.plans.delete_one({"_id": ObjectId(plan_id)})
    except Exception:
        raise HTTPException(400, "Invalid plan id")
    return {"deleted": res.deleted_count == 1}

# -------------------------------------------------------------------
# Startup / Shutdown
# -------------------------------------------------------------------
@app.on_event("startup")
async def startup_indexes():
    # Initialize DB connection first
    try:
        database.init_db()
        logger.info("DB init complete")
    except Exception as e:
        logger.exception("Failed to initialize DB: %s", e)
        raise

    # Ensure unique indexes for users collection (auth)
    try:
        await database.db.users.create_index("email", unique=True)
        await database.db.users.create_index("username", unique=True)
        logger.info("Indexes ensured for users collection")
    except Exception as e:
        logger.exception("Failed creating user indexes: %s", e)
        # Not fatal for server start; comment the next line if you want strict start-up
        # raise

@app.on_event("shutdown")
async def shutdown_db():
    try:
        database.close_db()
        logger.info("DB closed")
    except Exception as e:
        logger.exception("Error closing DB: %s", e)

# -------------------------------------------------------------------
# Routers
# -------------------------------------------------------------------
app.include_router(auth_router)
app.include_router(ocr_router)