"""
Series service — mirrors database/src/seriesService.ts.
Fetches TV series from MongoDB or TMDB API with full season/episode data.
"""

from datetime import datetime
from typing import List

import httpx

from app.core.config import settings
from app.database import get_database
from app.utils import is_series_doc, sanitize as _sanitize


async def get_series_by_id(tmdb_id: int) -> dict:
    """Fetch a TV series by TMDB ID. Checks MongoDB first, then falls back to TMDB API."""
    db = get_database()

    existing = await db.tblSeries.find_one({"tmdb_id": tmdb_id})
    if existing and existing.get("raw_data") and existing.get("seasons"):
        # Guard: reject movie documents that ended up in the series collection
        if not is_series_doc(existing):
            raise ValueError(f"{tmdb_id} is not a series")
        return _sanitize(existing)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.themoviedb.org/3/tv/{tmdb_id}",
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
        await db.tblGenres.update_one(
            {"genre_id": genre["id"]},
            {"$set": {"name": genre["name"]}},
            upsert=True,
        )

    # Reconcile the series_genres junction (canonical n-n store). Derived from the
    # same data["genres"] used for the embedded array below, so the two never drift.
    genre_ids = [g["id"] for g in data.get("genres", [])]
    await db.tblSeriesGenres.delete_many({"tmdb_id": data["id"]})
    if genre_ids:
        await db.tblSeriesGenres.insert_many(
            [{"tmdb_id": data["id"], "genre_id": gid} for gid in genre_ids],
            ordered=False,
        )

    # Fetch season details with episodes (limit to first 10 seasons)
    seasons_to_fetch = (data.get("seasons") or [])[:10]
    enriched_seasons: list[dict] = []

    async with httpx.AsyncClient() as client:
        for season in seasons_to_fetch:
            try:
                s_resp = await client.get(
                    f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season['season_number']}",
                    params={"api_key": settings.TMDB_API_KEY},
                    timeout=15.0,
                )
                s_resp.raise_for_status()
                s_data = s_resp.json()

                enriched_seasons.append(
                    {
                        "season_number": season["season_number"],
                        "name": season.get("name") or s_data.get("name", ""),
                        "overview": season.get("overview") or s_data.get("overview", ""),
                        "poster_path": season.get("poster_path") or s_data.get("poster_path"),
                        "air_date": season.get("air_date") or s_data.get("air_date"),
                        "episode_count": season.get("episode_count") or len(s_data.get("episodes", [])),
                        "episodes": [
                            {
                                "episode_number": ep["episode_number"],
                                "name": ep.get("name", ""),
                                "overview": ep.get("overview", ""),
                                "still_path": ep.get("still_path"),
                                "air_date": ep.get("air_date"),
                                "runtime": ep.get("runtime"),
                                "vote_average": ep.get("vote_average", 0),
                                "vote_count": ep.get("vote_count", 0),
                                "season_number": ep["season_number"],
                            }
                            for ep in s_data.get("episodes", [])
                        ],
                    }
                )
            except Exception:
                enriched_seasons.append(
                    {
                        "season_number": season["season_number"],
                        "name": season.get("name", ""),
                        "overview": season.get("overview", ""),
                        "poster_path": season.get("poster_path"),
                        "air_date": season.get("air_date"),
                        "episode_count": season.get("episode_count", 0),
                        "episodes": [],
                    }
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
        if c.get("job") in ("Director", "Producer", "Writer", "Executive Producer")
    ][:10]

    series_doc = {
        "tmdb_id": data["id"],
        "name": data["name"],
        "original_name": data.get("original_name"),
        "tagline": data.get("tagline"),
        "overview": data.get("overview", ""),
        "poster_path": data.get("poster_path"),
        "backdrop_path": data.get("backdrop_path"),
        "first_air_date": data.get("first_air_date"),
        "last_air_date": data.get("last_air_date"),
        "original_language": data.get("original_language"),
        "popularity": data.get("popularity", 0),
        "vote_average": data.get("vote_average", 0),
        "vote_count": data.get("vote_count", 0),
        "adult": data.get("adult", False),
        "episode_run_time": data.get("episode_run_time", []),
        "type": data.get("type"),
        "status": data.get("status"),
        "imdb_id": data.get("imdb_id"),
        "homepage": data.get("homepage"),
        "number_of_seasons": data.get("number_of_seasons", 0),
        "number_of_episodes": data.get("number_of_episodes", 0),
        "genres": [{"genre_id": g["id"], "name": g["name"]} for g in data.get("genres", [])],
        "cast": cast,
        "crew": crew,
        "seasons": enriched_seasons,
        "networks_json": data.get("networks", []),
        "production_countries_json": data.get("production_countries", []),
        "spoken_languages_json": data.get("spoken_languages", []),
        "raw_data": data,
        "updated_at": datetime.utcnow(),
    }

    result = await db.tblSeries.find_one_and_update(
        {"tmdb_id": data["id"]},
        {
            "$set": series_doc,
            "$setOnInsert": {"created_at": datetime.utcnow()},
        },
        upsert=True,
        return_document=True,
    )
    return _sanitize(result)


async def get_series_by_ids(tmdb_ids: List[int]) -> List[dict]:
    db = get_database()
    cursor = db.tblSeries.find({"tmdb_id": {"$in": tmdb_ids}})
    docs = []
    async for doc in cursor:
        docs.append(_sanitize(doc))
    return docs
