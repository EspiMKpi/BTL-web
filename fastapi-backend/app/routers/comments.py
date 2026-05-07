"""
Comments router — user comments on movies/series.
GET /:tmdb_id — public
POST / — authenticated
DELETE /:comment_id — owner or admin
"""

from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.deps import get_current_user
from app.database import get_database
from app.models.schemas import CommentCreateRequest, CommentOut

router = APIRouter(prefix="/api/comments", tags=["comments"])


@router.get("/{tmdb_id}")
async def get_comments(
    tmdb_id: int,
    content_type: str = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
):
    """Get comments for a content item."""
    db = get_database()
    query: dict = {"tmdb_id": tmdb_id}
    if content_type:
        query["content_type"] = content_type

    skip = (page - 1) * limit
    cursor = db.comments.find(query).sort("created_at", -1).skip(skip).limit(limit)
    comments = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        comments.append(doc)
    return comments


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_comment(
    body: CommentCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Add a comment to a content item."""
    db = get_database()
    comment_doc = {
        "user_id": current_user["_id"],
        "username": current_user.get("username", current_user.get("email", "User")),
        "content_type": body.content_type,
        "tmdb_id": body.tmdb_id,
        "text": body.text,
        "created_at": datetime.utcnow(),
    }
    result = await db.comments.insert_one(comment_doc)
    comment_doc["_id"] = str(result.inserted_id)
    return comment_doc


@router.delete("/{comment_id}")
async def delete_comment(
    comment_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete own comment (or admin can delete any)."""
    db = get_database()
    try:
        oid = ObjectId(comment_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid comment ID")

    comment = await db.comments.find_one({"_id": oid})
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    is_owner = comment.get("user_id") == current_user["_id"]
    is_admin = current_user.get("role") == "admin"
    if not is_owner and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")

    await db.comments.delete_one({"_id": oid})
    return {"message": "Comment deleted", "comment_id": comment_id}
