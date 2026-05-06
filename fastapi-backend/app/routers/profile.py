"""
Profile router — mirrors database/src/routes/profile.ts.
All routes require authentication.
"""

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_current_user
from app.database import get_database
from app.models.schemas import ProfileStatsOut, ProfileUpdateRequest, UserOut
from app.services.library_service import get_profile_stats, get_recent_activity

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/stats", response_model=ProfileStatsOut)
async def profile_stats(current_user: dict = Depends(get_current_user)):
    return await get_profile_stats(current_user["_id"])


@router.get("/recent-activity")
async def recent_activity(
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    return await get_recent_activity(current_user["_id"], limit)


@router.get("/")
async def get_profile(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["_id"],
        "email": current_user["email"],
        "username": current_user.get("username", ""),
        "avatar_url": current_user.get("avatar_url"),
        "role": current_user.get("role", "user"),
        "is_active": current_user.get("is_active", True),
        "created_at": current_user.get("created_at"),
    }


@router.patch("/")
async def update_profile(
    body: ProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    db = get_database()
    result = await db.users.find_one_and_update(
        {"_id": ObjectId(current_user["_id"])},
        {"$set": updates},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": str(result["_id"]),
        "email": result["email"],
        "username": result.get("username", ""),
        "avatar_url": result.get("avatar_url"),
        "role": result.get("role", "user"),
    }
