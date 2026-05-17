"""
Tests for the recommendations router — /api/recommendations/similar/{content_type}/{tmdb_id}.

Pairs trained TF-IDF artifacts (via build_artifacts fixture) with seeded Mongo
docs (via the autouse mock client) and exercises the whole path: validation,
503-when-untrained, hydration, recommender-order preservation, and the
post-training-hidden filter.
"""

from bson import ObjectId


class TestValidation:
    async def test_rejects_unknown_content_type(self, client):
        resp = await client.get("/api/recommendations/similar/music/550")
        assert resp.status_code == 422

    async def test_rejects_tmdb_id_below_one(self, client):
        resp = await client.get("/api/recommendations/similar/movie/0")
        assert resp.status_code == 422

    async def test_rejects_limit_above_ceiling(self, client):
        resp = await client.get("/api/recommendations/similar/movie/1?limit=100")
        assert resp.status_code == 422

    async def test_rejects_limit_below_floor(self, client):
        resp = await client.get("/api/recommendations/similar/movie/1?limit=0")
        assert resp.status_code == 422


class TestNotTrained:
    async def test_503_when_artifacts_missing(self, client, artifact_root):
        # artifact_root is an empty tmp dir — no metadata.json under movies/.
        resp = await client.get("/api/recommendations/similar/movie/1")
        assert resp.status_code == 503
        assert "train_recommender" in resp.json()["detail"]


class TestEmptyResults:
    async def test_unknown_tmdb_id_returns_empty_list(
        self, client, artifact_root, build_artifacts
    ):
        build_artifacts(artifact_root, "movie", [
            (1, "A", "foo bar baz"),
            (2, "B", "foo bar baz"),
        ])
        resp = await client.get("/api/recommendations/similar/movie/99999")
        assert resp.status_code == 200
        assert resp.json() == []


class TestHydration:
    async def test_returns_docs_in_recommender_order(
        self, client, db, artifact_root, build_artifacts
    ):
        await db.movies.insert_many([
            {"_id": ObjectId(), "tmdb_id": 1, "title": "Alpha",
             "popularity": 10, "vote_average": 8, "genres": [], "raw_data": {}},
            {"_id": ObjectId(), "tmdb_id": 2, "title": "Beta",
             "popularity": 9, "vote_average": 7, "genres": [], "raw_data": {}},
            {"_id": ObjectId(), "tmdb_id": 3, "title": "Gamma",
             "popularity": 8, "vote_average": 6, "genres": [], "raw_data": {}},
        ])
        # Item 2 shares 3 tokens with item 1; item 3 shares only 1 → 2 ranks above 3.
        build_artifacts(artifact_root, "movie", [
            (1, "Alpha", "space stars galaxy aliens"),
            (2, "Beta",  "space stars galaxy planets"),
            (3, "Gamma", "space orbit"),
        ])
        resp = await client.get("/api/recommendations/similar/movie/1?limit=5")
        assert resp.status_code == 200
        body = resp.json()
        assert [d["tmdb_id"] for d in body] == [2, 3]
        assert body[0]["title"] == "Beta"

    async def test_series_route_returns_series_docs(
        self, client, db, artifact_root, build_artifacts
    ):
        await db.series.insert_many([
            {"_id": ObjectId(), "tmdb_id": 10, "name": "S Alpha",
             "popularity": 10, "first_air_date": "2020-01-01",
             "vote_average": 8, "genres": [], "raw_data": {}, "seasons": []},
            {"_id": ObjectId(), "tmdb_id": 20, "name": "S Beta",
             "popularity": 9, "first_air_date": "2021-01-01",
             "vote_average": 7, "genres": [], "raw_data": {}, "seasons": []},
        ])
        build_artifacts(artifact_root, "series", [
            (10, "S Alpha", "drama crime murder mystery"),
            (20, "S Beta",  "drama crime murder investigation"),
        ])
        resp = await client.get("/api/recommendations/similar/series/10?limit=5")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["tmdb_id"] == 20
        # Series docs carry `name`, not `title` — verify hydration used db.series.
        assert body[0]["name"] == "S Beta"

    async def test_drops_items_hidden_after_training(
        self, client, db, artifact_root, build_artifacts
    ):
        # Item 2 was in the trained corpus but got is_hidden=True later.
        # It MUST NOT surface even though TF-IDF would rank it high.
        await db.movies.insert_many([
            {"_id": ObjectId(), "tmdb_id": 1, "title": "Alpha",
             "popularity": 10, "vote_average": 8, "genres": [], "raw_data": {}},
            {"_id": ObjectId(), "tmdb_id": 2, "title": "Beta",
             "popularity": 9, "vote_average": 7, "genres": [], "raw_data": {},
             "is_hidden": True},
            {"_id": ObjectId(), "tmdb_id": 3, "title": "Gamma",
             "popularity": 8, "vote_average": 6, "genres": [], "raw_data": {}},
        ])
        build_artifacts(artifact_root, "movie", [
            (1, "Alpha", "space stars galaxy"),
            (2, "Beta",  "space stars galaxy"),
            (3, "Gamma", "space stars galaxy"),
        ])
        resp = await client.get("/api/recommendations/similar/movie/1?limit=5")
        assert resp.status_code == 200
        ids = [d["tmdb_id"] for d in resp.json()]
        assert 2 not in ids
        assert 3 in ids

    async def test_drops_items_no_longer_in_mongo(
        self, client, db, artifact_root, build_artifacts
    ):
        # Trained on 3 items but Mongo only has item 1 + item 3. Item 2 silently
        # dropped during the by_id reshape.
        await db.movies.insert_many([
            {"_id": ObjectId(), "tmdb_id": 1, "title": "Alpha",
             "popularity": 10, "vote_average": 8, "genres": [], "raw_data": {}},
            {"_id": ObjectId(), "tmdb_id": 3, "title": "Gamma",
             "popularity": 8, "vote_average": 6, "genres": [], "raw_data": {}},
        ])
        build_artifacts(artifact_root, "movie", [
            (1, "Alpha", "space stars galaxy"),
            (2, "Beta",  "space stars galaxy"),
            (3, "Gamma", "space stars galaxy"),
        ])
        resp = await client.get("/api/recommendations/similar/movie/1?limit=5")
        assert resp.status_code == 200
        ids = [d["tmdb_id"] for d in resp.json()]
        assert ids == [3]
