"""
Tests for ratings router — get ratings, get my ratings, create, delete.
"""

import pytest
from bson import ObjectId


# ── Get Public Ratings ────────────────────────────────────────────────────

class TestGetRatings:
    async def test_get_ratings_empty(self, client):
        resp = await client.get("/api/ratings/?tmdb_id=550")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ratings"] == []
        assert body["stats"]["average"] == 0
        assert body["stats"]["count"] == 0

    async def test_get_ratings_with_data(self, client, db, test_user):
        # Seed ratings
        await db.tblUserRatings.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["_id"],
            "content_type": "movie",
            "tmdb_id": 550,
            "rating": 8.5,
            "review": "Great movie!",
            "created_at": "2025-01-15T10:00:00Z",
        })
        await db.tblUserRatings.insert_one({
            "_id": ObjectId(),
            "user_id": str(ObjectId()),
            "content_type": "movie",
            "tmdb_id": 550,
            "rating": 7.0,
            "created_at": "2025-01-16T10:00:00Z",
        })

        resp = await client.get("/api/ratings/?tmdb_id=550")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["ratings"]) == 2
        assert body["stats"]["count"] == 2
        assert body["stats"]["average"] == 7.8  # (8.5 + 7.0) / 2 = 7.75 → rounded to 7.8

    async def test_get_ratings_filter_by_content_type(self, client, db, test_user):
        await db.tblUserRatings.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["_id"],
            "content_type": "movie",
            "tmdb_id": 550,
            "rating": 8.0,
            "created_at": "2025-01-15T10:00:00Z",
        })
        await db.tblUserRatings.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["_id"],
            "content_type": "series",
            "tmdb_id": 550,
            "rating": 9.0,
            "created_at": "2025-01-16T10:00:00Z",
        })

        resp = await client.get("/api/ratings/?tmdb_id=550&content_type=movie")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["ratings"]) == 1
        assert body["ratings"][0]["content_type"] == "movie"

    async def test_get_ratings_requires_tmdb_id(self, client):
        resp = await client.get("/api/ratings/")
        assert resp.status_code == 422  # tmdb_id is required


# ── Get My Ratings ────────────────────────────────────────────────────────

class TestGetMyRatings:
    async def test_my_ratings_empty(self, client, auth_headers):
        resp = await client.get("/api/ratings/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_my_ratings_with_data(self, client, auth_headers, db, test_user):
        await db.tblUserRatings.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["_id"],
            "content_type": "movie",
            "tmdb_id": 550,
            "rating": 8.5,
            "review": "Great!",
            "created_at": "2025-01-15T10:00:00Z",
        })
        await db.tblUserRatings.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["_id"],
            "content_type": "series",
            "tmdb_id": 1399,
            "rating": 9.0,
            "created_at": "2025-01-16T10:00:00Z",
        })

        resp = await client.get("/api/ratings/me", headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 2

    async def test_my_ratings_filter(self, client, auth_headers, db, test_user):
        await db.tblUserRatings.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["_id"],
            "content_type": "movie",
            "tmdb_id": 550,
            "rating": 8.5,
            "created_at": "2025-01-15T10:00:00Z",
        })
        await db.tblUserRatings.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["_id"],
            "content_type": "series",
            "tmdb_id": 1399,
            "rating": 9.0,
            "created_at": "2025-01-16T10:00:00Z",
        })

        resp = await client.get("/api/ratings/me?content_type=series", headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["content_type"] == "series"

    async def test_my_ratings_no_auth(self, client):
        resp = await client.get("/api/ratings/me")
        assert resp.status_code == 401


# ── Create Rating ─────────────────────────────────────────────────────────

class TestCreateRating:
    async def test_create_rating_success(self, client, auth_headers):
        resp = await client.post(
            "/api/ratings/",
            json={
                "content_type": "movie",
                "tmdb_id": 550,
                "rating": 8.5,
                "review": "Excellent film!",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["rating"] == 8.5
        assert body["review"] == "Excellent film!"
        assert body["content_type"] == "movie"
        assert body["tmdb_id"] == 550

    async def test_create_rating_without_review(self, client, auth_headers):
        resp = await client.post(
            "/api/ratings/",
            json={"content_type": "movie", "tmdb_id": 550, "rating": 7.0},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["review"] is None

    async def test_create_rating_upserts(self, client, auth_headers):
        """Rating same content twice should update, not duplicate."""
        resp1 = await client.post(
            "/api/ratings/",
            json={"content_type": "movie", "tmdb_id": 550, "rating": 7.0},
            headers=auth_headers,
        )
        resp2 = await client.post(
            "/api/ratings/",
            json={"content_type": "movie", "tmdb_id": 550, "rating": 9.0},
            headers=auth_headers,
        )
        assert resp1.status_code == 201
        assert resp2.status_code == 201
        assert resp1.json()["_id"] == resp2.json()["_id"]
        assert resp2.json()["rating"] == 9.0

    async def test_create_rating_invalid_range(self, client, auth_headers):
        resp = await client.post(
            "/api/ratings/",
            json={"content_type": "movie", "tmdb_id": 550, "rating": 11.0},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "between 0 and 10" in resp.json()["detail"].lower()

    async def test_create_rating_negative(self, client, auth_headers):
        resp = await client.post(
            "/api/ratings/",
            json={"content_type": "movie", "tmdb_id": 550, "rating": -1.0},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    async def test_create_rating_missing_fields(self, client, auth_headers):
        resp = await client.post(
            "/api/ratings/",
            json={"content_type": "movie"},  # missing tmdb_id and rating
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_create_rating_no_auth(self, client):
        resp = await client.post(
            "/api/ratings/",
            json={"content_type": "movie", "tmdb_id": 550, "rating": 8.0},
        )
        assert resp.status_code == 401


# ── Delete Rating ─────────────────────────────────────────────────────────

class TestDeleteRating:
    async def test_delete_rating_success(self, client, auth_headers):
        # Create a rating first
        await client.post(
            "/api/ratings/",
            json={"content_type": "movie", "tmdb_id": 550, "rating": 8.0},
            headers=auth_headers,
        )

        resp = await client.request(
            "DELETE",
            "/api/ratings/",
            json={"content_type": "movie", "tmdb_id": 550},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "message" in resp.json()

        # Verify it's gone
        me_resp = await client.get("/api/ratings/me", headers=auth_headers)
        assert me_resp.json() == []

    async def test_delete_rating_not_found(self, client, auth_headers):
        """Deleting a non-existent rating should still succeed (idempotent)."""
        resp = await client.request(
            "DELETE",
            "/api/ratings/",
            json={"content_type": "movie", "tmdb_id": 9999},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    async def test_delete_rating_no_auth(self, client):
        resp = await client.request(
            "DELETE",
            "/api/ratings/",
            json={"content_type": "movie", "tmdb_id": 550},
        )
        assert resp.status_code == 401
