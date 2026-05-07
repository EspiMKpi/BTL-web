"""
Tests for watchlist router — CRUD operations.
"""

import pytest
from bson import ObjectId


# ── Add to Watchlist ──────────────────────────────────────────────────────

class TestAddWatchlist:
    async def test_add_success(self, client, auth_headers):
        resp = await client.post(
            "/api/watchlist/",
            json={
                "content_type": "movie",
                "tmdb_id": 550,
                "status": "plan_to_watch",
                "is_bookmarked": True,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["content_type"] == "movie"
        assert body["tmdb_id"] == 550
        assert body["status"] == "plan_to_watch"
        assert body["is_bookmarked"] is True
        assert "_id" in body

    async def test_add_duplicate_upserts(self, client, auth_headers):
        """Adding the same content twice should upsert, not duplicate."""
        payload = {
            "content_type": "movie",
            "tmdb_id": 550,
            "status": "plan_to_watch",
        }
        resp1 = await client.post("/api/watchlist/", json=payload, headers=auth_headers)
        resp2 = await client.post(
            "/api/watchlist/",
            json={**payload, "status": "watching"},
            headers=auth_headers,
        )
        assert resp1.status_code == 201
        assert resp2.status_code == 201
        assert resp1.json()["_id"] == resp2.json()["_id"]  # same document
        assert resp2.json()["status"] == "watching"

    async def test_add_no_auth(self, client):
        resp = await client.post(
            "/api/watchlist/",
            json={"content_type": "movie", "tmdb_id": 550},
        )
        assert resp.status_code == 401

    async def test_add_missing_fields(self, client, auth_headers):
        resp = await client.post(
            "/api/watchlist/",
            json={"content_type": "movie"},  # missing tmdb_id
            headers=auth_headers,
        )
        assert resp.status_code == 422  # pydantic validation


# ── Get Watchlist ─────────────────────────────────────────────────────────

class TestGetWatchlist:
    async def test_get_empty(self, client, auth_headers):
        resp = await client.get("/api/watchlist/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_get_with_items(self, client, auth_headers):
        # Add two items
        await client.post(
            "/api/watchlist/",
            json={"content_type": "movie", "tmdb_id": 550, "status": "watching"},
            headers=auth_headers,
        )
        await client.post(
            "/api/watchlist/",
            json={"content_type": "series", "tmdb_id": 1399, "status": "plan_to_watch"},
            headers=auth_headers,
        )
        resp = await client.get("/api/watchlist/", headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 2

    async def test_filter_by_status(self, client, auth_headers):
        await client.post(
            "/api/watchlist/",
            json={"content_type": "movie", "tmdb_id": 550, "status": "watching"},
            headers=auth_headers,
        )
        await client.post(
            "/api/watchlist/",
            json={"content_type": "movie", "tmdb_id": 680, "status": "completed"},
            headers=auth_headers,
        )
        resp = await client.get("/api/watchlist/?status_filter=watching", headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["status"] == "watching"

    async def test_filter_by_content_type(self, client, auth_headers):
        await client.post(
            "/api/watchlist/",
            json={"content_type": "movie", "tmdb_id": 550},
            headers=auth_headers,
        )
        await client.post(
            "/api/watchlist/",
            json={"content_type": "series", "tmdb_id": 1399},
            headers=auth_headers,
        )
        resp = await client.get("/api/watchlist/?content_type=series", headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["content_type"] == "series"

    async def test_no_auth(self, client):
        resp = await client.get("/api/watchlist/")
        assert resp.status_code == 401


# ── Update Watchlist Item ─────────────────────────────────────────────────

class TestUpdateWatchlist:
    async def test_update_status(self, client, auth_headers):
        add_resp = await client.post(
            "/api/watchlist/",
            json={"content_type": "movie", "tmdb_id": 550, "status": "plan_to_watch"},
            headers=auth_headers,
        )
        item_id = add_resp.json()["_id"]

        resp = await client.patch(
            f"/api/watchlist/{item_id}",
            json={"status": "watching"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "watching"

    async def test_update_multiple_fields(self, client, auth_headers):
        add_resp = await client.post(
            "/api/watchlist/",
            json={"content_type": "movie", "tmdb_id": 550},
            headers=auth_headers,
        )
        item_id = add_resp.json()["_id"]

        resp = await client.patch(
            f"/api/watchlist/{item_id}",
            json={"status": "completed", "is_bookmarked": True},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "completed"
        assert body["is_bookmarked"] is True

    async def test_update_empty_body(self, client, auth_headers):
        add_resp = await client.post(
            "/api/watchlist/",
            json={"content_type": "movie", "tmdb_id": 550},
            headers=auth_headers,
        )
        item_id = add_resp.json()["_id"]

        resp = await client.patch(
            f"/api/watchlist/{item_id}",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    async def test_update_not_found(self, client, auth_headers):
        fake_id = str(ObjectId())
        resp = await client.patch(
            f"/api/watchlist/{fake_id}",
            json={"status": "watching"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_update_no_auth(self, client):
        fake_id = str(ObjectId())
        resp = await client.patch(
            f"/api/watchlist/{fake_id}",
            json={"status": "watching"},
        )
        assert resp.status_code == 401


# ── Delete Watchlist Item ─────────────────────────────────────────────────

class TestDeleteWatchlist:
    async def test_delete_success(self, client, auth_headers):
        add_resp = await client.post(
            "/api/watchlist/",
            json={"content_type": "movie", "tmdb_id": 550},
            headers=auth_headers,
        )
        item_id = add_resp.json()["_id"]

        resp = await client.delete(f"/api/watchlist/{item_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert "message" in resp.json()

        # Verify it's gone
        get_resp = await client.get("/api/watchlist/", headers=auth_headers)
        assert len(get_resp.json()) == 0

    async def test_delete_not_found(self, client, auth_headers):
        fake_id = str(ObjectId())
        resp = await client.delete(f"/api/watchlist/{fake_id}", headers=auth_headers)
        assert resp.status_code == 404

    async def test_delete_no_auth(self, client):
        fake_id = str(ObjectId())
        resp = await client.delete(f"/api/watchlist/{fake_id}")
        assert resp.status_code == 401


# ── User Isolation ────────────────────────────────────────────────────────

class TestWatchlistIsolation:
    async def test_user_cannot_see_other_users_items(self, client, auth_headers, db):
        """Users should only see their own watchlist items."""
        # Add item for test_user
        await client.post(
            "/api/watchlist/",
            json={"content_type": "movie", "tmdb_id": 550},
            headers=auth_headers,
        )

        # Create another user
        from app.core.security import hash_password, create_access_token
        other_user_id = str(ObjectId())
        await db.users.insert_one({
            "_id": ObjectId(other_user_id),
            "email": "other@vozflix.com",
            "password": hash_password("Other1234!"),
            "username": "other",
            "role": "user",
            "is_active": True,
        })
        other_token = create_access_token(other_user_id, "other@vozflix.com")
        other_headers = {"Authorization": f"Bearer {other_token}"}

        resp = await client.get("/api/watchlist/", headers=other_headers)
        assert resp.status_code == 200
        assert resp.json() == []
