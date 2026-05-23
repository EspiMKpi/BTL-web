"""
Shared test fixtures — mongomock-motor for DB isolation, httpx.AsyncClient for API tests.

Recommender-specific fixtures (FP-Growth + GRU4Rec artifact builders) are in
this file too so multiple test modules can share them.
"""

import json
from datetime import datetime, timezone

import pytest
import torch
from bson import ObjectId
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

import app.database as db_module
from app.core.security import create_access_token, hash_password
from app.main import app
from app.services import history_recommendation_service as _hr
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


# ── FP-Growth artifact fixtures ───────────────────────────────────────────

@pytest.fixture
def fpgrowth_artifact_root(tmp_path, monkeypatch):
    """Redirect FP-Growth ARTIFACT_ROOT to a fresh tmp dir; clear cached state."""
    monkeypatch.setattr(_rs, "ARTIFACT_ROOT", tmp_path)
    _rs._STATE.clear()
    yield tmp_path
    _rs._STATE.clear()


@pytest.fixture
def build_fpgrowth_artifacts():
    """Builder that writes an FP-Growth artifact set to disk.

    Signature: build(artifact_root, content_type, rules, *, kind=None)
        rules: { antecedent_tmdb_id: [consequent_tmdb_id, ...] }
        kind:  override metadata kind (default = current EXPECTED_KIND).
    """
    def _build(artifact_root, content_type, rules, *, kind=None):
        subdir = artifact_root / _rs.SUBDIR_BY_TYPE[content_type]
        subdir.mkdir(parents=True, exist_ok=True)
        (subdir / "rules.json").write_text(json.dumps(
            {str(k): list(v) for k, v in rules.items()}
        ))
        (subdir / "metadata.json").write_text(json.dumps({
            "built_at": datetime.now(timezone.utc).isoformat(),
            "content_type": content_type,
            "n_rules": len(rules),
            "kind": kind or _rs.EXPECTED_KIND,
            "min_support": 0.05,
            "min_confidence": 0.2,
        }))
    return _build


# ── GRU4Rec artifact fixtures ─────────────────────────────────────────────

@pytest.fixture
def gru4rec_artifact_root(tmp_path, monkeypatch):
    """Redirect GRU4Rec ARTIFACT_ROOT to a fresh tmp dir; clear cached state + prediction cache."""
    monkeypatch.setattr(_hr, "ARTIFACT_ROOT", tmp_path)
    _hr._STATE.clear()
    _hr._predict_cache.clear()
    yield tmp_path
    _hr._STATE.clear()
    _hr._predict_cache.clear()


@pytest.fixture
def build_gru4rec_artifacts():
    """Builder that writes a (randomly-initialised) GRU4Rec model + vocab.

    Signature: build(artifact_root, content_type, tmdb_ids, *,
                     embed_dim=16, hidden_dim=32, max_seq_len=10, kind=None)
        tmdb_ids: ordered list — index 0 is RESERVED for pad, so real items
                  go to indices 1..len(tmdb_ids). Pass only real tmdb_ids;
                  the fixture inserts the pad slot for you.
    """
    def _build(
        artifact_root,
        content_type,
        tmdb_ids,
        *,
        embed_dim=16,
        hidden_dim=32,
        max_seq_len=10,
        kind=None,
    ):
        subdir = artifact_root / _hr.SUBDIR_BY_TYPE[content_type]
        subdir.mkdir(parents=True, exist_ok=True)

        # Pad-aware vocab. idx_to_tmdb[0] = 0 (sentinel, never returned).
        idx_to_tmdb = [0] + [int(t) for t in tmdb_ids]
        tmdb_to_idx = {int(t): i + 1 for i, t in enumerate(tmdb_ids)}
        vocab_size = len(idx_to_tmdb)

        model = _hr.GRU4RecModel(vocab_size=vocab_size, embed_dim=embed_dim, hidden_dim=hidden_dim)
        torch.save(model.state_dict(), subdir / "model.pt")

        (subdir / "item_vocab.json").write_text(json.dumps({
            "tmdb_to_idx": {str(k): v for k, v in tmdb_to_idx.items()},
            "idx_to_tmdb": idx_to_tmdb,
        }))
        (subdir / "metadata.json").write_text(json.dumps({
            "built_at": datetime.now(timezone.utc).isoformat(),
            "content_type": content_type,
            "n_items": len(tmdb_ids),
            "embed_dim": embed_dim,
            "hidden_dim": hidden_dim,
            "max_seq_len": max_seq_len,
            "kind": kind or _hr.EXPECTED_KIND,
        }))
    return _build
