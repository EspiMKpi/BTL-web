"""
Content router — mirrors database/src/routes/content.ts.
GET /home, GET /genres, GET /browse/:genre_id, GET /movie/:id, GET /series/:id, GET /search
"""

from typing import Optional

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.deps import get_optional_current_user
from app.database import get_database
from app.services.libraryService import (
    get_content_by_genre,
    get_hidden_genre_ids,
    get_home_rails,
    get_movie_rails,
    get_series_rails,
    public_content_filter,
)
from app.services.movieService import get_movie_by_id
from app.services.seriesService import get_series_by_id
from app.utils import escape_mongo_regex, is_movie_doc, is_series_doc, sanitize


router = APIRouter(prefix="/api/content", tags=["content"])


@router.get("/home")
async def home(
    limit: int = Query(10, ge=1, le=50),
    current_user: Optional[dict] = Depends(get_optional_current_user),
):
    user_id = current_user["_id"] if current_user else None
    return await get_home_rails(user_id, rail_limit=limit)


@router.get("/series/rails")
async def series_rails(
    limit: int = Query(12, ge=1, le=50),
    current_user: Optional[dict] = Depends(get_optional_current_user),
):
    """Series-specific curated rails (Currently Airing, Completed Gems, etc.)."""
    user_id = current_user["_id"] if current_user else None
    return await get_series_rails(rail_limit=limit, user_id=user_id)


@router.get("/movies/rails")
async def movie_rails(
    limit: int = Query(12, ge=1, le=50),
    current_user: Optional[dict] = Depends(get_optional_current_user),
):
    """Movie-specific curated rails (Trending, Top Rated, Classics, etc.)."""
    user_id = current_user["_id"] if current_user else None
    return await get_movie_rails(rail_limit=limit, user_id=user_id)


@router.get("/genres")
async def list_genres():
    db = get_database()
    cursor = db.tblGenres.find({"is_hidden": {"$ne": True}}).sort("name", 1)
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
    genre = await db.tblGenres.find_one({"genre_id": genre_id})
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
    escaped = escape_mongo_regex(q)
    public_filter = await public_content_filter()

    # Search both movies and series
    movie_cursor = db.tblMovies.find(
        {"title": {"$regex": escaped, "$options": "i"}, **public_filter},
        {"tmdb_id": 1, "title": 1, "name": 1, "poster_path": 1, "backdrop_path": 1, "vote_average": 1, "release_date": 1, "first_air_date": 1, "overview": 1, "seasons": 1, "number_of_seasons": 1},
    ).skip(skip).limit(limit)
    series_cursor = db.tblSeries.find(
        {"name": {"$regex": escaped, "$options": "i"}, **public_filter},
        {"tmdb_id": 1, "name": 1, "title": 1, "poster_path": 1, "backdrop_path": 1, "vote_average": 1, "first_air_date": 1, "release_date": 1, "overview": 1},
    ).skip(skip).limit(limit)

    movies = []
    async for d in movie_cursor:
        d = sanitize(d)
        d["content_type"] = "series" if not is_movie_doc(d) else "movie"
        movies.append(d)

    series = []
    async for d in series_cursor:
        d = sanitize(d)
        d["content_type"] = "movie" if not is_series_doc(d) else "series"
        series.append(d)

    # Merge and deduplicate by tmdb_id (prefer correct collection)
    seen: dict[int, str] = {}
    all_results = []
    for item in movies + series:
        tid = item.get("tmdb_id")
        key = f"{tid}_{item['content_type']}"
        if key not in seen:
            seen[key] = True
            all_results.append(item)

    return {
        "results": all_results[:limit],
        "page": page,
        "limit": limit,
        "total": len(all_results),
    }


class BatchItem(BaseModel):
    content_type: str
    tmdb_id: int


class BatchRequest(BaseModel):
    items: list[BatchItem]


@router.post("/batch")
async def content_batch(body: BatchRequest):
    """Resolve metadata for many titles in one round-trip.

    Used by the watchlist / continue-watching views, which previously fired
    one detail request per item (an N+1 storm). MongoDB-only — never hits TMDB.
    """
    if not body.items:
        return []

    ids = list({i.tmdb_id for i in body.items})
    db = get_database()
    projection = {
        "tmdb_id": 1,
        "title": 1,
        "name": 1,
        "poster_path": 1,
        "backdrop_path": 1,
        "vote_average": 1,
        "runtime": 1,
    }

    movies: dict[int, dict] = {}
    async for doc in db.tblMovies.find({"tmdb_id": {"$in": ids}}, projection):
        movies[doc["tmdb_id"]] = sanitize(doc)
    series: dict[int, dict] = {}
    async for doc in db.tblSeries.find({"tmdb_id": {"$in": ids}}, projection):
        series[doc["tmdb_id"]] = sanitize(doc)

    results = []
    for item in body.items:
        tid = item.tmdb_id
        # Prefer the requested collection, fall back to the other —
        # stored content_type in watch_history / watchlist can be stale.
        if item.content_type == "series":
            doc = series.get(tid) or movies.get(tid)
            resolved_type = "series" if tid in series else "movie"
        else:
            doc = movies.get(tid) or series.get(tid)
            resolved_type = "movie" if tid in movies else "series"
        if not doc:
            continue
        results.append({**doc, "content_type": resolved_type})

    return results


def _has_hidden_genre(doc: dict, hidden_ids: list[int]) -> bool:
    if not hidden_ids:
        return False
    return any(g.get("genre_id") in hidden_ids for g in (doc.get("genres") or []))


@router.get("/stats")
async def content_stats():
    """Return global content counts from the database."""
    db = get_database()
    movie_count, series_count, genre_count = await asyncio.gather(
        db.tblMovies.count_documents({}),
        db.tblSeries.count_documents({}),
        db.tblGenres.count_documents({}),
    )
    return {
        "movie_count": movie_count,
        "series_count": series_count,
        "genre_count": genre_count,
    }


@router.get("/movie/{movie_id}")
async def movie_detail(movie_id: int):
    try:
        movie = await get_movie_by_id(movie_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    hidden_ids = await get_hidden_genre_ids()
    if movie.get("is_hidden") or _has_hidden_genre(movie, hidden_ids):
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@router.get("/series/{series_id}")
async def series_detail(series_id: int):
    try:
        series = await get_series_by_id(series_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    hidden_ids = await get_hidden_genre_ids()
    if series.get("is_hidden") or _has_hidden_genre(series, hidden_ids):
        raise HTTPException(status_code=404, detail="Series not found")
    return series
