"""
Movie service — mirrors database/src/movieService.ts.
Two-tier fetch: MongoDB first, then TMDB API with upsert.
"""

from datetime import datetime
from typing import Any, List, Optional

import httpx
import re
from bson import ObjectId

from app.core.config import settings
from app.database import get_database


def _sanitize(value: Any) -> Any:
    """Recursively convert ObjectId and datetime to JSON-serializable types."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    return value


async def get_movie_by_id(tmdb_id: int) -> dict:
    """Fetch a movie by TMDB ID. Checks MongoDB first, then falls back to TMDB API."""
    db = get_database()

    existing = await db.movies.find_one({"tmdb_id": tmdb_id})
    if existing and existing.get("raw_data") and existing.get("title"):
        print(f"Movie {tmdb_id} served from MongoDB")
        return _sanitize(existing)

    print(f"Movie {tmdb_id} fetching from TMDB...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.themoviedb.org/3/movie/{tmdb_id}",
            params={
                "api_key": settings.TMDB_API_KEY,
                "append_to_response": "credits",
            },
            timeout=15.0,
        )
        resp.raise_for_status()
    data = resp.json()

    # Upsert genres
    for genre in data.get("genres", []):
        await db.genres.update_one(
            {"genre_id": genre["id"]},
            {"$set": {"name": genre["name"]}},
            upsert=True,
        )

    credits = data.get("credits", {})
    cast = [
        {
            "person_id": a["id"],
            "name": a["name"],
            "profile_path": a.get("profile_path"),
            "character_name": a.get("character", ""),
            "cast_order": a.get("order", 0),
        }
        for a in (credits.get("cast") or [])[:20]
    ]
    crew = [
        {
            "person_id": c["id"],
            "name": c["name"],
            "profile_path": c.get("profile_path"),
            "job": c.get("job", ""),
        }
        for c in (credits.get("crew") or [])
        if c.get("job") in ("Director", "Producer", "Writer")
    ][:10]

    movie_doc = {
        "tmdb_id": data["id"],
        "title": data["title"],
        "original_title": data.get("original_title"),
        "tagline": data.get("tagline"),
        "overview": data.get("overview", ""),
        "poster_path": data.get("poster_path"),
        "backdrop_path": data.get("backdrop_path"),
        "release_date": data.get("release_date"),
        "original_language": data.get("original_language"),
        "popularity": data.get("popularity", 0),
        "vote_average": data.get("vote_average", 0),
        "vote_count": data.get("vote_count", 0),
        "adult": data.get("adult", False),
        "video": data.get("video", False),
        "runtime": data.get("runtime"),
        "budget": data.get("budget", 0),
        "revenue": data.get("revenue", 0),
        "status": data.get("status"),
        "imdb_id": data.get("imdb_id"),
        "homepage": data.get("homepage"),
        "genres": [{"genre_id": g["id"], "name": g["name"]} for g in data.get("genres", [])],
        "cast": cast,
        "crew": crew,
        "production_countries_json": data.get("production_countries", []),
        "spoken_languages_json": data.get("spoken_languages", []),
        "raw_data": data,
        "updated_at": __import__("datetime").datetime.utcnow(),
    }

    result = await db.movies.find_one_and_update(
        {"tmdb_id": data["id"]},
        {
            "$set": movie_doc,
            "$setOnInsert": {"created_at": datetime.utcnow()},
        },
        upsert=True,
        return_document=True,
    )
    return _sanitize(result)


async def get_movies_by_ids(tmdb_ids: List[int]) -> List[dict]:
    db = get_database()
    cursor = db.movies.find({"tmdb_id": {"$in": tmdb_ids}})
    docs = []
    async for doc in cursor:
        docs.append(_sanitize(doc))
    return docs


async def search_movies(query: str, limit: int = 20) -> List[dict]:
    db = get_database()
    escaped_query = re.escape(query)
    cursor = (
        db.movies.find({"title": {"$regex": escaped_query, "$options": "i"}})
        # Optional: You can't use textScore anymore, so sort alphabetically or by year
        # .sort("title", 1) 
        .limit(limit)
    )
    docs = []
    async for doc in cursor:
        docs.append(_sanitize(doc))
    return docs
