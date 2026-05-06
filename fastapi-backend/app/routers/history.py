"""
History router — mirrors database/src/routes/history.ts.
All routes require authentication.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import get_current_user
from app.database import get_database
from app.models.schemas import ProgressUpdateRequest, WatchHistoryOut

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/continue-watching", response_model=list[WatchHistoryOut])
async def continue_watching(current_user: dict = Depends(get_current_user)):
    db = get_database()
    cursor = (
        db.watch_history.find(
            {"user_id": current_user["_id"], "completed": False, "progress_seconds": {"$gt": 0}}
        )
        .sort("last_watched_at", -1)
        .limit(20)
    )
    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)
    return items


@router.get("/", response_model=list[WatchHistoryOut])
async def get_history(
    content_type: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    db = get_database()
    query: dict = {"user_id": current_user["_id"]}
    if content_type:
        query["content_type"] = content_type

    cursor = db.watch_history.find(query).sort("last_watched_at", -1).limit(50)
    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)
    return items


@router.post("/progress", response_model=WatchHistoryOut)
async def update_progress(
    body: ProgressUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    if not body.content_type or not body.tmdb_id:
        raise HTTPException(status_code=400, detail="content_type and tmdb_id are required")

    db = get_database()
    now = datetime.utcnow()
    result = await db.watch_history.find_one_and_update(
        {
            "user_id": current_user["_id"],
            "content_type": body.content_type,
            "tmdb_id": body.tmdb_id,
            "season_number": body.season_number,
            "episode_number": body.episode_number,
        },
        {
            "$set": {
                "progress_seconds": body.progress_seconds,
                "completed": body.completed,
                "last_watched_at": now,
            },
            "$setOnInsert": {
                "user_id": current_user["_id"],
                "content_type": body.content_type,
                "tmdb_id": body.tmdb_id,
                "season_number": body.season_number,
                "episode_number": body.episode_number,
                "created_at": now,
            },
        },
        upsert=True,
        return_document=True,
    )
    result["_id"] = str(result["_id"])
    return result
