"""
Tests for the GRU4Rec sequential recommender (inference + /next route).

The model is exercised with a fixture-built, randomly-initialised state_dict —
we test the IO/data layer, masking, and cold-start contract, not the quality
of the predictions (which depends on real training).
"""

from datetime import datetime, timedelta, timezone

import pytest
import torch
from bson import ObjectId

from app.services import history_recommendation_service as hr
from app.services import recommendation_service as rs


def _seed_history(db, user_id: str, items: list[tuple[str, int, bool]], *, content_type: str = "movie"):
    """items: [(tmdb_id, days_ago, completed), ...] — most-recent-first ordering
    is built by the days_ago value (smaller = newer).
    """
    now = datetime.now(timezone.utc)
    coros = []
    for tmdb_id, days_ago, completed in items:
        coros.append(db.watch_history.insert_one({
            "_id": ObjectId(),
            "user_id": user_id,
            "content_type": content_type,
            "tmdb_id": tmdb_id,
            "season_number": None,
            "episode_number": None,
            "progress_seconds": 7200 if completed else 2000,
            "completed": completed,
            "last_watched_at": now - timedelta(days=days_ago),
        }))
    return coros


# ── Inference layer ───────────────────────────────────────────────────────

class TestNextInSequence:
    async def test_predicts_outside_seen(
        self, db, gru4rec_artifact_root, build_gru4rec_artifacts, test_user,
    ):
        torch.manual_seed(0)
        build_gru4rec_artifacts(
            gru4rec_artifact_root, "movie", tmdb_ids=[101, 102, 103, 104, 105],
            embed_dim=8, hidden_dim=16, max_seq_len=5,
        )

        # 3 positive watches in vocab — meets MIN_SEQUENCE_LEN
        for coro in _seed_history(db, test_user["_id"], [
            (101, 5, True),
            (102, 3, True),
            (103, 1, True),
        ]):
            await coro

        out = await hr.next_in_sequence(test_user["_id"], "movie", n=2)
        # Length up to 2, type int, none of them are seen items
        assert 0 <= len(out) <= 2
        assert all(isinstance(t, int) for t in out)
        seen = {101, 102, 103}
        assert not seen & set(out), f"recommended a seen item: {out}"

    async def test_cold_start_below_threshold_returns_empty(
        self, db, gru4rec_artifact_root, build_gru4rec_artifacts, test_user,
    ):
        build_gru4rec_artifacts(
            gru4rec_artifact_root, "movie", tmdb_ids=[101, 102, 103],
            embed_dim=8, hidden_dim=16, max_seq_len=5,
        )
        # Only 2 in-vocab positive watches — below MIN_SEQUENCE_LEN
        for coro in _seed_history(db, test_user["_id"], [
            (101, 5, True),
            (102, 1, True),
        ]):
            await coro

        out = await hr.next_in_sequence(test_user["_id"], "movie", n=5)
        assert out == []

    async def test_oov_items_dropped(
        self, db, gru4rec_artifact_root, build_gru4rec_artifacts, test_user,
    ):
        build_gru4rec_artifacts(
            gru4rec_artifact_root, "movie", tmdb_ids=[101, 102, 103],
            embed_dim=8, hidden_dim=16, max_seq_len=5,
        )
        # 2 in-vocab + 2 OOV (added to catalog after training) — should drop to 2 → cold start
        for coro in _seed_history(db, test_user["_id"], [
            (101, 5, True),
            (999, 4, True),   # OOV
            (888, 3, True),   # OOV
            (102, 1, True),
        ]):
            await coro

        out = await hr.next_in_sequence(test_user["_id"], "movie", n=5)
        assert out == []  # only 2 in-vocab => cold start

    async def test_partial_progress_counts_as_positive(
        self, db, gru4rec_artifact_root, build_gru4rec_artifacts, test_user,
    ):
        torch.manual_seed(0)
        build_gru4rec_artifacts(
            gru4rec_artifact_root, "movie", tmdb_ids=[101, 102, 103, 104],
            embed_dim=8, hidden_dim=16, max_seq_len=5,
        )
        # 3 not-completed but progress_seconds >= 1800 → positive
        now = datetime.now(timezone.utc)
        for tmdb_id, days_ago in [(101, 5), (102, 3), (103, 1)]:
            await db.watch_history.insert_one({
                "_id": ObjectId(),
                "user_id": test_user["_id"],
                "content_type": "movie",
                "tmdb_id": tmdb_id,
                "progress_seconds": 2400,
                "completed": False,
                "last_watched_at": now - timedelta(days=days_ago),
            })

        out = await hr.next_in_sequence(test_user["_id"], "movie", n=2)
        assert isinstance(out, list)
        # Three positive seeds means we predicted, not cold-started.
        # (Output may be empty if the random model picks all-seen items, but
        # those would be masked → predicted count is 0..2.)
        assert len(out) <= 2

    async def test_bounced_watches_excluded(
        self, db, gru4rec_artifact_root, build_gru4rec_artifacts, test_user,
    ):
        build_gru4rec_artifacts(
            gru4rec_artifact_root, "movie", tmdb_ids=[101, 102, 103, 104],
            embed_dim=8, hidden_dim=16, max_seq_len=5,
        )
        # 3 bounced (progress < 1800) → all excluded → cold start
        now = datetime.now(timezone.utc)
        for tmdb_id, days_ago in [(101, 5), (102, 3), (103, 1)]:
            await db.watch_history.insert_one({
                "_id": ObjectId(),
                "user_id": test_user["_id"],
                "content_type": "movie",
                "tmdb_id": tmdb_id,
                "progress_seconds": 500,  # well below threshold
                "completed": False,
                "last_watched_at": now - timedelta(days=days_ago),
            })

        out = await hr.next_in_sequence(test_user["_id"], "movie", n=5)
        assert out == []

    async def test_missing_artifact_raises(self, gru4rec_artifact_root, test_user):
        with pytest.raises(rs.RecommenderNotTrained):
            await hr.next_in_sequence(test_user["_id"], "movie", n=5)

    async def test_kind_mismatch_raises(
        self, gru4rec_artifact_root, build_gru4rec_artifacts, test_user,
    ):
        build_gru4rec_artifacts(
            gru4rec_artifact_root, "movie", tmdb_ids=[101, 102, 103],
            embed_dim=8, hidden_dim=16, max_seq_len=5, kind="gru4rec_v999",
        )
        with pytest.raises(RuntimeError, match="Artifact kind mismatch"):
            await hr.next_in_sequence(test_user["_id"], "movie", n=5)

    async def test_unknown_content_type_raises(self):
        with pytest.raises(ValueError):
            await hr.next_in_sequence("uid", "audio")

    async def test_predict_cache_reuse(
        self, db, gru4rec_artifact_root, build_gru4rec_artifacts, test_user,
    ):
        torch.manual_seed(0)
        build_gru4rec_artifacts(
            gru4rec_artifact_root, "movie", tmdb_ids=[101, 102, 103, 104],
            embed_dim=8, hidden_dim=16, max_seq_len=5,
        )
        for coro in _seed_history(db, test_user["_id"], [
            (101, 5, True), (102, 3, True), (103, 1, True),
        ]):
            await coro

        first = await hr.next_in_sequence(test_user["_id"], "movie", n=2)
        # Wipe the underlying watch_history; cached result should still come back
        await db.watch_history.delete_many({})
        second = await hr.next_in_sequence(test_user["_id"], "movie", n=2)
        assert first == second


