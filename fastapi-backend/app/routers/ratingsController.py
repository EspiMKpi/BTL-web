"""
Ratings router — mirrors database/src/routes/ratings.ts.
GET / (public), GET /me, POST /, DELETE /
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from bson import ObjectId

from app.core.deps import get_current_user
from app.database import get_database
from app.models.schemas import RatingCreateRequest, RatingDeleteRequest, UserRatingOut

router = APIRouter(prefix="/api/ratings", tags=["ratings"])


@router.get("/")
async def get_ratings(
    tmdb_id: int = Query(...),
    content_type: str | None = None,
    reviews_only: bool = Query(False),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
):
    """Public: get ratings & reviews for a content item with aggregate stats."""
    db = get_database()
    query: dict = {"tmdb_id": tmdb_id}
    if content_type:
        query["content_type"] = content_type
    if reviews_only:
        query["review"] = {"$exists": True, "$ne": "", "$ne": None}

    # Aggregate stats (always full set, not paginated)
    stats_pipeline = [
        {"$match": {"tmdb_id": tmdb_id, **({"content_type": content_type} if content_type else {})}},
        {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}, "total_ratings": {"$sum": 1}}},
    ]
    agg = await db.tblUserRatings.aggregate(stats_pipeline).to_list(1)
    stats = (
        {"average": round(agg[0]["avg_rating"] * 10) / 10, "count": agg[0]["total_ratings"]}
        if agg and agg[0].get("avg_rating") is not None
        else {"average": 0, "count": 0}
    )

    # Rating distribution (1-10 buckets)
    dist_pipeline = [
        {"$match": {"tmdb_id": tmdb_id, **({"content_type": content_type} if content_type else {})}},
        {"$group": {"_id": {"$floor": "$rating"}, "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    dist_raw = await db.tblUserRatings.aggregate(dist_pipeline).to_list(10)
    distribution = {str(i): 0 for i in range(1, 11)}
    for d in dist_raw:
        bucket = int(d["_id"])
        if 1 <= bucket <= 10:
            distribution[str(bucket)] = d["count"]

    # Paginated ratings/reviews with user info
    skip = (page - 1) * limit
    cursor = db.tblUserRatings.find(query).sort("created_at", -1).skip(skip).limit(limit)
    ratings = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        # Enrich with username
        try:
            user = await db.tblUsers.find_one({"_id": ObjectId(doc["user_id"])})
            doc["username"] = user.get("username", "Anonymous") if user else "Anonymous"
            doc["avatar_url"] = user.get("avatar_url") if user else None
        except Exception:
            doc["username"] = "Anonymous"
            doc["avatar_url"] = None
        ratings.append(doc)

    return {"ratings": ratings, "stats": {**stats, "distribution": distribution}}


@router.get("/me", response_model=list[UserRatingOut])
async def get_my_ratings(
    content_type: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    db = get_database()
    query: dict = {"user_id": current_user["_id"]}
    if content_type:
        query["content_type"] = content_type

    cursor = db.tblUserRatings.find(query).sort("created_at", -1)
    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)
    return items


@router.post("/", response_model=UserRatingOut, status_code=status.HTTP_201_CREATED)
async def create_rating(
    body: RatingCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    if not body.content_type or not body.tmdb_id or body.rating is None:
        raise HTTPException(status_code=400, detail="content_type, tmdb_id, and rating are required")
    if body.rating < 0 or body.rating > 10:
        raise HTTPException(status_code=400, detail="Rating must be between 0 and 10")

    db = get_database()
    now = datetime.utcnow()
    result = await db.tblUserRatings.find_one_and_update(
        {"user_id": current_user["_id"], "content_type": body.content_type, "tmdb_id": body.tmdb_id},
        {
            "$set": {"rating": body.rating, "review": body.review, "updated_at": now},
            "$setOnInsert": {
                "user_id": current_user["_id"],
                "content_type": body.content_type,
                "tmdb_id": body.tmdb_id,
                "created_at": now,
            },
        },
        upsert=True,
        return_document=True,
    )

    result["_id"] = str(result["_id"])
    return result


@router.delete("/")
async def delete_rating(
    body: RatingDeleteRequest,
    current_user: dict = Depends(get_current_user),
):
    if not body.content_type or not body.tmdb_id:
        raise HTTPException(status_code=400, detail="content_type and tmdb_id are required")

    db = get_database()
    await db.tblUserRatings.find_one_and_delete(
        {"user_id": current_user["_id"], "content_type": body.content_type, "tmdb_id": body.tmdb_id}
    )
    return {"message": "Rating removed"}
