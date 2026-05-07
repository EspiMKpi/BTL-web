"""
Tests for movie_service — get_movie_by_id, get_movies_by_ids, search_movies.
"""

import pytest
from bson import ObjectId
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.movie_service import get_movie_by_id, get_movies_by_ids, search_movies


# ── get_movie_by_id ───────────────────────────────────────────────────────

class TestGetMovieById:
    async def test_movie_from_db(self, db):
        """If movie exists in MongoDB with raw_data and title, return it directly."""
        doc = {
            "_id": ObjectId(),
            "tmdb_id": 550,
            "title": "Fight Club",
            "overview": "An insomniac office worker...",
            "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
            "genres": [{"genre_id": 18, "name": "Drama"}],
            "cast": [],
            "crew": [],
            "raw_data": {"id": 550},
        }
        await db.movies.insert_one(doc)

        result = await get_movie_by_id(550)
        assert result["tmdb_id"] == 550
        assert result["title"] == "Fight Club"
        assert isinstance(result["_id"], str)

    async def test_movie_from_tmdb(self, db):
        """If movie not in DB, fetch from TMDB and upsert."""
        tmdb_data = {
            "id": 550,
            "title": "Fight Club",
            "original_title": "Fight Club",
            "tagline": "Mischief. Mayhem. Soap.",
            "overview": "An insomniac office worker...",
            "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
            "backdrop_path": "/hZkgoQYus5dXo3H8T7Uef6DNknx.jpg",
            "release_date": "1999-10-15",
            "original_language": "en",
            "popularity": 61.416,
            "vote_average": 8.433,
            "vote_count": 26280,
            "adult": False,
            "video": False,
            "runtime": 139,
            "budget": 63000000,
            "revenue": 100853753,
            "status": "Released",
            "imdb_id": "tt0137523",
            "homepage": "http://www.foxmovies.com/movies/fight-club",
            "genres": [{"id": 18, "name": "Drama"}, {"id": 53, "name": "Thriller"}],
            "credits": {
                "cast": [
                    {
                        "id": 819,
                        "name": "Edward Norton",
                        "profile_path": "/5Y9JGMHcQjF0kSGvOd5G8VG8oHs.jpg",
                        "character": "The Narrator",
                        "order": 0,
                    }
                ],
                "crew": [
                    {
                        "id": 7467,
                        "name": "David Fincher",
                        "profile_path": "/dcxBn8NRKx9vLjLh7U0WjY0UCLp.jpg",
                        "job": "Director",
                    }
                ],
            },
            "production_countries": [{"iso_3166_1": "US", "name": "United States of America"}],
            "spoken_languages": [{"iso_639_1": "en", "name": "English"}],
        }

        mock_response = MagicMock()
        mock_response.json.return_value = tmdb_data
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.movie_service.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance

            result = await get_movie_by_id(550)

        assert result["tmdb_id"] == 550
        assert result["title"] == "Fight Club"
        assert result["runtime"] == 139
        assert len(result["genres"]) == 2
        assert len(result["cast"]) == 1
        assert result["cast"][0]["name"] == "Edward Norton"
        assert len(result["crew"]) == 1
        assert result["crew"][0]["name"] == "David Fincher"
        assert isinstance(result["_id"], str)

        # Verify it was upserted into MongoDB
        stored = await db.movies.find_one({"tmdb_id": 550})
        assert stored is not None
        assert stored["title"] == "Fight Club"

        # Verify genres were upserted
        genre = await db.genres.find_one({"genre_id": 18})
        assert genre is not None
        assert genre["name"] == "Drama"


# ── get_movies_by_ids ─────────────────────────────────────────────────────

class TestGetMoviesByIds:
    async def test_multiple_movies(self, db):
        for i in range(3):
            await db.movies.insert_one({
                "_id": ObjectId(),
                "tmdb_id": 1000 + i,
                "title": f"Movie {i}",
            })

        result = await get_movies_by_ids([1000, 1001, 1002])
        assert len(result) == 3
        for doc in result:
            assert isinstance(doc["_id"], str)

    async def test_partial_match(self, db):
        await db.movies.insert_one({"_id": ObjectId(), "tmdb_id": 1000, "title": "Movie 0"})

        result = await get_movies_by_ids([1000, 9999])
        assert len(result) == 1
        assert result[0]["tmdb_id"] == 1000

    async def test_empty_result(self, db):
        result = await get_movies_by_ids([9999])
        assert result == []


# ── search_movies ─────────────────────────────────────────────────────────

class TestSearchMovies:
    @pytest.mark.skip(reason="mongomock does not support $text operator")
    async def test_search_returns_list(self, db):
        """$text search may not work in mongomock, but function should return a list."""
        result = await search_movies("test query")
        assert isinstance(result, list)
