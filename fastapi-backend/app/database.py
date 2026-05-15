"""
Motor async MongoDB client — replaces Mongoose connection.
Uses the same MONGODB_URI and DB_NAME from .env.
Falls back to mongomock for development/testing when MongoDB is unavailable.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from mongomock_motor import AsyncMongoMockClient
from app.core.config import settings


_client: AsyncIOMotorClient | AsyncMongoMockClient | None = None
_use_mock = False

async def connect_to_mongo() -> None:
    """Call once at startup. Falls back to mongomock if MongoDB unavailable."""
    global _client

    global _use_mock
    try:
        _client = AsyncIOMotorClient(settings.MONGODB_URI)
        # Verify connection
        await _client.admin.command("ping")
        _use_mock = False
        print(f"✓ Connected to MongoDB (db={settings.DB_NAME})")
    except Exception as e:
        print(f"⚠ MongoDB connection failed: {e}")
        print("  Falling back to in-memory mongomock for development...")
        _client = AsyncMongoMockClient()
        _use_mock = True
        print(f"✓ Using mongomock in-memory database (db={settings.DB_NAME})")

async def close_mongo_connection() -> None:
    """Call at shutdown."""
    global _client
    if _client:
        _client.close()
        _client = None

        print("Database connection closed")

def get_database() -> AsyncIOMotorDatabase:
    """Return the database instance for use in services/routes."""
    if _client is None:
        raise RuntimeError("Database client not initialised — call connect_to_mongo first")
    return _client[settings.DB_NAME]
