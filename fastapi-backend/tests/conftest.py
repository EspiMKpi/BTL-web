"""
Shared test fixtures — mongomock-motor for DB isolation, httpx.AsyncClient for API tests.
"""

import json
from datetime import datetime, timezone

import joblib
import numpy as np
import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer

import app.database as db_module
from app.core.security import create_access_token, hash_password
from app.main import app
from app.services import recommendation_service as _rs


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


# ── Recommender artifact fixtures ─────────────────────────────────────────

@pytest.fixture
def artifact_root(tmp_path, monkeypatch):
    """Redirect recommender ARTIFACT_ROOT to a fresh tmp dir; clear cached state.

    Use together with the `build_artifacts` fixture to populate the dir.
    """
    monkeypatch.setattr(_rs, "ARTIFACT_ROOT", tmp_path)
    _rs._STATE.clear()
    yield tmp_path
    _rs._STATE.clear()


@pytest.fixture
def build_artifacts():
    """Return a builder callable that writes a TF-IDF artifact set to disk.

    Signature: build(artifact_root, content_type, items, *, kind=None)
        items: [(tmdb_id, title, soup), ...]
        kind:  override metadata kind (default = current EXPECTED_KIND).
    """
    def _build(artifact_root, content_type, items, *, kind=None):
        subdir = artifact_root / _rs.SUBDIR_BY_TYPE[content_type]
        subdir.mkdir(parents=True, exist_ok=True)
        tmdb_ids = [it[0] for it in items]
        titles = [it[1] for it in items]
        soups = [it[2] for it in items]
        vectorizer = TfidfVectorizer(stop_words="english", dtype=np.float32)
        matrix = vectorizer.fit_transform(soups)
        joblib.dump(vectorizer, subdir / "vectorizer.joblib")
        sparse.save_npz(subdir / "tfidf_matrix.npz", matrix)
        (subdir / "item_index.json").write_text(
            json.dumps({"tmdb_ids": tmdb_ids, "titles": titles})
        )
        (subdir / "metadata.json").write_text(json.dumps({
            "built_at": datetime.now(timezone.utc).isoformat(),
            "content_type": content_type,
            "n_items": len(items),
            "vocab_size": len(vectorizer.vocabulary_),
            "kind": kind or _rs.EXPECTED_KIND,
        }))
    return _build
