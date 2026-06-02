"""
One-shot migration: rename existing MongoDB collections to the tbl* camelCase scheme.

Idempotent — skips a pair if the source collection is missing or the target already
exists, so it is safe to re-run. Uses a raw Motor client (NOT connect_to_mongo) on
purpose: connect_to_mongo ensures indexes on the *new* tbl* names, which would create
empty target collections and cause the rename to be skipped.

Run once against the live database after the code rename has landed:
    .venv\\Scripts\\python scripts/rename_collections_to_tbl.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings

RENAMES = {
    "movies": "tblMovies",
    "series": "tblSeries",
    "genres": "tblGenres",
    "users": "tblUsers",
    "user_ratings": "tblUserRatings",
    "watch_history": "tblWatchHistory",
    "watchlist_items": "tblWatchlistItems",
    "movie_genres": "tblMovieGenres",
    "series_genres": "tblSeriesGenres",
    "comments": "tblComments",
}


async def main() -> None:
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DB_NAME]
    print(f"Connected to MongoDB (db={settings.DB_NAME})")

    existing = set(await db.list_collection_names())
    renamed = skipped = 0

    for old, new in RENAMES.items():
        if old not in existing:
            print(f"  skip: source '{old}' does not exist")
            skipped += 1
            continue
        if new in existing:
            # The auto-reloading app may have pre-created an EMPTY target via the
            # startup index step (database.py ensures indexes on the tbl* names).
            # If the target is empty, drop it so the source (with its data) can
            # take the name; if it already holds data, leave everything untouched.
            if await db[new].count_documents({}) == 0:
                await db[new].drop()
                print(f"  dropped empty pre-created target '{new}'")
            else:
                print(f"  skip: target '{new}' already has data")
                skipped += 1
                continue
        await db[old].rename(new)
        print(f"  renamed: '{old}' -> '{new}'")
        renamed += 1

    client.close()
    print(f"\nDone. renamed={renamed}, skipped={skipped}")


if __name__ == "__main__":
    asyncio.run(main())
