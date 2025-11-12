# backend/models/user.py
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    username: Optional[str] = Field(default=None, min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)

class UserLogin(BaseModel):
    # used if you later want a JSON body login – not required for OAuth2 form flow
    username_or_email: str
    password: str

class UserPublic(BaseModel):
    id: str
    email: EmailStr
    username: str
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

