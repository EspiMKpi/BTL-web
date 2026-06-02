"""
Seed MongoDB with popular movies and TV series from TMDB.

Run from the fastapi-backend/ directory:
    python scripts/seed_tmdb.py
"""

import asyncio
import os
import sys
import time

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.database import connect_to_mongo
from app.services.movieService import get_movie_by_id
from app.services.seriesService import get_series_by_id

TMDB_BASE = "https://api.themoviedb.org/3"
PAGES = 5
SEMAPHORE_LIMIT = 5


async def fetch_tmdb_ids(client: httpx.AsyncClient, endpoint: str, pages: int) -> set[int]:
    ids: set[int] = set()
    for page in range(1, pages + 1):
        try:
            resp = await client.get(
                f"{TMDB_BASE}{endpoint}",
                params={"api_key": settings.TMDB_API_KEY, "page": page},
                timeout=15,
            )
            resp.raise_for_status()
            for item in resp.json().get("results", []):
                if item.get("id"):
                    ids.add(item["id"])
        except Exception as e:
            print(f"  Warning: failed to fetch {endpoint} page {page}: {e}")
    return ids


async def seed_movies(movie_ids: set[int]) -> int:
    sem = asyncio.Semaphore(SEMAPHORE_LIMIT)
    ok = 0

    async def upsert(tmdb_id: int) -> None:
        nonlocal ok
        async with sem:
            try:
                await get_movie_by_id(tmdb_id)
                ok += 1
            except Exception as e:
                print(f"  Movie {tmdb_id} failed: {e}")

    await asyncio.gather(*[upsert(mid) for mid in movie_ids])
    return ok


async def seed_series(series_ids: set[int]) -> int:
    sem = asyncio.Semaphore(SEMAPHORE_LIMIT)
    ok = 0

    async def upsert(tmdb_id: int) -> None:
        nonlocal ok
        async with sem:
            try:
                await get_series_by_id(tmdb_id)
                ok += 1
            except Exception as e:
                print(f"  Series {tmdb_id} failed: {e}")

    await asyncio.gather(*[upsert(sid) for sid in series_ids])
    return ok


async def main() -> None:
    print("Connecting to MongoDB...")
    await connect_to_mongo()

    print("Fetching TMDB ID lists...")
    async with httpx.AsyncClient() as client:
        movie_popular_ids, movie_top_ids, series_ids = await asyncio.gather(
            fetch_tmdb_ids(client, "/movie/popular", PAGES),
            fetch_tmdb_ids(client, "/movie/top_rated", PAGES),
            fetch_tmdb_ids(client, "/tv/popular", PAGES),
        )

    all_movie_ids = movie_popular_ids | movie_top_ids
    print(f"\nSeeding {len(all_movie_ids)} movies...")
    t0 = time.monotonic()
    movies_ok = await seed_movies(all_movie_ids)
    print(f"Movies done: {movies_ok}/{len(all_movie_ids)} upserted in {time.monotonic() - t0:.1f}s")

    print(f"\nSeeding {len(series_ids)} TV series (this takes longer — fetches all seasons)...")
    t1 = time.monotonic()
    series_ok = await seed_series(series_ids)
    print(f"Series done: {series_ok}/{len(series_ids)} upserted in {time.monotonic() - t1:.1f}s")

    elapsed = time.monotonic() - t0
    print(f"\nDone. {movies_ok} movies + {series_ok} series seeded in {elapsed:.0f}s total.")


if __name__ == "__main__":
    asyncio.run(main())
