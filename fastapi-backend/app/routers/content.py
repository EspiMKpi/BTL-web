"""
Content router — mirrors database/src/routes/content.ts.
GET /home, GET /genres, GET /browse/:genre_id, GET /movie/:id, GET /series/:id, GET /search
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import get_optional_current_user
from app.database import get_database
from app.services.library_service import get_content_by_genre, get_home_rails
from app.services.movie_service import get_movie_by_id
from app.services.series_service import get_series_by_id
from app.utils import sanitize


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
    cursor = db.genres.find({"is_hidden": {"$ne": True}}).sort("name", 1)
    genres = []
    async for doc in cursor:
        genres.append(sanitize(doc))
    return genres


@router.get("/browse/{genre_id}")
async def browse_genre(
    genre_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    db = get_database()
    genre = await db.genres.find_one({"genre_id": genre_id})
    if genre and genre.get("is_hidden"):
        raise HTTPException(status_code=404, detail="Genre not found")
    return await get_content_by_genre(genre_id, page, limit)


@router.get("/search")
async def search_content(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    skip = (page - 1) * limit
    db = get_database()
    escaped = q.replace(".", r"\.")

    # Search both movies and series
    movie_cursor = db.movies.find(
        {"title": {"$regex": escaped, "$options": "i"}, "is_hidden": {"$ne": True}},
        {"tmdb_id": 1, "title": 1, "poster_path": 1, "backdrop_path": 1, "vote_average": 1, "release_date": 1, "overview": 1},
    ).limit(limit + skip)
    series_cursor = db.series.find(
        {"name": {"$regex": escaped, "$options": "i"}, "is_hidden": {"$ne": True}},
        {"tmdb_id": 1, "name": 1, "poster_path": 1, "backdrop_path": 1, "vote_average": 1, "first_air_date": 1, "overview": 1},
    ).limit(limit + skip)

    movies = [dict(sanitize(d), content_type="movie") async for d in movie_cursor]
    series = [dict(sanitize(d), content_type="series") async for d in series_cursor]

    # Merge and paginate
    all_results = movies + series
    return {
        "results": all_results[skip : skip + limit],
        "page": page,
        "limit": limit,
        "total": len(all_results),
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
