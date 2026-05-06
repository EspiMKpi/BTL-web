"""
Content router — mirrors database/src/routes/content.ts.
GET /home, GET /genres, GET /browse/:genre_id, GET /movie/:id, GET /series/:id, GET /search
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import get_optional_current_user
from app.database import get_database
from app.services.library_service import get_content_by_genre, get_home_rails
from app.services.movie_service import get_movie_by_id, search_movies
from app.services.series_service import get_series_by_id

router = APIRouter(prefix="/api/content", tags=["content"])


@router.get("/home")
async def home(
    limit: int = Query(10, ge=1, le=50),
    current_user: Optional[dict] = Depends(get_optional_current_user),
):
    user_id = current_user["_id"] if current_user else None
    return await get_home_rails(user_id, rail_limit=limit)


@router.get("/genres")
async def list_genres():
    db = get_database()
    cursor = db.genres.find().sort("name", 1)
    genres = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        genres.append(doc)
    return genres


@router.get("/browse/{genre_id}")
async def browse_genre(
    genre_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    return await get_content_by_genre(genre_id, page, limit)


@router.get("/search")
async def search_content(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    skip = (page - 1) * limit
    results = await search_movies(q, limit=limit + skip)
    return {
        "results": results[skip : skip + limit],
        "page": page,
        "limit": limit,
        "total": len(results),
    }


@router.get("/movie/{movie_id}")
async def movie_detail(movie_id: int):
    try:
        return await get_movie_by_id(movie_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/series/{series_id}")
async def series_detail(series_id: int):
    try:
        return await get_series_by_id(series_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))
