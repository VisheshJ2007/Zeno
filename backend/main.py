from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging

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
@app.get("/health")
def health():
    """Basic health check endpoint"""
    return {"ok": True, "service": "zeno-api"}

# Original planning endpoint (kept for backward compatibility)
class PlanIn(BaseModel):
    topic: str
    notes: str | None = None

@app.post("/plan")
def plan(inp: PlanIn):
    """Generate study plan for a topic"""
    return {
        "goals": ["Understand key ideas", "Practice 3 problems", "Exit ticket"],
        "checkpoints": ["Warmup", "Core", "Challenge"]
    }
