"""
Tests for series_service — get_series_by_id, get_series_by_ids.
"""

import pytest
from bson import ObjectId
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.series_service import get_series_by_id, get_series_by_ids


# ── get_series_by_id ──────────────────────────────────────────────────────

class TestGetSeriesById:
    async def test_series_from_db(self, db):
        """If series exists in MongoDB with raw_data and seasons, return directly."""
        doc = {
            "_id": ObjectId(),
            "tmdb_id": 1399,
            "name": "Game of Thrones",
            "overview": "Seven noble families fight...",
            "poster_path": "/poster.jpg",
            "genres": [{"genre_id": 10765, "name": "Sci-Fi & Fantasy"}],
            "cast": [],
            "crew": [],
            "seasons": [{"season_number": 1, "name": "Season 1", "episodes": []}],
            "raw_data": {"id": 1399},
        }
        await db.series.insert_one(doc)

        result = await get_series_by_id(1399)
        assert result["tmdb_id"] == 1399
        assert result["name"] == "Game of Thrones"
        assert isinstance(result["_id"], str)

    async def test_series_from_tmdb(self, db):
        """If series not in DB, fetch from TMDB and upsert."""
        tmdb_data = {
            "id": 1399,
            "name": "Game of Thrones",
            "original_name": "Game of Thrones",
            "tagline": "Winter Is Coming",
            "overview": "Seven noble families fight...",
            "poster_path": "/poster.jpg",
            "backdrop_path": "/backdrop.jpg",
            "first_air_date": "2011-04-17",
            "last_air_date": "2019-05-19",
            "original_language": "en",
            "popularity": 346.416,
            "vote_average": 8.4,
            "vote_count": 21000,
            "adult": False,
            "episode_run_time": [60],
            "type": "Scripted",
            "status": "Ended",
            "imdb_id": "tt0944947",
            "homepage": "http://www.hbo.com/game-of-thrones",
            "number_of_seasons": 8,
            "number_of_episodes": 73,
            "genres": [
                {"id": 10765, "name": "Sci-Fi & Fantasy"},
                {"id": 18, "name": "Drama"},
            ],
            "seasons": [
                {
                    "season_number": 1,
                    "name": "Season 1",
                    "overview": "Season 1 overview",
                    "poster_path": "/s1.jpg",
                    "air_date": "2011-04-17",
                    "episode_count": 10,
                },
                {
                    "season_number": 0,
                    "name": "Specials",
                    "overview": "",
                    "poster_path": None,
                    "air_date": None,
                    "episode_count": 0,
                },
            ],
            "credits": {
                "cast": [
                    {
                        "id": 239019,
                        "name": "Emilia Clarke",
                        "profile_path": "/emilia.jpg",
                        "character": "Daenerys Targaryen",
                        "order": 0,
                    }
                ],
                "crew": [
                    {
                        "id": 9287,
                        "name": "David Benioff",
                        "profile_path": "/benioff.jpg",
                        "job": "Executive Producer",
                    }
                ],
            },
            "networks": [{"id": 49, "name": "HBO"}],
            "production_countries": [{"iso_3166_1": "US", "name": "United States of America"}],
            "spoken_languages": [{"iso_639_1": "en", "name": "English"}],
        }

        # Mock season detail response
        season_data = {
            "season_number": 1,
            "name": "Season 1",
            "overview": "Season 1 overview",
            "poster_path": "/s1.jpg",
            "air_date": "2011-04-17",
            "episodes": [
                {
                    "episode_number": 1,
                    "name": "Winter Is Coming",
                    "overview": "Episode 1 overview",
                    "still_path": "/ep1.jpg",
                    "air_date": "2011-04-17",
                    "runtime": 62,
                    "vote_average": 8.1,
                    "vote_count": 200,
                    "season_number": 1,
                }
            ],
        }

        mock_main_resp = MagicMock()
        mock_main_resp.json.return_value = tmdb_data
        mock_main_resp.raise_for_status = MagicMock()

        mock_season_resp = MagicMock()
        mock_season_resp.json.return_value = season_data
        mock_season_resp.raise_for_status = MagicMock()

        call_count = 0

        async def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if "season" in url:
                return mock_season_resp
            return mock_main_resp

        with patch("app.services.series_service.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_instance.get = AsyncMock(side_effect=mock_get)
            mock_client.return_value = mock_instance

            result = await get_series_by_id(1399)

        assert result["tmdb_id"] == 1399
        assert result["name"] == "Game of Thrones"
        assert result["number_of_seasons"] == 8
        assert result["number_of_episodes"] == 73
        assert len(result["genres"]) == 2
        assert len(result["cast"]) == 1
        assert result["cast"][0]["name"] == "Emilia Clarke"
        assert len(result["crew"]) == 1
        assert result["crew"][0]["name"] == "David Benioff"
        assert len(result["seasons"]) >= 1
        # First season should have episodes
        s1 = next(s for s in result["seasons"] if s["season_number"] == 1)
        assert len(s1["episodes"]) == 1
        assert s1["episodes"][0]["name"] == "Winter Is Coming"
        assert isinstance(result["_id"], str)

        # Verify upserted into MongoDB
        stored = await db.series.find_one({"tmdb_id": 1399})
        assert stored is not None
        assert stored["name"] == "Game of Thrones"


# ── get_series_by_ids ─────────────────────────────────────────────────────

class TestGetSeriesByIds:
    async def test_multiple_series(self, db):
        for i in range(3):
            await db.series.insert_one({
                "_id": ObjectId(),
                "tmdb_id": 2000 + i,
                "name": f"Series {i}",
            })

        result = await get_series_by_ids([2000, 2001, 2002])
        assert len(result) == 3
        for doc in result:
            assert isinstance(doc["_id"], str)

    async def test_partial_match(self, db):
        await db.series.insert_one({"_id": ObjectId(), "tmdb_id": 2000, "name": "Series 0"})

        result = await get_series_by_ids([2000, 9999])
        assert len(result) == 1
        assert result[0]["tmdb_id"] == 2000

    async def test_empty_result(self, db):
        result = await get_series_by_ids([9999])
        assert result == []
