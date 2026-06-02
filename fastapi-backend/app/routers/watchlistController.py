"""
Watchlist router — mirrors database/src/routes/watchlist.ts.
All routes require authentication.
"""

from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import get_current_user
from app.database import get_database
from app.models.schemas import WatchlistAddRequest, WatchlistItemOut, WatchlistUpdateRequest

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("/", response_model=list[WatchlistItemOut])
async def get_watchlist(
    status_filter: str | None = None,
    content_type: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    db = get_database()
    query: dict = {"user_id": current_user["_id"]}
    if status_filter:
        query["status"] = status_filter
    if content_type:
        query["content_type"] = content_type

    cursor = db.tblWatchlistItems.find(query).sort("updated_at", -1)
    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)
    return items


@router.post("/", response_model=WatchlistItemOut, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    body: WatchlistAddRequest,
    current_user: dict = Depends(get_current_user),
):
    if not body.content_type or not body.tmdb_id:
        raise HTTPException(status_code=400, detail="content_type and tmdb_id are required")

    db = get_database()
    now = datetime.utcnow()

    # Normalize content_type: reject 'mixed' and other invalid values
    valid_types = {"movie", "series"}
    content_type = body.content_type if body.content_type in valid_types else "movie"

    # Upsert by (user_id, tmdb_id) only — prevents duplicate entries for the
    # same title even if content_type differs (e.g. 'series' vs 'mixed').
    result = await db.tblWatchlistItems.find_one_and_update(
        {"user_id": current_user["_id"], "tmdb_id": body.tmdb_id},
        {
            "$setOnInsert": {
                "user_id": current_user["_id"],
                "tmdb_id": body.tmdb_id,
                "created_at": now,
            },
            "$set": {
                "content_type": content_type,
                "status": body.status,
                "is_bookmarked": body.is_bookmarked,
                "is_favorite": body.is_favorite,
                "updated_at": now,
            },
        },
        upsert=True,
        return_document=True,
    )
    result["_id"] = str(result["_id"])
    return result


@router.patch("/{item_id}", response_model=WatchlistItemOut)
async def update_watchlist_item(
    item_id: str,
    body: WatchlistUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    db = get_database()
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = datetime.utcnow()

    try:
        result = await db.tblWatchlistItems.find_one_and_update(
            {"_id": ObjectId(item_id), "user_id": current_user["_id"]},
            {"$set": updates},
            return_document=True,
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    if not result:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    result["_id"] = str(result["_id"])
    return result


@router.delete("/{item_id}")
async def remove_from_watchlist(
    item_id: str,
    current_user: dict = Depends(get_current_user),
):
    db = get_database()
    try:
        result = await db.tblWatchlistItems.find_one_and_delete(
            {"_id": ObjectId(item_id), "user_id": current_user["_id"]}
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    if not result:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    return {"message": "Removed from watchlist"}
