"""
Library service — mirrors database/src/libraryService.ts.
Home rails, genre browsing, profile stats, recent activity.
"""

from datetime import datetime
from functools import wraps
from typing import Any, Dict, List, Optional

from cachetools import TTLCache

from app.database import get_database

# ── In-memory TTL cache for home rails (per-worker, 5 min TTL) ───────────
_home_cache: TTLCache[str, dict] = TTLCache(maxsize=64, ttl=300)


def _cache_key(user_id: Optional[str], rail_limit: int) -> str:
    return f"home:{user_id or 'anon'}:{rail_limit}"


async def get_home_rails(user_id: Optional[str] = None, rail_limit: int = 10) -> dict:
    """Build Netflix-style home page rails."""
    cache_key = _cache_key(user_id, rail_limit)

    # Only cache anonymous requests (authenticated rails include per-user data)
    if user_id is None and cache_key in _home_cache:
        return _home_cache[cache_key]

    db = get_database()

    # Fetch all rails concurrently
    trending_movies = await db.movies.find().sort("popularity", -1).limit(rail_limit).to_list(rail_limit)
    trending_series = await db.series.find().sort("popularity", -1).limit(rail_limit).to_list(rail_limit)
    top_rated_movies = await db.movies.find({"vote_count": {"$gte": 50}}).sort("vote_average", -1).limit(rail_limit).to_list(rail_limit)
    top_rated_series = await db.series.find({"vote_count": {"$gte": 50}}).sort("vote_average", -1).limit(rail_limit).to_list(rail_limit)
    new_release_movies = await db.movies.find().sort("release_date", -1).limit(rail_limit).to_list(rail_limit)
    recent_series = await db.series.find().sort("first_air_date", -1).limit(rail_limit).to_list(rail_limit)
    genres = await db.genres.find().sort("name", 1).to_list(100)

    # Convert ObjectId to string
    for doc_list in (trending_movies, trending_series, top_rated_movies, top_rated_series, new_release_movies, recent_series):
        for doc in doc_list:
            doc["_id"] = str(doc["_id"])
    for g in genres:
        g["_id"] = str(g["_id"])

    rails: List[Dict[str, Any]] = [
        {"id": "trending_movies", "title": "Trending Movies", "content_type": "movie", "items": trending_movies},
        {"id": "trending_series", "title": "Trending TV Shows", "content_type": "series", "items": trending_series},
        {"id": "top_rated_movies", "title": "Top Rated Movies", "content_type": "movie", "items": top_rated_movies},
        {"id": "top_rated_series", "title": "Top Rated TV Shows", "content_type": "series", "items": top_rated_series},
        {"id": "new_releases", "title": "New Releases", "content_type": "movie", "items": new_release_movies},
        {"id": "recent_series", "title": "Recently Added TV Shows", "content_type": "series", "items": recent_series},
    ]

    # Continue watching rail (authenticated users only)
    if user_id:
        continue_items = (
            await db.watch_history.find(
                {"user_id": user_id, "completed": False, "progress_seconds": {"$gt": 0}}
            )
            .sort("last_watched_at", -1)
            .limit(10)
            .to_list(10)
        )

        if continue_items:
            movie_ids = [h["tmdb_id"] for h in continue_items if h["content_type"] == "movie"]
            series_ids = [h["tmdb_id"] for h in continue_items if h["content_type"] == "series"]

            movies = await db.movies.find({"tmdb_id": {"$in": movie_ids}}).to_list(50) if movie_ids else []
            series_list = await db.series.find({"tmdb_id": {"$in": series_ids}}).to_list(50) if series_ids else []

            content_map: Dict[str, dict] = {}
            for m in movies:
                m["_id"] = str(m["_id"])
                content_map[f"movie_{m['tmdb_id']}"] = m
            for s in series_list:
                s["_id"] = str(s["_id"])
                content_map[f"series_{s['tmdb_id']}"] = s

            continue_watching = []
            for h in continue_items:
                content = content_map.get(f"{h['content_type']}_{h['tmdb_id']}")
                if not content:
                    continue
                continue_watching.append(
                    {
                        **content,
                        "_history": {
                            "progress_seconds": h["progress_seconds"],
                            "season_number": h.get("season_number"),
                            "episode_number": h.get("episode_number"),
                            "last_watched_at": h.get("last_watched_at"),
                        },
                    }
                )

            if continue_watching:
                rails.insert(
                    0,
                    {"id": "continue_watching", "title": "Continue Watching", "content_type": "mixed", "items": continue_watching},
                )

    result = {"rails": rails, "genres": genres}

    # Cache anonymous requests only
    if user_id is None:
        _home_cache[cache_key] = result

    return result


async def get_content_by_genre(genre_id: int, page: int = 1, limit: int = 20) -> dict:
    """Genre-filtered browse page data."""
    db = get_database()
    skip = (page - 1) * limit

    movies = await db.movies.find({"genres.genre_id": genre_id}).sort("popularity", -1).skip(skip).limit(limit).to_list(limit)
    series_list = await db.series.find({"genres.genre_id": genre_id}).sort("popularity", -1).skip(skip).limit(limit).to_list(limit)
    movie_total = await db.movies.count_documents({"genres.genre_id": genre_id})
    series_total = await db.series.count_documents({"genres.genre_id": genre_id})

    for doc in movies + series_list:
        doc["_id"] = str(doc["_id"])

    return {
        "movies": movies,
        "series": series_list,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_movies": movie_total,
            "total_series": series_total,
            "has_more_movies": skip + limit < movie_total,
            "has_more_series": skip + limit < series_total,
        },
    }


async def get_profile_stats(user_id: str) -> dict:
    """Profile statistics for an authenticated user."""
    db = get_database()

    watchlist_count = await db.watchlist_items.count_documents({"user_id": user_id})
    completed_count = await db.watchlist_items.count_documents({"user_id": user_id, "status": "completed"})
    watching_count = await db.watchlist_items.count_documents({"user_id": user_id, "status": "watching"})
    ratings_count = await db.user_ratings.count_documents({"user_id": user_id})
    history_count = await db.watch_history.count_documents({"user_id": user_id})

    avg_pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": None, "avg": {"$avg": "$rating"}}},
    ]
    avg_result = await db.user_ratings.aggregate(avg_pipeline).to_list(1)
    average_rating = round(avg_result[0]["avg"] * 10) / 10 if avg_result else 0

    return {
        "watchlist_count": watchlist_count,
        "completed_count": completed_count,
        "watching_count": watching_count,
        "ratings_count": ratings_count,
        "history_count": history_count,
        "average_rating": average_rating,
    }


async def get_recent_activity(user_id: str, limit: int = 20) -> dict:
    """Recent activity feed for profile page."""
    db = get_database()

    recent_history = await db.watch_history.find({"user_id": user_id}).sort("last_watched_at", -1).limit(limit).to_list(limit)
    recent_ratings = await db.user_ratings.find({"user_id": user_id}).sort("created_at", -1).limit(limit).to_list(limit)
    recent_watchlist = await db.watchlist_items.find({"user_id": user_id}).sort("updated_at", -1).limit(limit).to_list(limit)

    for doc_list in (recent_history, recent_ratings, recent_watchlist):
        for doc in doc_list:
            doc["_id"] = str(doc["_id"])

    return {
        "recent_history": recent_history,
        "recent_ratings": recent_ratings,
        "recent_watchlist": recent_watchlist,
    }
