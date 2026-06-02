"""
Auth router — mirrors database/src/routes/auth.ts.
POST /register, POST /login, GET /me
"""

from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_database
from app.models.schemas import AuthResponse, LoginRequest, RegisterRequest, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Per-endpoint rate limiter (in-memory, per-worker)
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest):
    if not body.email or not body.password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    db = get_database()
    existing = await db.tblUsers.find_one({"email": body.email.lower()})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    username = body.email.split("@")[0]
    user_doc = {
        "email": body.email,
        "password": hash_password(body.password),
        "username": username,
        "avatar_url": None,
        "role": "user",
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    result = await db.tblUsers.insert_one(user_doc)
    user_id = str(result.inserted_id)

    token = create_access_token(user_id, body.email)
    return {
        "token": token,
        "user": {"_id": user_id, "email": body.email, "username": username, "role": "user"},
    }


@router.post("/login", response_model=AuthResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest):
    if not body.email or not body.password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    db = get_database()
    user = await db.tblUsers.find_one({"email": body.email.lower()})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    stored_password = user.get("password", "")
    if not verify_password(body.password, stored_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.get("is_banned", False):
        raise HTTPException(status_code=403, detail="Your account has been banned")

    user_id = str(user["_id"])
    token = create_access_token(user_id, user["email"])
    return {
        "token": token,
        "user": {
            "_id": user_id,
            "email": user["email"],
            "username": user.get("username", ""),
            "role": user.get("role", "user"),
        },
    }


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["_id"],
        "email": current_user["email"],
        "username": current_user.get("username", ""),
        "role": current_user.get("role", "user"),
        "is_active": current_user.get("is_active", True),
        "is_banned": current_user.get("is_banned", False),
    }
