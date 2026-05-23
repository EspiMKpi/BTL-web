"""
Tests for the FP-Growth recommender (inference layer + /related route).

We exercise the inference module directly with hand-built rules.json, and the
HTTP route via mongomock-seeded movies/series collections. Training itself
isn't unit-tested — that's a script wrapping a third-party library.
"""

import json

import pytest
from bson import ObjectId

from app.services import recommendation_service as rs


# ── Inference layer ───────────────────────────────────────────────────────

class TestRelatedItems:
    def test_returns_consequents_in_order(self, fpgrowth_artifact_root, build_fpgrowth_artifacts):
        build_fpgrowth_artifacts(fpgrowth_artifact_root, "movie", {
            550: [101, 102, 103, 104],
            101: [550, 102],
        })
        out = rs.related_items("movie", 550, top_n=3)
        assert out == [101, 102, 103]

    def test_caps_to_top_n(self, fpgrowth_artifact_root, build_fpgrowth_artifacts):
        build_fpgrowth_artifacts(fpgrowth_artifact_root, "movie", {
            550: list(range(1, 21)),
        })
        out = rs.related_items("movie", 550, top_n=5)
        assert out == [1, 2, 3, 4, 5]

    def test_cold_start_item_returns_empty(self, fpgrowth_artifact_root, build_fpgrowth_artifacts):
        build_fpgrowth_artifacts(fpgrowth_artifact_root, "movie", {550: [101]})
        # 9999 wasn't in any rule
        out = rs.related_items("movie", 9999, top_n=10)
        assert out == []

    def test_unknown_content_type_raises(self):
        with pytest.raises(ValueError):
            rs.related_items("audio", 1)

    def test_missing_artifact_raises(self, fpgrowth_artifact_root):
        with pytest.raises(rs.RecommenderNotTrained):
            rs.related_items("movie", 1)

    def test_kind_mismatch_raises(self, fpgrowth_artifact_root, build_fpgrowth_artifacts):
        build_fpgrowth_artifacts(fpgrowth_artifact_root, "movie", {550: [101]},
                                 kind="something_else_v999")
        with pytest.raises(RuntimeError, match="Artifact kind mismatch"):
            rs.related_items("movie", 550)

    def test_lazy_load_then_cached(
        self, fpgrowth_artifact_root, build_fpgrowth_artifacts, monkeypatch,
    ):
        build_fpgrowth_artifacts(fpgrowth_artifact_root, "movie", {550: [101, 102]})
        # First call triggers load
        assert rs.related_items("movie", 550, top_n=2) == [101, 102]
        # Subsequent calls hit the in-memory cache — make the file unreadable
        # to prove we don't re-read it.
        (fpgrowth_artifact_root / "movies" / "rules.json").write_text("not json")
        # Cached call still works
        assert rs.related_items("movie", 550, top_n=2) == [101, 102]

    def test_reload_drops_cache(self, fpgrowth_artifact_root, build_fpgrowth_artifacts):
        build_fpgrowth_artifacts(fpgrowth_artifact_root, "movie", {550: [101]})
        assert rs.related_items("movie", 550, top_n=1) == [101]
        # Update artifact in place
        build_fpgrowth_artifacts(fpgrowth_artifact_root, "movie", {550: [202]})
        rs.reload("movie")
        assert rs.related_items("movie", 550, top_n=1) == [202]


# ── HTTP route ────────────────────────────────────────────────────────────

class TestRelatedRoute:
    async def test_503_when_untrained(self, client, fpgrowth_artifact_root):
        resp = await client.get("/api/recommendations/related/movie/550")
        assert resp.status_code == 503
        assert "FP-Growth" in resp.json()["detail"]

    async def test_unsupported_content_type_returns_422(self, client, fpgrowth_artifact_root):
        resp = await client.get("/api/recommendations/related/podcast/550")
        assert resp.status_code == 422

    async def test_returns_hydrated_docs_in_rule_order(
        self, client, db, fpgrowth_artifact_root, build_fpgrowth_artifacts,
    ):
        # Seed catalog
        for tmdb_id in (550, 101, 102, 103):
            await db.movies.insert_one({
                "_id": ObjectId(),
                "tmdb_id": tmdb_id,
                "title": f"Movie {tmdb_id}",
                "popularity": 50,
                "genres": [],
                "raw_data": {},
            })
        build_fpgrowth_artifacts(fpgrowth_artifact_root, "movie", {
            550: [101, 102, 103],
        })

        resp = await client.get("/api/recommendations/related/movie/550?limit=10")
        assert resp.status_code == 200
        ids = [item["tmdb_id"] for item in resp.json()]
        assert ids == [101, 102, 103]

    async def test_hidden_titles_dropped_silently(
        self, client, db, fpgrowth_artifact_root, build_fpgrowth_artifacts,
    ):
        # 101 is hidden, 102 + 103 are visible
        await db.movies.insert_one({"_id": ObjectId(), "tmdb_id": 550, "title": "X", "genres": []})
        await db.movies.insert_one({"_id": ObjectId(), "tmdb_id": 101, "title": "Hidden",
                                     "is_hidden": True, "genres": []})
        await db.movies.insert_one({"_id": ObjectId(), "tmdb_id": 102, "title": "Vis", "genres": []})
        await db.movies.insert_one({"_id": ObjectId(), "tmdb_id": 103, "title": "Vis", "genres": []})

        build_fpgrowth_artifacts(fpgrowth_artifact_root, "movie", {
            550: [101, 102, 103],
        })

        resp = await client.get("/api/recommendations/related/movie/550")
        ids = [item["tmdb_id"] for item in resp.json()]
        assert ids == [102, 103]  # 101 filtered, order preserved

    async def test_cold_start_item_returns_empty_list(
        self, client, fpgrowth_artifact_root, build_fpgrowth_artifacts,
    ):
        build_fpgrowth_artifacts(fpgrowth_artifact_root, "movie", {550: [101]})
        resp = await client.get("/api/recommendations/related/movie/9999")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_invalid_tmdb_id_returns_422(self, client, fpgrowth_artifact_root, build_fpgrowth_artifacts):
        build_fpgrowth_artifacts(fpgrowth_artifact_root, "movie", {550: [101]})
        resp = await client.get("/api/recommendations/related/movie/0")
        assert resp.status_code == 422  # ge=1 constraint

    async def test_route_does_not_require_auth(
        self, client, db, fpgrowth_artifact_root, build_fpgrowth_artifacts,
    ):
        # Public — no Authorization header. Should still return 200.
        await db.movies.insert_one({"_id": ObjectId(), "tmdb_id": 550, "title": "X", "genres": []})
        await db.movies.insert_one({"_id": ObjectId(), "tmdb_id": 101, "title": "Y", "genres": []})
        build_fpgrowth_artifacts(fpgrowth_artifact_root, "movie", {550: [101]})

        resp = await client.get("/api/recommendations/related/movie/550")
        assert resp.status_code == 200
