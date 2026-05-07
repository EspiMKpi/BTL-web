"""
Admin router — management panel for admins only.
All routes require admin role.
"""

from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.deps import get_admin_user
from app.database import get_database
from app.models.schemas import (
    AdminMovieOut,
    AdminUserOut,
    BanUserRequest,
    CommentOut,
    HideMovieRequest,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ─── User management ─────────────────────────────────────────────────────

@router.get("/users", response_model=list[AdminUserOut])
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    admin: dict = Depends(get_admin_user),
):
    """List all users (paginated)."""
    db = get_database()
    skip = (page - 1) * limit
    cursor = db.users.find().sort("created_at", -1).skip(skip).limit(limit)
    users = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        users.append(doc)
    return users


@router.patch("/users/{user_id}/ban")
async def ban_user(
    user_id: str,
    body: BanUserRequest,
    admin: dict = Depends(get_admin_user),
):
    """Ban or unban a user. Banned users cannot log in."""
    db = get_database()
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    result = await db.users.find_one_and_update(
        {"_id": oid},
        {"$set": {"is_banned": body.is_banned, "updated_at": datetime.utcnow()}},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    action = "banned" if body.is_banned else "unbanned"
    return {"message": f"User {action}", "user_id": user_id, "is_banned": body.is_banned}


# ─── Movie visibility ────────────────────────────────────────────────────

@router.get("/movies")
async def list_movies(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    admin: dict = Depends(get_admin_user),
):
    """List all movies with visibility status (paginated)."""
    db = get_database()
    skip = (page - 1) * limit
    cursor = db.movies.find(
        {},
        {"tmdb_id": 1, "title": 1, "poster_path": 1, "is_hidden": 1, "vote_average": 1},
    ).sort("title", 1).skip(skip).limit(limit)
    movies = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doc.setdefault("is_hidden", False)
        movies.append(doc)
    return movies


@router.patch("/movies/{tmdb_id}/visibility")
async def toggle_movie_visibility(
    tmdb_id: int,
    body: HideMovieRequest,
    admin: dict = Depends(get_admin_user),
):
    """Show or hide a movie from regular users."""
    db = get_database()
    result = await db.movies.find_one_and_update(
        {"tmdb_id": tmdb_id},
        {"$set": {"is_hidden": body.is_hidden, "updated_at": datetime.utcnow()}},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Movie not found")

    action = "hidden" if body.is_hidden else "visible"
    return {"message": f"Movie is now {action}", "tmdb_id": tmdb_id, "is_hidden": body.is_hidden}


# ─── Comment moderation ──────────────────────────────────────────────────

@router.get("/comments")
async def list_all_comments(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    admin: dict = Depends(get_admin_user),
):
    """List all comments across all content (paginated)."""
    db = get_database()
    skip = (page - 1) * limit
    cursor = db.comments.find().sort("created_at", -1).skip(skip).limit(limit)
    comments = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        comments.append(doc)
    return comments


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: str,
    admin: dict = Depends(get_admin_user),
):
    """Delete a comment by admin."""
    db = get_database()
    try:
        oid = ObjectId(comment_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid comment ID")

    result = await db.comments.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Comment not found")

    return {"message": "Comment deleted", "comment_id": comment_id}
