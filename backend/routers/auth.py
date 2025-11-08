# backend/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse, JSONResponse
from bson import ObjectId
from datetime import datetime, timezone
from typing import Optional
import os
import re
import secrets
import urllib.parse
import httpx

from backend.database import db
from backend.models.user import UserCreate, UserLogin, UserPublic, Token
from backend.utils.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# OAuth2 scheme (form-encoded login at /auth/login)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ---------- helpers ----------
def _normalize_username(u: str) -> str:
    return u.strip().lower()

def _normalize_email(e: str) -> str:
    return e.strip().lower()

async def _user_to_public(u) -> UserPublic:
    return UserPublic(
        id=str(u["_id"]),
        email=u["email"],
        username=u["username"],
        created_at=u["created_at"],
    )

async def get_current_user(token: str = Depends(oauth2_scheme)):
    subject = decode_token(token)
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = await db.users.find_one({"_id": ObjectId(subject)})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

# ---------- local auth routes ----------
@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate):
    email = _normalize_email(payload.email)
    username = _normalize_username(payload.username)

    # unique checks
    exists = await db.users.find_one({"$or": [{"email": email}, {"username": username}]})
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or username already in use")

    doc = {
        "email": email,
        "username": username,
        "password_hash": hash_password(payload.password),
        "created_at": datetime.now(timezone.utc),
        "provider": "local",
    }
    res = await db.users.insert_one(doc)
    created = await db.users.find_one({"_id": res.inserted_id})
    return await _user_to_public(created)

# OAuth2PasswordRequestForm expects form data: username, password
@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    identifier = form_data.username.strip()
    password = form_data.password

    query = {}
    if re.match(r".+@.+\..+", identifier):
        query["email"] = _normalize_email(identifier)
    else:
        query["username"] = _normalize_username(identifier)

    user = await db.users.find_one(query)
    if not user:
        # Make it explicit so frontend can suggest registration
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect credentials")

    token = create_access_token(subject=str(user["_id"]))
    return Token(access_token=token)

# Optional JSON-style login if your frontend prefers JSON
@router.post("/login-json", response_model=Token)
async def login_json(payload: UserLogin):
    identifier = payload.username_or_email.strip()
    password = payload.password

    query = {}
    if re.match(r".+@.+\..+", identifier):
        query["email"] = _normalize_email(identifier)
    else:
        query["username"] = _normalize_username(identifier)

    user = await db.users.find_one(query)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect credentials")

    token = create_access_token(subject=str(user["_id"]))
    return Token(access_token=token)

@router.get("/me", response_model=UserPublic)
async def me(current=Depends(get_current_user)):
    return await _user_to_public(current)

# ---------- forgot/reset placeholders (implement later) ----------
@router.post("/forgot-password")
async def forgot_password(username_or_email: str):
    return {"ok": True, "msg": "Reset link would be emailed in step 2."}

@router.post("/reset-password")
async def reset_password(token: str, new_password: str):
    return {"ok": True, "msg": "Password would be reset in step 2."}

