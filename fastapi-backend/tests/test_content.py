"""
Tests for content router — home, genres, browse, search, movie detail, series detail.
"""

import pytest
from bson import ObjectId


# ── Helpers ───────────────────────────────────────────────────────────────

async def _seed_movies(db, count=3):
    """Insert sample movies into the mock DB."""
    docs = []
    for i in range(count):
        doc = {
            "_id": ObjectId(),
            "tmdb_id": 1000 + i,
            "title": f"Movie {i}",
            "overview": f"Overview for movie {i}",
            "poster_path": f"/poster_{i}.jpg",
            "backdrop_path": f"/backdrop_{i}.jpg",
            "release_date": f"2025-0{i+1}-01",
            "popularity": 100 - i,
            "vote_average": 8.0 - i * 0.5,
            "vote_count": 200 - i * 30,
            "genres": [{"genre_id": 28, "name": "Action"}],
            "cast": [],
            "crew": [],
            "raw_data": {"id": 1000 + i},
        }
        await db.movies.insert_one(doc)
        docs.append(doc)
    return docs


async def _seed_series(db, count=3):
    """Insert sample series into the mock DB."""
    docs = []
    for i in range(count):
        doc = {
            "_id": ObjectId(),
            "tmdb_id": 2000 + i,
            "name": f"Series {i}",
            "overview": f"Overview for series {i}",
            "poster_path": f"/series_poster_{i}.jpg",
            "backdrop_path": f"/series_backdrop_{i}.jpg",
            "first_air_date": f"2024-0{i+1}-15",
            "popularity": 90 - i,
            "vote_average": 7.5 - i * 0.3,
            "vote_count": 150 - i * 20,
            "genres": [{"genre_id": 18, "name": "Drama"}],
            "cast": [],
            "crew": [],
            "seasons": [{"season_number": 1, "name": "Season 1", "episodes": [], "episode_count": 0}],
            "raw_data": {"id": 2000 + i},
        }
        await db.series.insert_one(doc)
        docs.append(doc)
    return docs


async def _seed_genres(db):
    """Insert sample genres."""
    genres = [
        {"_id": ObjectId(), "genre_id": 28, "name": "Action"},
        {"_id": ObjectId(), "genre_id": 18, "name": "Drama"},
        {"_id": ObjectId(), "genre_id": 35, "name": "Comedy"},
    ]
    for g in genres:
        await db.genres.insert_one(g)
    return genres


# ── Home Rails ────────────────────────────────────────────────────────────

