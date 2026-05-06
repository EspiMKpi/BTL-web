"""
History router — mirrors database/src/routes/history.ts.
All routes require authentication.  Progress updates run as background tasks
so the client gets an immediate 200 OK.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from app.core.deps import get_current_user
from app.database import get_database
from app.models.schemas import ProgressUpdateRequest, WatchHistoryOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/continue-watching", response_model=list[WatchHistoryOut])
async def continue_watching(
    limit: int = Query(20, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    db = get_database()
    cursor = (
        db.watch_history.find(
            {"user_id": current_user["_id"], "completed": False, "progress_seconds": {"$gt": 0}}
        )
        .sort("last_watched_at", -1)
        .limit(limit)
    )
    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)
    return items


@router.get("/", response_model=list[WatchHistoryOut])
async def get_history(
    content_type: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    db = get_database()
    query: dict = {"user_id": current_user["_id"]}
    if content_type:
        query["content_type"] = content_type

    skip = (page - 1) * limit
    cursor = db.watch_history.find(query).sort("last_watched_at", -1).skip(skip).limit(limit)
    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)
    return items


@router.post("/progress", status_code=202)
async def update_progress(
    body: ProgressUpdateRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    if not body.content_type or not body.tmdb_id:
        raise HTTPException(status_code=400, detail="content_type and tmdb_id are required")

    background_tasks.add_task(
        _persist_progress,
        user_id=current_user["_id"],
        body=body,
    )
    return {"status": "accepted"}


async def _persist_progress(user_id: str, body: ProgressUpdateRequest) -> None:
    """Background task — upsert watch progress into MongoDB."""
    try:
        db = get_database()
        now = datetime.utcnow()
        await db.watch_history.find_one_and_update(
            {
                "user_id": user_id,
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
                    "user_id": user_id,
                    "content_type": body.content_type,
                    "tmdb_id": body.tmdb_id,
                    "season_number": body.season_number,
                    "episode_number": body.episode_number,
                    "created_at": now,
                },
            },
            upsert=True,
        )
    except Exception:
        logger.exception(
            "Failed to persist watch progress for user=%s tmdb_id=%s",
            user_id,
            body.tmdb_id,
        )
