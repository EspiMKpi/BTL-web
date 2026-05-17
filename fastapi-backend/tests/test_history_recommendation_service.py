"""
Tests for history_recommendation_service — per-user "Recommended For You".

Combines the `artifact_root` + `build_artifacts` fixtures (TF-IDF model in tmp)
with `db` (mongomock) for the user's watch_history + watchlist_items.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.services import history_recommendation_service as hrs
from app.services import recommendation_service as rs


async def _add_history(
    db, user_id, content_type, tmdb_id, *,
    completed=False, progress_seconds=0, last_watched_at=None,
):
    await db.watch_history.insert_one({
        "user_id": user_id,
        "content_type": content_type,
        "tmdb_id": tmdb_id,
        "completed": completed,
        "progress_seconds": progress_seconds,
        "last_watched_at": last_watched_at or datetime.now(timezone.utc),
    })


async def _add_watchlist(
    db, user_id, content_type, tmdb_id, *,
    status="plan_to_watch", is_favorite=False,
):
    await db.watchlist_items.insert_one({
        "user_id": user_id,
        "content_type": content_type,
        "tmdb_id": tmdb_id,
        "status": status,
        "is_favorite": is_favorite,
    })


class TestColdStart:
    async def test_no_signals_returns_empty(self, db, artifact_root, build_artifacts):
        build_artifacts(artifact_root, "movie", [
            (1, "A", "alpha beta"), (2, "B", "alpha gamma"), (3, "C", "delta epsilon"),
        ])
        assert await hrs.for_user("u1", "movie") == []

    async def test_below_threshold_returns_empty(self, db, artifact_root, build_artifacts):
        build_artifacts(artifact_root, "movie", [
            (1, "A", "alpha beta gamma"), (2, "B", "alpha beta gamma"),
            (3, "C", "alpha beta gamma"), (4, "D", "alpha beta gamma"),
        ])
        # Two seeds — below MIN_SEEDS_FOR_RECS=3.
        await _add_history(db, "u1", "movie", 1, completed=True)
        await _add_history(db, "u1", "movie", 2, completed=True)
        assert await hrs.for_user("u1", "movie") == []

    async def test_at_threshold_produces_recommendations(self, db, artifact_root, build_artifacts):
        build_artifacts(artifact_root, "movie", [
            (1, "A", "alpha beta gamma"), (2, "B", "alpha beta gamma"),
            (3, "C", "alpha beta gamma"), (4, "D", "alpha beta gamma"),
        ])
        await _add_history(db, "u1", "movie", 1, completed=True)
        await _add_history(db, "u1", "movie", 2, completed=True)
        await _add_history(db, "u1", "movie", 3, completed=True)
        result = await hrs.for_user("u1", "movie")
        # Only unseen item is 4; seeds themselves must be excluded from output.
        assert result == [4]


class TestPositiveSignals:
    async def test_completed_seeds_drive_recommendations(self, db, artifact_root, build_artifacts):
        build_artifacts(artifact_root, "movie", [
            (1, "A", "alpha beta"),
            (2, "B", "alpha gamma"),
            (3, "C", "alpha delta"),
            (4, "D", "alpha epsilon"),   # shares "alpha" with all seeds
            (5, "E", "unrelated cooking pasta"),  # zero overlap with seeds
        ])
        await _add_history(db, "u1", "movie", 1, completed=True)
        await _add_history(db, "u1", "movie", 2, completed=True)
        await _add_history(db, "u1", "movie", 3, completed=True)
        result = await hrs.for_user("u1", "movie")
        assert result == [4]

    async def test_long_progress_counts_as_positive(self, db, artifact_root, build_artifacts):
        build_artifacts(artifact_root, "movie", [
            (1, "A", "alpha beta gamma"), (2, "B", "alpha beta gamma"),
            (3, "C", "alpha beta gamma"), (4, "D", "alpha beta gamma"),
        ])
        # Not completed, but progress_seconds >= MIN_PROGRESS_SECONDS (1800)
        await _add_history(db, "u1", "movie", 1, progress_seconds=2000)
        await _add_history(db, "u1", "movie", 2, progress_seconds=2000)
        await _add_history(db, "u1", "movie", 3, progress_seconds=2000)
        assert await hrs.for_user("u1", "movie") == [4]

    async def test_favorites_alone_drive_recommendations(self, db, artifact_root, build_artifacts):
        build_artifacts(artifact_root, "movie", [
            (1, "A", "alpha beta gamma"), (2, "B", "alpha beta gamma"),
            (3, "C", "alpha beta gamma"), (4, "D", "alpha beta gamma"),
        ])
        # No history — favorites only.
        await _add_watchlist(db, "u1", "movie", 1, is_favorite=True)
        await _add_watchlist(db, "u1", "movie", 2, is_favorite=True)
        await _add_watchlist(db, "u1", "movie", 3, is_favorite=True)
        assert await hrs.for_user("u1", "movie") == [4]


class TestNegativeFilters:
    async def test_short_progress_ignored(self, db, artifact_root, build_artifacts):
        build_artifacts(artifact_root, "movie", [
            (1, "A", "alpha beta"), (2, "B", "alpha beta"),
            (3, "C", "alpha beta"), (4, "D", "alpha beta"),
        ])
        # All below MIN_PROGRESS_SECONDS — must not seed.
        await _add_history(db, "u1", "movie", 1, progress_seconds=500)
        await _add_history(db, "u1", "movie", 2, progress_seconds=500)
        await _add_history(db, "u1", "movie", 3, progress_seconds=500)
        assert await hrs.for_user("u1", "movie") == []

    async def test_seen_history_items_never_recommended(self, db, artifact_root, build_artifacts):
        build_artifacts(artifact_root, "movie", [
            (1, "A", "alpha beta"), (2, "B", "alpha beta"), (3, "C", "alpha beta"),
            (4, "D", "alpha beta"),    # touched but not a seed
            (5, "E", "alpha beta"),    # the only true candidate
        ])
        await _add_history(db, "u1", "movie", 1, completed=True)
        await _add_history(db, "u1", "movie", 2, completed=True)
        await _add_history(db, "u1", "movie", 3, completed=True)
        # 4 sits in history with low progress — not a seed, but in seen-set.
        await _add_history(db, "u1", "movie", 4, progress_seconds=100)
        result = await hrs.for_user("u1", "movie")
        assert 4 not in result
        assert 5 in result

    async def test_plan_to_watch_items_never_recommended(self, db, artifact_root, build_artifacts):
        build_artifacts(artifact_root, "movie", [
            (1, "A", "alpha beta"), (2, "B", "alpha beta"), (3, "C", "alpha beta"),
            (4, "D", "alpha beta"),    # bookmarked plan_to_watch
            (5, "E", "alpha beta"),    # candidate
        ])
        await _add_history(db, "u1", "movie", 1, completed=True)
        await _add_history(db, "u1", "movie", 2, completed=True)
        await _add_history(db, "u1", "movie", 3, completed=True)
        await _add_watchlist(db, "u1", "movie", 4, status="plan_to_watch")
        result = await hrs.for_user("u1", "movie")
        assert 4 not in result
        assert 5 in result


class TestRecency:
    async def test_recent_seed_outranks_old_seed(self, db, artifact_root, build_artifacts):
        # Two seed neighbourhoods. Item 10 is closest to the recent seed,
        # item 20 is closest to the old seed. After recency decay, 10 must rank
        # above 20.
        build_artifacts(artifact_root, "movie", [
            (1,  "Recent", "alpha"),
            (2,  "Old",    "gamma"),
            (3,  "Filler", "isolated unique stuff"),  # 3rd seed, no neighbours
            (10, "NearA",  "alpha"),
            (20, "NearB",  "gamma"),
        ])
        now = datetime.now(timezone.utc)
        await _add_history(db, "u1", "movie", 1, completed=True, last_watched_at=now)
        await _add_history(
            db, "u1", "movie", 2, completed=True,
            last_watched_at=now - timedelta(days=365),
        )
        await _add_history(db, "u1", "movie", 3, completed=True, last_watched_at=now)
        result = await hrs.for_user("u1", "movie")
        assert 10 in result and 20 in result
        assert result.index(10) < result.index(20)


class TestContentTypeIsolation:
    async def test_movie_seeds_do_not_recommend_series(
        self, db, artifact_root, build_artifacts,
    ):
        build_artifacts(artifact_root, "movie", [
            (1, "M", "alpha beta"), (2, "M", "alpha beta"),
            (3, "M", "alpha beta"), (4, "M", "alpha beta"),
        ])
        build_artifacts(artifact_root, "series", [
            (10, "S", "alpha beta"), (20, "S", "alpha beta"),
            (30, "S", "alpha beta"), (40, "S", "alpha beta"),
        ])
        # Movie history only — no series seeds.
        await _add_history(db, "u1", "movie", 1, completed=True)
        await _add_history(db, "u1", "movie", 2, completed=True)
        await _add_history(db, "u1", "movie", 3, completed=True)
        assert await hrs.for_user("u1", "series") == []
        assert await hrs.for_user("u1", "movie") == [4]

    async def test_rejects_unknown_content_type(self, db, artifact_root):
        with pytest.raises(ValueError, match="unsupported content_type"):
            await hrs.for_user("u1", "music")


class TestPropagation:
    async def test_propagates_recommender_not_trained(self, db, artifact_root):
        # No build_artifacts call → tmp ARTIFACT_ROOT is empty.
        # Three seeds clear the cold-start gate so similar_to() is actually called.
        await _add_history(db, "u1", "movie", 1, completed=True)
        await _add_history(db, "u1", "movie", 2, completed=True)
        await _add_history(db, "u1", "movie", 3, completed=True)
        with pytest.raises(rs.RecommenderNotTrained):
            await hrs.for_user("u1", "movie")

    async def test_user_isolation(self, db, artifact_root, build_artifacts):
        build_artifacts(artifact_root, "movie", [
            (1, "A", "alpha beta"), (2, "B", "alpha beta"),
            (3, "C", "alpha beta"), (4, "D", "alpha beta"),
        ])
        # u1 has seeds; u2 has none.
        await _add_history(db, "u1", "movie", 1, completed=True)
        await _add_history(db, "u1", "movie", 2, completed=True)
        await _add_history(db, "u1", "movie", 3, completed=True)
        assert await hrs.for_user("u1", "movie") == [4]
        assert await hrs.for_user("u2", "movie") == []


class TestLimit:
    async def test_respects_n_limit(self, db, artifact_root, build_artifacts):
        # 3 seeds, 5 candidates — limit to 2.
        build_artifacts(artifact_root, "movie", [
            (1, "S1", "alpha beta"), (2, "S2", "alpha beta"), (3, "S3", "alpha beta"),
            (4, "C1", "alpha beta"), (5, "C2", "alpha beta"),
            (6, "C3", "alpha beta"), (7, "C4", "alpha beta"), (8, "C5", "alpha beta"),
        ])
        await _add_history(db, "u1", "movie", 1, completed=True)
        await _add_history(db, "u1", "movie", 2, completed=True)
        await _add_history(db, "u1", "movie", 3, completed=True)
        result = await hrs.for_user("u1", "movie", n=2)
        assert len(result) == 2