class TestHomeRails:
    async def test_home_empty_db(self, client):
        resp = await client.get("/api/content/home")
        assert resp.status_code == 200
        body = resp.json()
        assert "rails" in body
        assert "genres" in body
        assert isinstance(body["rails"], list)
        assert len(body["rails"]) >= 6  # at least 6 default rails

    async def test_home_with_data(self, client, db):
        from app.services.library_service import _home_cache
        _home_cache.clear()
        await _seed_movies(db, 3)
        await _seed_series(db, 3)
        await _seed_genres(db)
        resp = await client.get("/api/content/home")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["rails"]) >= 6
        # Check trending movies rail has items
        trending = next(r for r in body["rails"] if r["id"] == "trending_movies")
        assert len(trending["items"]) == 3
        assert len(body["genres"]) == 3

    async def test_home_with_custom_limit(self, client, db):
        await _seed_movies(db, 5)
        resp = await client.get("/api/content/home?limit=2")
        assert resp.status_code == 200
        trending = next(r for r in resp.json()["rails"] if r["id"] == "trending_movies")
        assert len(trending["items"]) == 2

    async def test_home_limit_too_high(self, client):
        resp = await client.get("/api/content/home?limit=100")
        assert resp.status_code == 422  # max is 50

    async def test_home_authenticated_with_continue_watching(self, client, db, test_user, auth_headers):
        await _seed_movies(db, 2)
        # Seed watch history
        await db.watch_history.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["_id"],
            "content_type": "movie",
            "tmdb_id": 1000,
            "progress_seconds": 1200,
            "completed": False,
            "last_watched_at": "2025-01-01T00:00:00Z",
        })
        resp = await client.get("/api/content/home", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        # Should have continue_watching_movies as first rail (seeded entry is a movie)
        assert body["rails"][0]["id"] == "continue_watching_movies"
        assert len(body["rails"][0]["items"]) == 1


# ── Genres ────────────────────────────────────────────────────────────────

class TestGenres:
    async def test_list_genres_empty(self, client):
        resp = await client.get("/api/content/genres")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_genres_with_data(self, client, db):
        await _seed_genres(db)
        resp = await client.get("/api/content/genres")
        assert resp.status_code == 200
        genres = resp.json()
        assert len(genres) == 3
        # Should be sorted by name
        names = [g["name"] for g in genres]
        assert names == sorted(names)
        # All should have string _id
        for g in genres:
            assert isinstance(g["_id"], str)


# ── Browse by Genre ───────────────────────────────────────────────────────

class TestBrowseGenre:
    async def test_browse_empty(self, client):
        resp = await client.get("/api/content/browse/28")
        assert resp.status_code == 200
        body = resp.json()
        assert body["movies"] == []
        assert body["series"] == []
        assert body["pagination"]["total_movies"] == 0
        assert body["pagination"]["total_series"] == 0

    async def test_browse_with_data(self, client, db):
        await _seed_movies(db, 5)
        await _seed_series(db, 3)
        resp = await client.get("/api/content/browse/28")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["movies"]) == 5  # all have genre_id 28
        assert len(body["series"]) == 0  # series have genre_id 18

    async def test_browse_pagination(self, client, db):
        await _seed_movies(db, 5)
        resp = await client.get("/api/content/browse/28?page=1&limit=2")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["movies"]) == 2
        assert body["pagination"]["page"] == 1
        assert body["pagination"]["total_movies"] == 5
        assert body["pagination"]["has_more_movies"] is True

    async def test_browse_page_2(self, client, db):
        await _seed_movies(db, 5)
        resp = await client.get("/api/content/browse/28?page=3&limit=2")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["movies"]) == 1  # 5 items, page 3 of size 2 = 1 item
        assert body["pagination"]["page"] == 3

    async def test_browse_invalid_page(self, client):
        resp = await client.get("/api/content/browse/28?page=0")
        assert resp.status_code == 422


# ── Search ────────────────────────────────────────────────────────────────

class TestSearch:
    async def test_search_requires_query(self, client):
        resp = await client.get("/api/content/search")
        assert resp.status_code == 422  # q is required

    async def test_search_empty_query(self, client):
        resp = await client.get("/api/content/search?q=")
        assert resp.status_code == 422  # min_length=1

    @pytest.mark.skip(reason="mongomock does not support $text operator")
    async def test_search_no_results(self, client, db):
        resp = await client.get("/api/content/search?q=nonexistent")
        assert resp.status_code == 200
        body = resp.json()
        assert body["results"] == []
        assert body["page"] == 1
        assert body["total"] == 0

    @pytest.mark.skip(reason="mongomock does not support $text operator")
    async def test_search_pagination_params(self, client, db):
        resp = await client.get("/api/content/search?q=test&page=1&limit=5")
        assert resp.status_code == 200
        body = resp.json()
        assert body["page"] == 1
        assert body["limit"] == 5


# ── Movie Detail ──────────────────────────────────────────────────────────

class TestMovieDetail:
    async def test_movie_in_db(self, client, db):
        movies = await _seed_movies(db, 1)
        movie = movies[0]
        resp = await client.get(f"/api/content/movie/{movie['tmdb_id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["tmdb_id"] == movie["tmdb_id"]
        assert body["title"] == movie["title"]
        assert isinstance(body["_id"], str)

    async def test_movie_not_found(self, client, db):
        # Movie not in DB and TMDB will fail — expect 404
        resp = await client.get("/api/content/movie/9999999")
        assert resp.status_code == 404


# ── Series Detail ─────────────────────────────────────────────────────────

class TestSeriesDetail:
    async def test_series_in_db(self, client, db):
        series_list = await _seed_series(db, 1)
        series = series_list[0]
        resp = await client.get(f"/api/content/series/{series['tmdb_id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["tmdb_id"] == series["tmdb_id"]
        assert body["name"] == series["name"]
        assert isinstance(body["_id"], str)

    async def test_series_not_found(self, client, db):
        resp = await client.get("/api/content/series/9999999")
        assert resp.status_code == 404
