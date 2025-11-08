from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from bson import ObjectId

# IMPORTANT: run server from repo root so this import works:
# python -m uvicorn backend.main:app --reload --port 8000
from backend.database import db


app = FastAPI(title="Zeno API")

# --- CORS (allow your static site / Live Server / local dev tools) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
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
        await db.command("ping")
        return {"mongo": "ok"}
    except Exception as e:
        # Bubble up message to help debug Atlas IP/creds issues
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
    payload = plan.model_dump()
    res = await db.plans.insert_one(payload)
    doc = await db.plans.find_one({"_id": res.inserted_id})
    return to_public(doc)

@app.get("/plans", response_model=List[dict])
async def list_plans(user: Optional[str] = None):
    query = {"user": user} if user else {}
    cursor = db.plans.find(query).sort([("_id", -1)]).limit(100)
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
