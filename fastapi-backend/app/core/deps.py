"""
FastAPI dependencies — replaces the Express auth_middleware / optional_auth.
Usage in routes:
    current_user = Depends(get_current_user)         # required auth
    current_user = Depends(get_optional_current_user) # optional auth
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from bson import ObjectId

from app.core.security import decode_access_token
from app.database import get_database

_bearer_scheme = HTTPBearer(auto_error=False)


async def _resolve_user(payload: dict) -> dict:
    """Look up the user document in MongoDB from a decoded JWT payload."""
    db = get_database()
    user = await db.users.find_one({"_id": ObjectId(payload["user_id"])})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    user["_id"] = str(user["_id"])
    return user


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> dict:
    """Required authentication — raises 401 if token is missing or invalid."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No token provided",
        )
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return await _resolve_user(payload)


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[dict]:
    """Optional authentication — returns None for unauthenticated requests."""
    if credentials is None:
        return None
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        return None
    try:
        return await _resolve_user(payload)
    except HTTPException:
        return None


async def get_admin_user(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Require admin role — raises 403 if user is not an admin."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
