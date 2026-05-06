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
