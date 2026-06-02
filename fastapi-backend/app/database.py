"""
Motor async MongoDB client — replaces Mongoose connection.
Uses the same MONGODB_URI and DB_NAME from .env.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

_client: AsyncIOMotorClient | None = None


async def connect_to_mongo() -> None:
    """Call once at startup."""
    global _client
    _client = AsyncIOMotorClient(settings.MONGODB_URI)
    # Verify connection
    await _client.admin.command("ping")
    print(f"Connected to MongoDB Atlas (db={settings.DB_NAME})")

    # Ensure critical unique indexes exist
    db = _client[settings.DB_NAME]
    # Unique index on (user_id, tmdb_id) prevents the same title appearing
    # twice in a user's watchlist, regardless of content_type.
    # Drop old index if it exists (migrating from the old 3-field index).
    try:
        await db.watchlist_items.drop_index("user_id_1_content_type_1_tmdb_id_1")
    except Exception:
        pass  # index may not exist on fresh DB
    await db.watchlist_items.create_index(
        [("user_id", 1), ("tmdb_id", 1)],
        unique=True,
        name="unique_user_tmdb",
    )

    # Genre junction collections (movie_genres / series_genres) materialise the
    # n-n relationship between content and genres. Unique (tmdb_id, genre_id)
    # makes the reconcile-on-upsert idempotent; the genre_id index serves the
    # genre -> content browse direction.
    for junction in ("movie_genres", "series_genres"):
        await db[junction].create_index(
            [("tmdb_id", 1), ("genre_id", 1)],
            unique=True,
            name="uniq_tmdb_genre",
        )
        await db[junction].create_index([("genre_id", 1)], name="by_genre")


async def close_mongo_connection() -> None:
    """Call at shutdown."""
    global _client
    if _client:
        _client.close()
        _client = None
        print("MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    """Return the database instance for use in services/routes."""
    if _client is None:
        raise RuntimeError("MongoDB client not initialised — call connect_to_mongo first")
    return _client[settings.DB_NAME]
