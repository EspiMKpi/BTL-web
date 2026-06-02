"""
Tests for admin router — focused on genre visibility (the new feature).
"""

import pytest
from bson import ObjectId

from app.core.security import create_access_token
from app.services.library_service import clear_home_cache


@pytest.fixture(autouse=True)
def _reset_home_cache():
    """Clear the module-level home rails cache between tests."""
    clear_home_cache()
    yield
    clear_home_cache()


@pytest.fixture
async def admin_user(db):
    """Insert an admin and return the doc."""
    user_doc = {
        "_id": ObjectId(),
        "email": "admin@vozflix.com",
        "password": "irrelevant",
        "username": "admin",
        "role": "admin",
        "is_active": True,
    }
    await db.users.insert_one(user_doc)
    user_doc["_id"] = str(user_doc["_id"])
    return user_doc


@pytest.fixture
def admin_headers(admin_user):
    token = create_access_token(admin_user["_id"], admin_user["email"])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def seeded_genres(db):
    """Two visible genres + one hidden genre."""
    docs = [
        {"_id": ObjectId(), "genre_id": 28, "name": "Action", "is_hidden": False},
        {"_id": ObjectId(), "genre_id": 35, "name": "Comedy"},  # no is_hidden = visible
        {"_id": ObjectId(), "genre_id": 27, "name": "Horror", "is_hidden": True},
    ]
    await db.genres.insert_many(docs)
    return docs


# ── Admin list ────────────────────────────────────────────────────────────

