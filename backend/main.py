from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
from typing import Optional, List
from bson import ObjectId

from database import db

# Import OCR router
from routers.ocr import router as ocr_router
from database.mongodb import get_mongo_manager, close_mongo_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Zeno API",
    description="AI-powered tutoring platform with OCR document processing",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        # Add your production frontend URL here
    ],
    allow_credentials=True,
# CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # add your prod URL later
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include OCR router
app.include_router(ocr_router)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    logger.info("Starting Zeno API...")
    try:
        # Initialize MongoDB connection
        mongo_manager = get_mongo_manager()
        health = mongo_manager.health_check()
        if health.get("status") == "healthy":
            logger.info("MongoDB connection established successfully")
        else:
            logger.warning(f"MongoDB connection issue: {health}")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup connections on shutdown"""
    logger.info("Shutting down Zeno API...")
    close_mongo_connection()
    logger.info("Connections closed")

# Health check endpoint
# ----------------- helpers -----------------
def to_public(doc: dict | None):
    """Convert Mongo document to response-safe dict (stringify _id)."""
    if not doc:
        return None
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    return doc

# ----------------- health / db ping -----------------
@app.get("/health")
def health():
    """Basic health check endpoint"""
    return {"ok": True, "service": "zeno-api"}

# Original planning endpoint (kept for backward compatibility)
@app.get("/db-ping")
async def db_ping():
    """Ping Atlas and surface any error text so it's easy to debug."""
    try:
        await db.command("ping")
        return {"mongo": "ok"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ----------------- models -----------------
class PlanIn(BaseModel):
    user: Optional[str] = None
    topic: str
    notes: Optional[str] = None

class PlanUpdate(BaseModel):
    topic: Optional[str] = None
    notes: Optional[str] = None

# ----------------- demo (kept from your file) -----------------
@app.post("/plan")
def plan(inp: PlanIn):
    """Generate study plan for a topic"""
def plan_demo(inp: PlanIn):
    return {
        "goals": ["Understand key ideas", "Practice 3 problems", "Exit ticket"],
        "checkpoints": ["Warmup", "Core", "Challenge"],
    }

# ----------------- MongoDB CRUD for plans -----------------
@app.post("/plans", response_model=dict)
async def create_plan(plan: PlanIn):
    payload = plan.model_dump()
    res = await db.plans.insert_one(payload)
    doc = await db.plans.find_one({"_id": res.inserted_id})
    return to_public(doc)

@app.get("/plans", response_model=List[dict])
async def list_plans(user: Optional[str] = None):
    q = {"user": user} if user else {}
    cursor = db.plans.find(q).sort([("_id", -1)]).limit(100)
    return [to_public(d) async for d in cursor]

@app.get("/plans/{plan_id}", response_model=dict)
async def get_plan(plan_id: str):
    try:
        doc = await db.plans.find_one({"_id": ObjectId(plan_id)})
    except Exception:
        raise HTTPException(400, "Invalid plan id")
    if not doc:
        raise HTTPException(404, "Plan not found")
    return to_public(doc)

@app.patch("/plans/{plan_id}", response_model=dict)
async def update_plan(plan_id: str, updates: PlanUpdate):
    data = {k: v for k, v in updates.model_dump().items() if v is not None}
    try:
        await db.plans.update_one({"_id": ObjectId(plan_id)}, {"$set": data})
        doc = await db.plans.find_one({"_id": ObjectId(plan_id)})
    except Exception:
        raise HTTPException(400, "Invalid plan id")
    if not doc:
        raise HTTPException(404, "Plan not found")
    return to_public(doc)

@app.delete("/plans/{plan_id}", response_model=dict)
async def delete_plan(plan_id: str):
    try:
        res = await db.plans.delete_one({"_id": ObjectId(plan_id)})
    except Exception:
        raise HTTPException(400, "Invalid plan id")
    return {"deleted": res.deleted_count == 1}
