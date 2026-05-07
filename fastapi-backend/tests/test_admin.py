"""
Tests for admin router — focused on genre visibility (the new feature).
"""

import pytest
from bson import ObjectId

from app.core.security import create_access_token


@pytest.fixture
async def admin_user(db):
    """Insert an admin and return the doc."""
    user_doc = {
        "_id": ObjectId(),
        "email": "admin@vozflix.com",
        "password": "irrelevant",
        "username": "admin",
        "role": "admin",
        "is_active": True,
    }
    await db.users.insert_one(user_doc)
    user_doc["_id"] = str(user_doc["_id"])
    return user_doc


@pytest.fixture
def admin_headers(admin_user):
    token = create_access_token(admin_user["_id"], admin_user["email"])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def seeded_genres(db):
    """Two visible genres + one hidden genre."""
    docs = [
        {"_id": ObjectId(), "genre_id": 28, "name": "Action", "is_hidden": False},
        {"_id": ObjectId(), "genre_id": 35, "name": "Comedy"},  # no is_hidden = visible
        {"_id": ObjectId(), "genre_id": 27, "name": "Horror", "is_hidden": True},
    ]
    await db.genres.insert_many(docs)
    return docs


# ── Admin list ────────────────────────────────────────────────────────────

class TestAdminListGenres:
    async def test_admin_sees_all_genres_including_hidden(
        self, client, admin_headers, seeded_genres
    ):
        resp = await client.get("/api/admin/genres", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 3
        names = {g["name"] for g in body}
        assert names == {"Action", "Comedy", "Horror"}
        # is_hidden defaults to False when missing on the document
        comedy = next(g for g in body if g["name"] == "Comedy")
        assert comedy["is_hidden"] is False

    async def test_non_admin_forbidden(
        self, client, auth_headers, seeded_genres
    ):
        resp = await client.get("/api/admin/genres", headers=auth_headers)
        assert resp.status_code == 403

    async def test_unauthenticated_forbidden(self, client, seeded_genres):
        resp = await client.get("/api/admin/genres")
        assert resp.status_code == 401


# ── Toggle visibility ─────────────────────────────────────────────────────

class TestToggleGenreVisibility:
    async def test_admin_can_hide_genre(
        self, client, admin_headers, seeded_genres, db
    ):
        resp = await client.patch(
            "/api/admin/genres/28/visibility",
            headers=admin_headers,
            json={"is_hidden": True},
        )
        assert resp.status_code == 200
        assert resp.json()["is_hidden"] is True
        doc = await db.genres.find_one({"genre_id": 28})
        assert doc["is_hidden"] is True

    async def test_admin_can_unhide_genre(
        self, client, admin_headers, seeded_genres, db
    ):
        resp = await client.patch(
            "/api/admin/genres/27/visibility",
            headers=admin_headers,
            json={"is_hidden": False},
        )
        assert resp.status_code == 200
        assert resp.json()["is_hidden"] is False
        doc = await db.genres.find_one({"genre_id": 27})
        assert doc["is_hidden"] is False

    async def test_unknown_genre_returns_404(
        self, client, admin_headers, seeded_genres
    ):
        resp = await client.patch(
            "/api/admin/genres/9999/visibility",
            headers=admin_headers,
            json={"is_hidden": True},
        )
        assert resp.status_code == 404

    async def test_non_admin_forbidden(
        self, client, auth_headers, seeded_genres
    ):
        resp = await client.patch(
            "/api/admin/genres/28/visibility",
            headers=auth_headers,
            json={"is_hidden": True},
        )
        assert resp.status_code == 403


# ── Public read-paths filter hidden genres ────────────────────────────────

class TestPublicGenreFiltering:
    async def test_public_genres_endpoint_excludes_hidden(
        self, client, seeded_genres
    ):
        resp = await client.get("/api/content/genres")
        assert resp.status_code == 200
        names = {g["name"] for g in resp.json()}
        assert names == {"Action", "Comedy"}
        assert "Horror" not in names

    async def test_browse_returns_404_for_hidden_genre(
        self, client, seeded_genres
    ):
        resp = await client.get("/api/content/browse/27")  # Horror is hidden
        assert resp.status_code == 404

    async def test_browse_works_for_visible_genre(
        self, client, seeded_genres
    ):
        resp = await client.get("/api/content/browse/28")  # Action is visible
        assert resp.status_code == 200
        # Body shape from get_content_by_genre
        body = resp.json()
        assert "movies" in body
        assert "series" in body
