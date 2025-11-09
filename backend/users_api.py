# backend/users_api.py
from __future__ import annotations
from fastapi import FastAPI, HTTPException, status, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from passlib.context import CryptContext
from typing import Optional
from backend import database
from motor.motor_asyncio import AsyncIOMotorCollection
import asyncio

app = FastAPI(title="User API")

# Allow your frontend origin(s) — adjust in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],  # adjust if your frontend serves elsewhere
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserIn(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    email: Optional[EmailStr] = None
    enable_notifications: Optional[bool] = False


def get_users_collection() -> AsyncIOMotorCollection:
    # Collection name "users"
    return database.db["users"]


@app.on_event("startup")
async def startup_db():
    # Initialize DB (calls init_db which sets database.db)
    # If init_db is already called elsewhere this is harmless.
    database.init_db()
    col = get_users_collection()
    # Create unique index on username and email
    try:
        await col.create_index("username", unique=True)
        await col.create_index("email", unique=True, sparse=True)
    except Exception:
        # ignore index creation errors in dev, but log/raise in prod
        pass


@app.post("/api/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    username: str = Form(...),
    password: str = Form(...),
    email: Optional[str] = Form(None),
    notifications: Optional[str] = Form(None),  # checkbox -> "on" if checked
):
    """
    Accepts form-encoded POST (application/x-www-form-urlencoded) from your HTML form.
    Stores user with a bcrypt-hashed password.
    """
    # Basic validation (pydantic could be used too)
    if not username or not password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "username and password required")

    user = UserIn(
        username=username.strip(),
        password=password,
        email=(email.strip() if email else None),
        enable_notifications=(notifications == "on"),
    )

    hashed = pwd_context.hash(user.password)

    doc = {
        "username": user.username,
        "password_hash": hashed,
        "email": user.email,
        "enable_notifications": user.enable_notifications,
        "created_at": __import__("datetime").datetime.utcnow().isoformat(),
    }

    col = get_users_collection()

    try:
        res = await col.insert_one(doc)
    except Exception as e:
        # likely duplicate username or email
        # inspect e for duplicate key in production
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"could not create user: {str(e)}")

    return {"status": "ok", "user_id": str(res.inserted_id)}


@app.post("/api/login")
async def login_user(username: str = Form(...), password: str = Form(...)):
    col = get_users_collection()
    user_doc = await col.find_one({"username": username})
    if not user_doc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid username or password")

    if not pwd_context.verify(password, user_doc.get("password_hash", "")):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid username or password")

    # In real app generate JWT or session; here we return a small success payload
    return {"status": "ok", "username": username}
