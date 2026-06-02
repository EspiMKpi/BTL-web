"""
Tests for libraryService — get_home_rails, get_content_by_genre, get_profile_stats, get_recent_activity.
These test the service layer directly (not through HTTP).
"""

import pytest
from bson import ObjectId

from app.services.libraryService import (
    get_home_rails,
    get_content_by_genre,
    get_profile_stats,
    get_recent_activity,
    _home_cache,
)


# ── get_home_rails ────────────────────────────────────────────────────────

class TestGetHomeRails:
    async def test_empty_db(self, db):
        result = await get_home_rails()
        assert "rails" in result
        assert "genres" in result
        assert len(result["rails"]) >= 6
        # Verify rail IDs
        rail_ids = [r["id"] for r in result["rails"]]
        assert "trending_movies" in rail_ids
        assert "trending_series" in rail_ids
        assert "top_rated_movies" in rail_ids
        assert "top_rated_series" in rail_ids
        assert "new_releases" in rail_ids
        assert "recent_series" in rail_ids

    async def test_rail_structure(self, db):
        result = await get_home_rails()
        for rail in result["rails"]:
            assert "id" in rail
            assert "title" in rail
            assert "content_type" in rail
            assert "items" in rail

    async def test_anonymous_caching(self, db):
        """Anonymous requests should be cached."""
        _home_cache.clear()
        result1 = await get_home_rails(user_id=None)
        cache_key = "home:anon:10"
        assert cache_key in _home_cache
        result2 = await get_home_rails(user_id=None)
        assert result1 == result2  # same cached result

    async def test_authenticated_not_cached(self, db):
        """Authenticated requests should NOT be cached."""
        _home_cache.clear()
        await get_home_rails(user_id="user123")
        # No cache entry for authenticated users
        assert "home:user123:10" not in _home_cache

    async def test_custom_rail_limit(self, db):
        result = await get_home_rails(rail_limit=5)
        for rail in result["rails"]:
            assert len(rail["items"]) <= 5

    async def test_with_movies_and_series(self, db):
        # Seed data
        for i in range(3):
            await db.tblMovies.insert_one({
                "_id": ObjectId(),
                "tmdb_id": 1000 + i,
                "title": f"Movie {i}",
                "popularity": 100 - i,
                "vote_average": 8.0,
                "vote_count": 200,
                "release_date": f"2025-0{i+1}-01",
                "genres": [],
                "raw_data": {},
            })
            await db.tblSeries.insert_one({
                "_id": ObjectId(),
                "tmdb_id": 2000 + i,
                "name": f"Series {i}",
                "popularity": 90 - i,
                "vote_average": 7.5,
                "vote_count": 150,
                "first_air_date": f"2024-0{i+1}-15",
                "genres": [],
                "raw_data": {},
            })

        result = await get_home_rails()
        trending_movies = next(r for r in result["rails"] if r["id"] == "trending_movies")
        assert len(trending_movies["items"]) == 3
        # ObjectIds should be strings
        for item in trending_movies["items"]:
            assert isinstance(item["_id"], str)

    async def test_continue_watching_authenticated(self, db):
        """Authenticated user with watch history gets continue_watching rail."""
        user_id = str(ObjectId())
        await db.tblMovies.insert_one({
            "_id": ObjectId(),
            "tmdb_id": 550,
            "title": "Fight Club",
            "popularity": 100,
            "vote_average": 8.0,
            "vote_count": 200,
            "genres": [],
            "raw_data": {},
        })
        await db.tblWatchHistory.insert_one({
            "_id": ObjectId(),
            "user_id": user_id,
            "content_type": "movie",
            "tmdb_id": 550,
            "progress_seconds": 1200,
            "completed": False,
            "last_watched_at": "2025-01-15T10:00:00Z",
        })

        result = await get_home_rails(user_id=user_id)
        assert result["rails"][0]["id"] == "continue_watching_movies"
        assert len(result["rails"][0]["items"]) == 1


# ── get_content_by_genre ──────────────────────────────────────────────────