class TestAdminListGenres:
    async def test_admin_sees_all_genres_including_hidden(
        self, client, admin_headers, seeded_genres
    ):
        resp = await client.get("/api/admin/genres", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 3
        names = {g["name"] for g in body}
        assert names == {"Action", "Comedy", "Horror"}
        # is_hidden defaults to False when missing on the document
        comedy = next(g for g in body if g["name"] == "Comedy")
        assert comedy["is_hidden"] is False

    async def test_non_admin_forbidden(
        self, client, auth_headers, seeded_genres
    ):
        resp = await client.get("/api/admin/genres", headers=auth_headers)
        assert resp.status_code == 403

    async def test_unauthenticated_forbidden(self, client, seeded_genres):
        resp = await client.get("/api/admin/genres")
        assert resp.status_code == 401


# ── Toggle visibility ─────────────────────────────────────────────────────

class TestToggleGenreVisibility:
    async def test_admin_can_hide_genre(
        self, client, admin_headers, seeded_genres, db
    ):
        resp = await client.patch(
            "/api/admin/genres/28/visibility",
            headers=admin_headers,
            json={"is_hidden": True},
        )
        assert resp.status_code == 200
        assert resp.json()["is_hidden"] is True
        doc = await db.genres.find_one({"genre_id": 28})
        assert doc["is_hidden"] is True

    async def test_admin_can_unhide_genre(
        self, client, admin_headers, seeded_genres, db
    ):
        resp = await client.patch(
            "/api/admin/genres/27/visibility",
            headers=admin_headers,
            json={"is_hidden": False},
        )
        assert resp.status_code == 200
        assert resp.json()["is_hidden"] is False
        doc = await db.genres.find_one({"genre_id": 27})
        assert doc["is_hidden"] is False

    async def test_unknown_genre_returns_404(
        self, client, admin_headers, seeded_genres
    ):
        resp = await client.patch(
            "/api/admin/genres/9999/visibility",
            headers=admin_headers,
            json={"is_hidden": True},
        )
        assert resp.status_code == 404

    async def test_non_admin_forbidden(
        self, client, auth_headers, seeded_genres
    ):
        resp = await client.patch(
            "/api/admin/genres/28/visibility",
            headers=auth_headers,
            json={"is_hidden": True},
        )
        assert resp.status_code == 403


# ── Public read-paths filter hidden genres ────────────────────────────────

class TestPublicGenreFiltering:
    async def test_public_genres_endpoint_excludes_hidden(
        self, client, seeded_genres
    ):
        resp = await client.get("/api/content/genres")
        assert resp.status_code == 200
        names = {g["name"] for g in resp.json()}
        assert names == {"Action", "Comedy"}
        assert "Horror" not in names

    async def test_browse_returns_404_for_hidden_genre(
        self, client, seeded_genres
    ):
        resp = await client.get("/api/content/browse/27")  # Horror is hidden
        assert resp.status_code == 404

    async def test_browse_works_for_visible_genre(
        self, client, seeded_genres
    ):
        resp = await client.get("/api/content/browse/28")  # Action is visible
        assert resp.status_code == 200
        # Body shape from get_content_by_genre
        body = resp.json()
        assert "movies" in body
        assert "series" in body


# ── Hidden-genre cascade onto movies/series ───────────────────────────────

@pytest.fixture
async def seeded_movies_with_genres(db, seeded_genres):
    """Three movies: one Action-only, one Action+Horror, one Comedy-only."""
    docs = [
        {
            "_id": ObjectId(),
            "tmdb_id": 1001,
            "title": "Pure Action Movie",
            "genres": [{"genre_id": 28, "name": "Action"}],
            "popularity": 100,
            "vote_count": 100,
            "vote_average": 8.0,
            "raw_data": {"id": 1001},  # required so two-tier service hits cache
        },
        {
            "_id": ObjectId(),
            "tmdb_id": 1002,
            "title": "Horror-Action Movie",
            "genres": [
                {"genre_id": 28, "name": "Action"},
                {"genre_id": 27, "name": "Horror"},  # 27 is hidden in fixture
            ],
            "popularity": 90,
            "vote_count": 100,
            "vote_average": 8.5,
            "raw_data": {"id": 1002},
        },
        {
            "_id": ObjectId(),
            "tmdb_id": 1003,
            "title": "Pure Comedy Movie",
            "genres": [{"genre_id": 35, "name": "Comedy"}],
            "popularity": 80,
            "vote_count": 100,
            "vote_average": 7.0,
            "raw_data": {"id": 1003},
        },
    ]
    await db.movies.insert_many(docs)
    # Mirror embedded genres[] into the junction (browse resolves genre membership there).
    for doc in docs:
        for g in doc["genres"]:
            await db.movie_genres.insert_one({"tmdb_id": doc["tmdb_id"], "genre_id": g["genre_id"]})
    return docs


class TestHiddenGenreCascade:
    async def test_search_excludes_movie_with_hidden_genre(
        self, client, seeded_movies_with_genres
    ):
        resp = await client.get("/api/content/search?q=Movie")
        assert resp.status_code == 200
        titles = {r["title"] for r in resp.json()["results"]}
        assert "Pure Action Movie" in titles
        assert "Pure Comedy Movie" in titles
        assert "Horror-Action Movie" not in titles  # has hidden Horror genre

    async def test_browse_excludes_movie_with_other_hidden_genre(
        self, client, seeded_movies_with_genres
    ):
        # Browse Action (28) — should still hide the movie also tagged Horror.
        resp = await client.get("/api/content/browse/28")
        assert resp.status_code == 200
        titles = {m["title"] for m in resp.json()["movies"]}
        assert "Pure Action Movie" in titles
        assert "Horror-Action Movie" not in titles

    async def test_movie_detail_404_for_hidden_genre_item(
        self, client, seeded_movies_with_genres
    ):
        resp = await client.get("/api/content/movie/1002")  # has hidden Horror
        assert resp.status_code == 404

    async def test_movie_detail_ok_for_clean_item(
        self, client, seeded_movies_with_genres
    ):
        resp = await client.get("/api/content/movie/1001")
        assert resp.status_code == 200

    async def test_home_rails_exclude_movies_with_hidden_genre(
        self, client, seeded_movies_with_genres
    ):
        resp = await client.get("/api/content/home")
        assert resp.status_code == 200
        all_titles = {
            item.get("title")
            for rail in resp.json()["rails"]
            for item in rail["items"]
        }
        assert "Pure Action Movie" in all_titles
        assert "Pure Comedy Movie" in all_titles
        assert "Horror-Action Movie" not in all_titles


# ── Cache invalidation on toggle ──────────────────────────────────────────

class TestCacheInvalidation:
    async def test_genre_toggle_clears_home_cache(
        self, client, admin_headers, db
    ):
        # Seed a genre + movie
        await db.genres.insert_one(
            {"_id": ObjectId(), "genre_id": 99, "name": "Test", "is_hidden": False}
        )
        await db.movies.insert_one({
            "_id": ObjectId(),
            "tmdb_id": 5001,
            "title": "Test Movie",
            "genres": [{"genre_id": 99, "name": "Test"}],
            "popularity": 50,
            "vote_count": 100,
            "vote_average": 7.0,
        })

        # Warm the anonymous home cache — Test Movie should appear.
        first = await client.get("/api/content/home")
        first_titles = {i.get("title") for r in first.json()["rails"] for i in r["items"]}
        assert "Test Movie" in first_titles

        # Hide the genre.
        resp = await client.patch(
            "/api/admin/genres/99/visibility",
            headers=admin_headers,
            json={"is_hidden": True},
        )
        assert resp.status_code == 200

        # Anonymous home should now exclude the movie immediately (cache cleared).
        second = await client.get("/api/content/home")
        second_titles = {i.get("title") for r in second.json()["rails"] for i in r["items"]}
        assert "Test Movie" not in second_titles