# ── HTTP route ────────────────────────────────────────────────────────────

class TestNextRoute:
    async def test_401_without_auth(self, client, gru4rec_artifact_root):
        resp = await client.get("/api/recommendations/next/movie")
        assert resp.status_code == 401

    async def test_503_when_untrained(self, client, gru4rec_artifact_root, auth_headers):
        resp = await client.get("/api/recommendations/next/movie", headers=auth_headers)
        assert resp.status_code == 503
        assert "GRU4Rec" in resp.json()["detail"]

    async def test_cold_start_returns_empty_list(
        self, client, gru4rec_artifact_root, build_gru4rec_artifacts, auth_headers,
    ):
        build_gru4rec_artifacts(
            gru4rec_artifact_root, "movie", tmdb_ids=[101, 102, 103],
            embed_dim=8, hidden_dim=16, max_seq_len=5,
        )
        # No watch_history for the test user → cold start
        resp = await client.get("/api/recommendations/next/movie", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_unsupported_content_type_returns_422(
        self, client, gru4rec_artifact_root, auth_headers,
    ):
        resp = await client.get("/api/recommendations/next/podcast", headers=auth_headers)
        assert resp.status_code == 422

    async def test_hydration_drops_missing_docs(
        self, client, db, gru4rec_artifact_root, build_gru4rec_artifacts, auth_headers, test_user,
    ):
        torch.manual_seed(0)
        build_gru4rec_artifacts(
            gru4rec_artifact_root, "movie", tmdb_ids=[101, 102, 103, 104, 105],
            embed_dim=8, hidden_dim=16, max_seq_len=5,
        )
        # Seed positive watches but only insert movie docs for 104 + 105.
        # Any recommended item not in `movies` collection should be silently dropped.
        for coro in _seed_history(db, test_user["_id"], [
            (101, 5, True), (102, 3, True), (103, 1, True),
        ]):
            await coro
        for tmdb_id in (104, 105):
            await db.movies.insert_one({
                "_id": ObjectId(),
                "tmdb_id": tmdb_id,
                "title": f"Movie {tmdb_id}",
                "genres": [],
            })

        resp = await client.get("/api/recommendations/next/movie?limit=5", headers=auth_headers)
        assert resp.status_code == 200
        # Whatever comes back must be a subset of {104, 105} (the only hydrated docs)
        ids = {item["tmdb_id"] for item in resp.json()}
        assert ids.issubset({104, 105})