class TestGetContentByGenre:
    async def test_empty_genre(self, db):
        result = await get_content_by_genre(999)
        assert result["movies"] == []
        assert result["series"] == []
        assert result["pagination"]["total_movies"] == 0
        assert result["pagination"]["total_series"] == 0
        assert result["pagination"]["has_more_movies"] is False

    async def test_genre_with_data(self, db):
        for i in range(3):
            await db.tblMovies.insert_one({
                "_id": ObjectId(),
                "tmdb_id": 1000 + i,
                "title": f"Movie {i}",
                "genres": [{"genre_id": 28, "name": "Action"}],
                "popularity": 100 - i,
                "raw_data": {},
            })
            await db.tblSeries.insert_one({
                "_id": ObjectId(),
                "tmdb_id": 2000 + i,
                "name": f"Series {i}",
                "genres": [{"genre_id": 28, "name": "Action"}],
                "popularity": 90 - i,
                "raw_data": {},
            })
            await db.tblMovieGenres.insert_one({"tmdb_id": 1000 + i, "genre_id": 28})
            await db.tblSeriesGenres.insert_one({"tmdb_id": 2000 + i, "genre_id": 28})

        result = await get_content_by_genre(28)
        assert len(result["movies"]) == 3
        assert len(result["series"]) == 3
        assert result["pagination"]["total_movies"] == 3
        assert result["pagination"]["total_series"] == 3

    async def test_genre_pagination(self, db):
        for i in range(5):
            await db.tblMovies.insert_one({
                "_id": ObjectId(),
                "tmdb_id": 1000 + i,
                "title": f"Movie {i}",
                "genres": [{"genre_id": 28, "name": "Action"}],
                "popularity": 100 - i,
                "raw_data": {},
            })
            await db.tblMovieGenres.insert_one({"tmdb_id": 1000 + i, "genre_id": 28})

        result = await get_content_by_genre(28, page=1, limit=2)
        assert len(result["movies"]) == 2
        assert result["pagination"]["total_movies"] == 5
        assert result["pagination"]["has_more_movies"] is True
        assert result["pagination"]["page"] == 1

        result2 = await get_content_by_genre(28, page=3, limit=2)
        assert len(result2["movies"]) == 1


# ── get_profile_stats ─────────────────────────────────────────────────────

class TestGetProfileStats:
    async def test_empty_stats(self, db):
        stats = await get_profile_stats("user123")
        assert stats["watchlist_count"] == 0
        assert stats["completed_count"] == 0
        assert stats["watching_count"] == 0
        assert stats["ratings_count"] == 0
        assert stats["history_count"] == 0
        assert stats["average_rating"] == 0

    async def test_stats_with_data(self, db):
        user_id = "user123"
        await db.tblWatchlistItems.insert_one({"_id": ObjectId(), "user_id": user_id, "status": "watching"})
        await db.tblWatchlistItems.insert_one({"_id": ObjectId(), "user_id": user_id, "status": "completed"})
        await db.tblWatchlistItems.insert_one({"_id": ObjectId(), "user_id": user_id, "status": "completed"})
        await db.tblUserRatings.insert_one({"_id": ObjectId(), "user_id": user_id, "rating": 8.0})
        await db.tblUserRatings.insert_one({"_id": ObjectId(), "user_id": user_id, "rating": 6.0})
        await db.tblWatchHistory.insert_one({"_id": ObjectId(), "user_id": user_id})
        await db.tblWatchHistory.insert_one({"_id": ObjectId(), "user_id": user_id})

        stats = await get_profile_stats(user_id)
        assert stats["watchlist_count"] == 3
        assert stats["completed_count"] == 2
        assert stats["watching_count"] == 1
        assert stats["ratings_count"] == 2
        assert stats["history_count"] == 2
        assert stats["average_rating"] == 7.0


# ── get_recent_activity ───────────────────────────────────────────────────

class TestGetRecentActivity:
    async def test_empty_activity(self, db):
        result = await get_recent_activity("user123")
        assert result["recent_history"] == []
        assert result["recent_ratings"] == []
        assert result["recent_watchlist"] == []

    async def test_activity_with_data(self, db):
        user_id = "user123"
        await db.tblWatchHistory.insert_one({
            "_id": ObjectId(),
            "user_id": user_id,
            "content_type": "movie",
            "tmdb_id": 550,
            "last_watched_at": "2025-01-15T10:00:00Z",
        })
        await db.tblUserRatings.insert_one({
            "_id": ObjectId(),
            "user_id": user_id,
            "content_type": "movie",
            "tmdb_id": 550,
            "rating": 8.0,
            "created_at": "2025-01-15T10:00:00Z",
        })
        await db.tblWatchlistItems.insert_one({
            "_id": ObjectId(),
            "user_id": user_id,
            "content_type": "movie",
            "tmdb_id": 550,
            "updated_at": "2025-01-15T10:00:00Z",
        })

        result = await get_recent_activity(user_id)
        assert len(result["recent_history"]) == 1
        assert len(result["recent_ratings"]) == 1
        assert len(result["recent_watchlist"]) == 1

        # All ObjectIds should be strings
        for doc in result["recent_history"]:
            assert isinstance(doc["_id"], str)
