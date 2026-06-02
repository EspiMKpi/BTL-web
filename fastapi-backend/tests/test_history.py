"""
Tests for history router — continue-watching, get history, update progress.
"""

import pytest
from bson import ObjectId


# ── Continue Watching ─────────────────────────────────────────────────────

class TestContinueWatching:
    async def test_empty_continue_watching(self, client, auth_headers):
        resp = await client.get("/api/history/continue-watching", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_continue_watching_with_data(self, client, auth_headers, db, test_user):
        # Seed watch history
        await db.tblWatchHistory.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["_id"],
            "content_type": "movie",
            "tmdb_id": 550,
            "progress_seconds": 1200,
            "completed": False,
            "last_watched_at": "2025-01-15T10:00:00Z",
            "created_at": "2025-01-10T10:00:00Z",
        })
        await db.tblWatchHistory.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["_id"],
            "content_type": "series",
            "tmdb_id": 1399,
            "season_number": 1,
            "episode_number": 3,
            "progress_seconds": 600,
            "completed": False,
            "last_watched_at": "2025-01-16T10:00:00Z",
            "created_at": "2025-01-12T10:00:00Z",
        })

        resp = await client.get("/api/history/continue-watching", headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 2
        # Should be sorted by last_watched_at desc
        assert items[0]["tmdb_id"] == 1399
        assert items[1]["tmdb_id"] == 550

    async def test_continue_watching_excludes_completed(self, client, auth_headers, db, test_user):
        await db.tblWatchHistory.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["_id"],
            "content_type": "movie",
            "tmdb_id": 550,
            "progress_seconds": 5400,
            "completed": True,  # completed
            "last_watched_at": "2025-01-15T10:00:00Z",
        })
        resp = await client.get("/api/history/continue-watching", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_continue_watching_excludes_zero_progress(self, client, auth_headers, db, test_user):
        await db.tblWatchHistory.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["_id"],
            "content_type": "movie",
            "tmdb_id": 550,
            "progress_seconds": 0,  # zero progress
            "completed": False,
            "last_watched_at": "2025-01-15T10:00:00Z",
        })
        resp = await client.get("/api/history/continue-watching", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_continue_watching_limit(self, client, auth_headers, db, test_user):
        for i in range(5):
            await db.tblWatchHistory.insert_one({
                "_id": ObjectId(),
                "user_id": test_user["_id"],
                "content_type": "movie",
                "tmdb_id": 1000 + i,
                "progress_seconds": 600 + i,
                "completed": False,
                "last_watched_at": f"2025-01-{15+i:02d}T10:00:00Z",
            })
        resp = await client.get("/api/history/continue-watching?limit=2", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_continue_watching_no_auth(self, client):
        resp = await client.get("/api/history/continue-watching")
        assert resp.status_code == 401


# ── Get History ───────────────────────────────────────────────────────────

class TestGetHistory:
    async def test_empty_history(self, client, auth_headers):
        resp = await client.get("/api/history/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_history_with_data(self, client, auth_headers, db, test_user):
        for i in range(3):
            await db.tblWatchHistory.insert_one({
                "_id": ObjectId(),
                "user_id": test_user["_id"],
                "content_type": "movie",
                "tmdb_id": 1000 + i,
                "progress_seconds": 600 * (i + 1),
                "completed": i == 2,
                "last_watched_at": f"2025-01-{15+i:02d}T10:00:00Z",
                "created_at": f"2025-01-{10+i:02d}T10:00:00Z",
            })

        resp = await client.get("/api/history/", headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 3
        # Should be sorted by last_watched_at desc
        assert items[0]["tmdb_id"] == 1002

    async def test_history_filter_by_content_type(self, client, auth_headers, db, test_user):
        await db.tblWatchHistory.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["_id"],
            "content_type": "movie",
            "tmdb_id": 550,
            "progress_seconds": 600,
            "completed": False,
            "last_watched_at": "2025-01-15T10:00:00Z",
        })
        await db.tblWatchHistory.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["_id"],
            "content_type": "series",
            "tmdb_id": 1399,
            "progress_seconds": 300,
            "completed": False,
            "last_watched_at": "2025-01-16T10:00:00Z",
        })

        resp = await client.get("/api/history/?content_type=movie", headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["content_type"] == "movie"

    async def test_history_pagination(self, client, auth_headers, db, test_user):
        for i in range(5):
            await db.tblWatchHistory.insert_one({
                "_id": ObjectId(),
                "user_id": test_user["_id"],
                "content_type": "movie",
                "tmdb_id": 1000 + i,
                "progress_seconds": 600,
                "last_watched_at": f"2025-01-{15+i:02d}T10:00:00Z",
            })

        resp = await client.get("/api/history/?page=1&limit=2", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

        resp2 = await client.get("/api/history/?page=2&limit=2", headers=auth_headers)
        assert resp2.status_code == 200
        assert len(resp2.json()) == 2

    async def test_history_no_auth(self, client):
        resp = await client.get("/api/history/")
        assert resp.status_code == 401


# ── Update Progress ───────────────────────────────────────────────────────

class TestUpdateProgress:
    async def test_update_progress_accepted(self, client, auth_headers):
        resp = await client.post(
            "/api/history/progress",
            json={
                "content_type": "movie",
                "tmdb_id": 550,
                "progress_seconds": 1200,
                "completed": False,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 202
        assert resp.json()["status"] == "accepted"

    async def test_update_progress_series(self, client, auth_headers):
        resp = await client.post(
            "/api/history/progress",
            json={
                "content_type": "series",
                "tmdb_id": 1399,
                "season_number": 1,
                "episode_number": 5,
                "progress_seconds": 900,
                "completed": False,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 202

    async def test_update_progress_completed(self, client, auth_headers):
        resp = await client.post(
            "/api/history/progress",
            json={
                "content_type": "movie",
                "tmdb_id": 550,
                "progress_seconds": 5400,
                "completed": True,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 202

    async def test_update_progress_no_auth(self, client):
        resp = await client.post(
            "/api/history/progress",
            json={"content_type": "movie", "tmdb_id": 550, "progress_seconds": 600},
        )
        assert resp.status_code == 401

    async def test_update_progress_missing_fields(self, client, auth_headers):
        resp = await client.post(
            "/api/history/progress",
            json={"content_type": "movie"},  # missing tmdb_id
            headers=auth_headers,
        )
        assert resp.status_code == 422
