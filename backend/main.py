from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Zeno API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

class PlanIn(BaseModel):
    topic: str
    notes: str | None = None

@app.post("/plan")
def plan(inp: PlanIn):
    return {
        "goals": ["Understand key ideas", "Practice 3 problems", "Exit ticket"],
        "checkpoints": ["Warmup", "Core", "Challenge"]
    }
