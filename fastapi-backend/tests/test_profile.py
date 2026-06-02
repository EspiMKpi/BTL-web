"""
Tests for profile router — get profile, update profile, stats, recent activity.
"""

import pytest
from bson import ObjectId


# ── Get Profile ───────────────────────────────────────────────────────────

class TestGetProfile:
    async def test_get_profile(self, client, auth_headers, test_user):
        resp = await client.get("/api/profile/", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == test_user["email"]
        assert body["username"] == test_user["username"]
        assert body["id"] == test_user["_id"]
        assert body["role"] == "user"
        assert body["is_active"] is True

    async def test_get_profile_no_auth(self, client):
        resp = await client.get("/api/profile/")
        assert resp.status_code == 401


# ── Update Profile ────────────────────────────────────────────────────────

class TestUpdateProfile:
    async def test_update_username(self, client, auth_headers):
        resp = await client.patch(
            "/api/profile/",
            json={"username": "newname"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == "newname"

    async def test_update_avatar(self, client, auth_headers):
        resp = await client.patch(
            "/api/profile/",
            json={"avatar_url": "https://example.com/avatar.png"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["avatar_url"] == "https://example.com/avatar.png"

    async def test_update_multiple_fields(self, client, auth_headers):
        resp = await client.patch(
            "/api/profile/",
            json={"username": "cooluser", "avatar_url": "https://example.com/pic.jpg"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == "cooluser"
        assert body["avatar_url"] == "https://example.com/pic.jpg"

    async def test_update_empty_body(self, client, auth_headers):
        resp = await client.patch(
            "/api/profile/",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    async def test_update_no_auth(self, client):
        resp = await client.patch(
            "/api/profile/",
            json={"username": "hacker"},
        )
        assert resp.status_code == 401


# ── Profile Stats ─────────────────────────────────────────────────────────

class TestProfileStats:
    async def test_stats_empty(self, client, auth_headers):
        resp = await client.get("/api/profile/stats", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["watchlist_count"] == 0
        assert body["completed_count"] == 0
        assert body["watching_count"] == 0
        assert body["ratings_count"] == 0
        assert body["history_count"] == 0
        assert body["average_rating"] == 0

    async def test_stats_with_data(self, client, auth_headers, test_user, db):
        # Add watchlist items
        await db.tblWatchlistItems.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["_id"],
            "content_type": "movie",
            "tmdb_id": 550,
            "status": "watching",
        })
        await db.tblWatchlistItems.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["_id"],
            "content_type": "movie",
            "tmdb_id": 680,
            "status": "completed",
        })
        await db.tblWatchlistItems.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["_id"],
            "content_type": "series",
            "tmdb_id": 1399,
            "status": "completed",
        })

        # Add ratings
        await db.tblUserRatings.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["_id"],
            "content_type": "movie",
            "tmdb_id": 550,
            "rating": 8.0,
        })
        await db.tblUserRatings.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["_id"],
            "content_type": "movie",
            "tmdb_id": 680,
            "rating": 9.0,
        })

        # Add history
        await db.tblWatchHistory.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["_id"],
            "content_type": "movie",
            "tmdb_id": 550,
            "progress_seconds": 1200,
        })

        resp = await client.get("/api/profile/stats", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["watchlist_count"] == 3
        assert body["completed_count"] == 2
        assert body["watching_count"] == 1
        assert body["ratings_count"] == 2
        assert body["history_count"] == 1
        assert body["average_rating"] == 8.5

    async def test_stats_no_auth(self, client):
        resp = await client.get("/api/profile/stats")
        assert resp.status_code == 401


# ── Recent Activity ───────────────────────────────────────────────────────

class TestRecentActivity:
    async def test_recent_activity_empty(self, client, auth_headers):
        resp = await client.get("/api/profile/recent-activity", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["recent_history"] == []
        assert body["recent_ratings"] == []
        assert body["recent_watchlist"] == []

    async def test_recent_activity_with_data(self, client, auth_headers, test_user, db):
        await db.tblWatchHistory.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["_id"],
            "content_type": "movie",
            "tmdb_id": 550,
            "progress_seconds": 1200,
            "last_watched_at": "2025-01-15T10:00:00Z",
        })
        await db.tblUserRatings.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["_id"],
            "content_type": "movie",
            "tmdb_id": 550,
            "rating": 8.5,
            "created_at": "2025-01-15T10:00:00Z",
        })
        await db.tblWatchlistItems.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["_id"],
            "content_type": "movie",
            "tmdb_id": 550,
            "status": "plan_to_watch",
            "updated_at": "2025-01-15T10:00:00Z",
        })

        resp = await client.get("/api/profile/recent-activity", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["recent_history"]) == 1
        assert len(body["recent_ratings"]) == 1
        assert len(body["recent_watchlist"]) == 1

    async def test_recent_activity_limit(self, client, auth_headers, test_user, db):
        for i in range(5):
            await db.tblWatchHistory.insert_one({
                "_id": ObjectId(),
                "user_id": test_user["_id"],
                "content_type": "movie",
                "tmdb_id": 1000 + i,
                "progress_seconds": 600,
                "last_watched_at": f"2025-01-{15+i:02d}T10:00:00Z",
            })

        resp = await client.get("/api/profile/recent-activity?limit=2", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["recent_history"]) == 2

    async def test_recent_activity_no_auth(self, client):
        resp = await client.get("/api/profile/recent-activity")
        assert resp.status_code == 401
