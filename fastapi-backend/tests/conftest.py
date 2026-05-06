"""
Shared test fixtures — mongomock-motor for DB isolation, httpx.AsyncClient for API tests.
"""

import pytest
from bson import ObjectId
from mongomock_motor import AsyncMongoMockClient
from httpx import ASGITransport, AsyncClient

import app.database as db_module
from app.core.security import create_access_token, hash_password
from app.main import app


# ── Database ──────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
async def _mock_db():
    """Replace the real Motor client with mongomock for every test."""
    client = AsyncMongoMockClient()
    db_module._client = client
    yield client
    db_module._client = None
    client.close()


@pytest.fixture
def db(_mock_db):
    """Shortcut to the mock database."""
    return _mock_db["movie_db"]


# ── HTTP client ───────────────────────────────────────────────────────────

@pytest.fixture
async def client():
    """Async HTTP client wired to the ASGI app (lifespan NOT triggered)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── User helpers ──────────────────────────────────────────────────────────

@pytest.fixture
async def test_user(db):
    """Insert a verified user and return the doc (password: Test1234!)."""
    user_doc = {
        "_id": ObjectId(),
        "email": "tester@vozflix.com",
        "password": hash_password("Test1234!"),
        "username": "tester",
        "avatar_url": None,
        "role": "user",
        "is_active": True,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }
    await db.users.insert_one(user_doc)
    user_doc["_id"] = str(user_doc["_id"])
    return user_doc


@pytest.fixture
def auth_headers(test_user):
    """Authorization headers with a valid JWT for test_user."""
    token = create_access_token(test_user["_id"], test_user["email"])
    return {"Authorization": f"Bearer {token}"}
