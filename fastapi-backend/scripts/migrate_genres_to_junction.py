"""
Backfill the movie_genres / series_genres junction collections from the
embedded `genres[]` arrays already stored on each movie / series document.

Idempotent and re-runnable: each (tmdb_id, genre_id) pair is upserted, so
running it twice creates no duplicates.

Run from the fastapi-backend/ directory:
    python scripts/migrate_genres_to_junction.py

Phase B (current): the embedded `genres[]` arrays are KEPT as a display cache;
this script only adds the junction. If/when you move to phase A (junction as the
sole source of truth) set UNSET_EMBEDDED = True to also drop the arrays — do this
only after the read paths that still read `genres[]` (detail, search, home/search
cascade) have been migrated to hydrate from the junction.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import connect_to_mongo, get_database

UNSET_EMBEDDED = False


async def _ensure_indexes(db, junction: str) -> None:
    await db[junction].create_index(
        [("tmdb_id", 1), ("genre_id", 1)], unique=True, name="uniq_tmdb_genre"
    )
    await db[junction].create_index([("genre_id", 1)], name="by_genre")


async def backfill(db, content_coll: str, junction: str) -> tuple[int, int]:
    """Return (pairs_written, docs_unset)."""
    await _ensure_indexes(db, junction)
    pairs = 0
    docs_unset = 0
    cursor = db[content_coll].find({}, {"tmdb_id": 1, "genres": 1})
    async for doc in cursor:
        tmdb_id = doc.get("tmdb_id")
        if tmdb_id is None:
            continue
        genre_ids = [
            g.get("genre_id")
            for g in (doc.get("genres") or [])
            if isinstance(g, dict) and g.get("genre_id") is not None
        ]
        for gid in genre_ids:
            await db[junction].update_one(
                {"tmdb_id": tmdb_id, "genre_id": gid},
                {"$setOnInsert": {"tmdb_id": tmdb_id, "genre_id": gid}},
                upsert=True,
            )
            pairs += 1
        if UNSET_EMBEDDED and genre_ids:
            await db[content_coll].update_one(
                {"_id": doc["_id"]}, {"$unset": {"genres": ""}}
            )
            docs_unset += 1
    return pairs, docs_unset


async def main() -> None:
    print("Connecting to MongoDB...")
    await connect_to_mongo()
    db = get_database()

    print("Backfilling movie_genres from movies.genres[] ...")
    m_pairs, m_unset = await backfill(db, "movies", "movie_genres")
    print(f"  movie_genres: {m_pairs} pairs upserted"
          + (f", {m_unset} movies unset" if UNSET_EMBEDDED else ""))

    print("Backfilling series_genres from series.genres[] ...")
    s_pairs, s_unset = await backfill(db, "series", "series_genres")
    print(f"  series_genres: {s_pairs} pairs upserted"
          + (f", {s_unset} series unset" if UNSET_EMBEDDED else ""))

    m_total = await db.movie_genres.count_documents({})
    s_total = await db.series_genres.count_documents({})
    print(f"\nDone. movie_genres={m_total} docs, series_genres={s_total} docs.")


if __name__ == "__main__":
    asyncio.run(main())
