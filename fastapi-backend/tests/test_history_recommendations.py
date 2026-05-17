"""
Tests for the /api/recommendations/for-you/{content_type} route.

Pairs trained TF-IDF artifacts with seeded watch_history rows for the
authenticated test_user and exercises the full path: auth, validation,
503 when untrained, cold-start, hydration with order, hidden-filter cascade.
"""

from datetime import datetime, timezone

from bson import ObjectId


async def _add_history(db, user_id, tmdb_id, *, content_type="movie", completed=True):
    await db.watch_history.insert_one({
        "user_id": user_id,
        "content_type": content_type,
        "tmdb_id": tmdb_id,
        "completed": completed,
        "progress_seconds": 5000,
        "last_watched_at": datetime.now(timezone.utc),
    })


class TestAuth:
    async def test_401_when_unauthenticated(self, client):
        resp = await client.get("/api/recommendations/for-you/movie")
        assert resp.status_code in (401, 403)  # depends on how get_current_user signals

    async def test_works_with_valid_token(
        self, client, db, auth_headers, test_user, artifact_root, build_artifacts,
    ):
        # Minimal happy path — artifact + 3 seeds + 1 candidate.
        build_artifacts(artifact_root, "movie", [
            (1, "A", "alpha beta"), (2, "B", "alpha beta"),
            (3, "C", "alpha beta"), (4, "D", "alpha beta"),
        ])
        await db.movies.insert_one({
            "_id": ObjectId(), "tmdb_id": 4, "title": "D",
            "popularity": 1, "vote_average": 7, "genres": [], "raw_data": {},
        })
        for tid in (1, 2, 3):
            await _add_history(db, test_user["_id"], tid)
        resp = await client.get(
            "/api/recommendations/for-you/movie", headers=auth_headers,
        )
        assert resp.status_code == 200
        assert [d["tmdb_id"] for d in resp.json()] == [4]


class TestValidation:
    async def test_rejects_unknown_content_type(self, client, auth_headers):
        resp = await client.get(
            "/api/recommendations/for-you/music", headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_rejects_limit_above_ceiling(self, client, auth_headers):
        resp = await client.get(
            "/api/recommendations/for-you/movie?limit=100", headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_rejects_limit_below_floor(self, client, auth_headers):
        resp = await client.get(
            "/api/recommendations/for-you/movie?limit=0", headers=auth_headers,
        )
        assert resp.status_code == 422


class TestNotTrained:
    async def test_503_when_artifacts_missing(
        self, client, db, auth_headers, test_user, artifact_root,
    ):
        # Three seeds so the cold-start gate is cleared and similar_to() runs.
        for tid in (1, 2, 3):
            await _add_history(db, test_user["_id"], tid)
        resp = await client.get(
            "/api/recommendations/for-you/movie", headers=auth_headers,
        )
        assert resp.status_code == 503
        assert "train_recommender" in resp.json()["detail"]


class TestColdStart:
    async def test_no_signals_returns_empty(
        self, client, auth_headers, artifact_root, build_artifacts,
    ):
        build_artifacts(artifact_root, "movie", [
            (1, "A", "alpha beta"), (2, "B", "alpha beta"),
            (3, "C", "alpha beta"), (4, "D", "alpha beta"),
        ])
        resp = await client.get(
            "/api/recommendations/for-you/movie", headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_below_threshold_returns_empty(
        self, client, db, auth_headers, test_user, artifact_root, build_artifacts,
    ):
        build_artifacts(artifact_root, "movie", [
            (1, "A", "alpha beta"), (2, "B", "alpha beta"),
            (3, "C", "alpha beta"), (4, "D", "alpha beta"),
        ])
        await _add_history(db, test_user["_id"], 1)
        await _add_history(db, test_user["_id"], 2)
        resp = await client.get(
            "/api/recommendations/for-you/movie", headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []


class TestHydration:
    async def test_preserves_recommender_order(
        self, client, db, auth_headers, test_user, artifact_root, build_artifacts,
    ):
        # Seed items 1,2,3 share more tokens with item 10 than with item 20.
        build_artifacts(artifact_root, "movie", [
            (1,  "S1", "alpha beta"),
            (2,  "S2", "alpha beta"),
            (3,  "S3", "alpha beta"),
            (10, "Near", "alpha beta"),
            (20, "Far",  "alpha gamma"),
        ])
        await db.movies.insert_many([
            {"_id": ObjectId(), "tmdb_id": 10, "title": "Near",
             "popularity": 5, "vote_average": 8, "genres": [], "raw_data": {}},
            {"_id": ObjectId(), "tmdb_id": 20, "title": "Far",
             "popularity": 4, "vote_average": 7, "genres": [], "raw_data": {}},
        ])
        for tid in (1, 2, 3):
            await _add_history(db, test_user["_id"], tid)
        resp = await client.get(
            "/api/recommendations/for-you/movie", headers=auth_headers,
        )
        assert resp.status_code == 200
        ids = [d["tmdb_id"] for d in resp.json()]
        assert ids[0] == 10
        assert 20 in ids
        assert ids.index(10) < ids.index(20)

    async def test_drops_items_hidden_after_training(
        self, client, db, auth_headers, test_user, artifact_root, build_artifacts,
    ):
        build_artifacts(artifact_root, "movie", [
            (1, "S", "alpha beta"), (2, "S", "alpha beta"), (3, "S", "alpha beta"),
            (4, "Hidden", "alpha beta"),
            (5, "Visible", "alpha beta"),
        ])
        await db.movies.insert_many([
            {"_id": ObjectId(), "tmdb_id": 4, "title": "Hidden",
             "popularity": 1, "vote_average": 7, "genres": [], "raw_data": {},
             "is_hidden": True},
            {"_id": ObjectId(), "tmdb_id": 5, "title": "Visible",
             "popularity": 1, "vote_average": 7, "genres": [], "raw_data": {}},
        ])
        for tid in (1, 2, 3):
            await _add_history(db, test_user["_id"], tid)
        resp = await client.get(
            "/api/recommendations/for-you/movie", headers=auth_headers,
        )
        assert resp.status_code == 200
        ids = [d["tmdb_id"] for d in resp.json()]
        assert 4 not in ids
        assert 5 in ids

    async def test_series_route_returns_series_shape(
        self, client, db, auth_headers, test_user, artifact_root, build_artifacts,
    ):
        build_artifacts(artifact_root, "series", [
            (10, "S", "drama crime"), (20, "S", "drama crime"),
            (30, "S", "drama crime"), (40, "S", "drama crime"),
        ])
        await db.series.insert_one({
            "_id": ObjectId(), "tmdb_id": 40, "name": "Show Forty",
            "popularity": 5, "first_air_date": "2022-01-01",
            "vote_average": 8, "genres": [], "raw_data": {}, "seasons": [],
        })
        for tid in (10, 20, 30):
            await _add_history(db, test_user["_id"], tid, content_type="series")
        resp = await client.get(
            "/api/recommendations/for-you/series", headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        # Series carries `name`, not `title` — confirms hydration hit db.series.
        assert body[0]["tmdb_id"] == 40
        assert body[0]["name"] == "Show Forty"
