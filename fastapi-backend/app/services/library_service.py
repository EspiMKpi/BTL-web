"""
Library service — mirrors database/src/libraryService.ts.
Home rails, genre browsing, profile stats, recent activity.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from cachetools import TTLCache

from app.database import get_database
from app.utils import is_movie_doc, is_series_doc, sanitize as _sanitize

# ── In-memory TTL cache for home rails (per-worker, 5 min TTL) ───────────
_home_cache: TTLCache[str, dict] = TTLCache(maxsize=64, ttl=300)


def _cache_key(user_id: Optional[str], rail_limit: int) -> str:
    return f"home:{user_id or 'anon'}:{rail_limit}"


def clear_home_cache() -> None:
    """Drop all cached anonymous home rails (call after admin visibility toggles)."""
    _home_cache.clear()


async def get_hidden_genre_ids() -> List[int]:
    """Genre IDs currently flagged is_hidden=True."""
    db = get_database()
    cursor = db.genres.find({"is_hidden": True}, {"genre_id": 1})
    return [doc["genre_id"] async for doc in cursor]


async def public_content_filter() -> Dict[str, Any]:
    """
    Mongo filter for movies/series visible to public users.
    Excludes per-doc-hidden items AND items tagged with any hidden genre.
    """
    f: Dict[str, Any] = {"is_hidden": {"$ne": True}}
    hidden_ids = await get_hidden_genre_ids()
    if hidden_ids:
        f["genres.genre_id"] = {"$nin": hidden_ids}
    return f


async def get_home_rails(user_id: Optional[str] = None, rail_limit: int = 10) -> dict:
    """Build Netflix-style home page rails."""
    cache_key = _cache_key(user_id, rail_limit)

    # Only cache anonymous requests (authenticated rails include per-user data)
    if user_id is None and cache_key in _home_cache:
        return _home_cache[cache_key]

    db = get_database()

    # Fetch all rails concurrently — exclude hidden content (per-doc + hidden-genre cascade)
    hidden_filter = await public_content_filter()
    trending_movies = await db.movies.find(hidden_filter).sort("popularity", -1).limit(rail_limit).to_list(rail_limit)
    trending_series = await db.series.find(hidden_filter).sort("popularity", -1).limit(rail_limit).to_list(rail_limit)
    top_rated_movies = await db.movies.find({"vote_count": {"$gte": 50}, **hidden_filter}).sort("vote_average", -1).limit(rail_limit).to_list(rail_limit)
    top_rated_series = await db.series.find({"vote_count": {"$gte": 50}, **hidden_filter}).sort("vote_average", -1).limit(rail_limit).to_list(rail_limit)
    new_release_movies = await db.movies.find(hidden_filter).sort("release_date", -1).limit(rail_limit).to_list(rail_limit)
    recent_series = await db.series.find(hidden_filter).sort("first_air_date", -1).limit(rail_limit).to_list(rail_limit)
    genres = await db.genres.find({"is_hidden": {"$ne": True}}).sort("name", 1).to_list(100)

    # Sanitize all documents (convert ObjectId, datetime, etc.)
    for doc_list in (trending_movies, trending_series, top_rated_movies, top_rated_series, new_release_movies, recent_series):
        for i, doc in enumerate(doc_list):
            doc_list[i] = _sanitize(doc)
    genres = [_sanitize(g) for g in genres]

    # Filter out misplaced documents (series in movies collection, movies in series collection)
    trending_movies = [d for d in trending_movies if is_movie_doc(d)]
    top_rated_movies = [d for d in top_rated_movies if is_movie_doc(d)]
    new_release_movies = [d for d in new_release_movies if is_movie_doc(d)]
    trending_series = [d for d in trending_series if is_series_doc(d)]
    top_rated_series = [d for d in top_rated_series if is_series_doc(d)]
    recent_series = [d for d in recent_series if is_series_doc(d)]

    rails: List[Dict[str, Any]] = [
        {"id": "trending_movies", "title": "Trending Movies", "content_type": "movie", "items": trending_movies},
        {"id": "trending_series", "title": "Trending TV Shows", "content_type": "series", "items": trending_series},
        {"id": "top_rated_movies", "title": "Top Rated Movies", "content_type": "movie", "items": top_rated_movies},
        {"id": "top_rated_series", "title": "Top Rated TV Shows", "content_type": "series", "items": top_rated_series},
        {"id": "new_releases", "title": "New Releases", "content_type": "movie", "items": new_release_movies},
        {"id": "recent_series", "title": "Recently Added TV Shows", "content_type": "series", "items": recent_series},
    ]

    # Continue watching rails (authenticated users only) — split per content_type
    if user_id:
        movies_cw, series_cw = await _build_continue_watching(db, user_id, hidden_filter)
        # Insert series first then movies so movies appears at index 0
        if series_cw:
            rails.insert(0, {"id": "continue_watching_series", "title": "Continue Watching", "content_type": "series", "items": series_cw})
        if movies_cw:
            rails.insert(0, {"id": "continue_watching_movies", "title": "Continue Watching", "content_type": "movie", "items": movies_cw})

    result = {"rails": rails, "genres": genres}

    # Cache anonymous requests only
    if user_id is None:
        _home_cache[cache_key] = result

    return _sanitize(result)


async def _build_continue_watching(
    db: Any,
    user_id: str,
    hidden_filter: Dict[str, Any],
) -> tuple[List[dict], List[dict]]:
    """Return (movies_cw, series_cw) for the given user, each sorted by recency."""
    cw_pipeline = [
        {
            "$match": {
                "user_id": user_id,
                "completed": False,
                "progress_seconds": {"$gt": 0},
            }
        },
        {"$sort": {"last_watched_at": -1}},
        {
            "$group": {
                "_id": {"content_type": "$content_type", "tmdb_id": "$tmdb_id"},
                "doc": {"$first": "$$ROOT"},
            }
        },
        {"$replaceRoot": {"newRoot": "$doc"}},
        {"$sort": {"last_watched_at": -1}},
        {"$limit": 20},
    ]
    continue_items = await db.watch_history.aggregate(cw_pipeline).to_list(20)
    if not continue_items:
        return [], []

    movie_ids = [h["tmdb_id"] for h in continue_items if h["content_type"] == "movie"]
    series_ids = [h["tmdb_id"] for h in continue_items if h["content_type"] == "series"]

    movies = await db.movies.find({"tmdb_id": {"$in": movie_ids}, **hidden_filter}).to_list(50) if movie_ids else []
    series_list = await db.series.find({"tmdb_id": {"$in": series_ids}, **hidden_filter}).to_list(50) if series_ids else []

    content_map: Dict[str, dict] = {}
    for m in movies:
        m = _sanitize(m)
        content_map[f"movie_{m['tmdb_id']}"] = m
    for s in series_list:
        s = _sanitize(s)
        content_map[f"series_{s['tmdb_id']}"] = s

    movies_cw: List[dict] = []
    series_cw: List[dict] = []
    for h in continue_items:
        content = content_map.get(f"{h['content_type']}_{h['tmdb_id']}")
        if not content:
            continue
        enriched = {
            **content,
            "_history": {
                "progress_seconds": h["progress_seconds"],
                "season_number": h.get("season_number"),
                "episode_number": h.get("episode_number"),
                "last_watched_at": h.get("last_watched_at"),
            },
        }
        if h["content_type"] == "movie":
            movies_cw.append(enriched)
        else:
            series_cw.append(enriched)

    return movies_cw, series_cw


async def get_series_rails(rail_limit: int = 12, user_id: Optional[str] = None) -> dict:
    """Build series-specific rails for the Series page.

    Returns curated rails that leverage series-specific metadata:
    - Currently Airing  (status = "Returning Series")
    - Completed Gems    (status = "Ended", sorted by vote_average)
    - Mini-Series       (number_of_seasons = 1)
    - Most Episodes     (sorted by number_of_episodes desc)
    Plus the standard trending / top-rated / recent series rails.
    """
    db = get_database()
    hidden_filter = await public_content_filter()

    # --- Curated rails (fetch concurrently) ---
    currently_airing, completed_gems, mini_series, most_episodes, trending, top_rated, recent = await asyncio.gather(
        db.series.find({"status": "Returning Series", **hidden_filter}).sort("popularity", -1).limit(rail_limit).to_list(rail_limit),
        db.series.find({"status": "Ended", "vote_count": {"$gte": 20}, **hidden_filter}).sort("vote_average", -1).limit(rail_limit).to_list(rail_limit),
        db.series.find({"number_of_seasons": 1, **hidden_filter}).sort("popularity", -1).limit(rail_limit).to_list(rail_limit),
        db.series.find({"number_of_episodes": {"$gte": 10}, **hidden_filter}).sort("number_of_episodes", -1).limit(rail_limit).to_list(rail_limit),
        db.series.find(hidden_filter).sort("popularity", -1).limit(rail_limit).to_list(rail_limit),
        db.series.find({"vote_count": {"$gte": 50}, **hidden_filter}).sort("vote_average", -1).limit(rail_limit).to_list(rail_limit),
        db.series.find(hidden_filter).sort("first_air_date", -1).limit(rail_limit).to_list(rail_limit),
    )

    # Sanitize all
    for doc_list in (currently_airing, completed_gems, mini_series, most_episodes, trending, top_rated, recent):
        for i, doc in enumerate(doc_list):
            doc_list[i] = _sanitize(doc)

    # Filter out misplaced movie documents from series collection
    for doc_list in (currently_airing, completed_gems, mini_series, most_episodes, trending, top_rated, recent):
        filtered = [d for d in doc_list if is_series_doc(d)]
        doc_list.clear()
        doc_list.extend(filtered)

    rails: List[Dict[str, Any]] = []

    if currently_airing:
        rails.append({"id": "currently_airing", "title": "Currently Airing", "content_type": "series", "items": currently_airing})
    if trending:
        rails.append({"id": "trending_series", "title": "Trending Now", "content_type": "series", "items": trending})
    if top_rated:
        rails.append({"id": "top_rated_series", "title": "Top Rated", "content_type": "series", "items": top_rated})
    if completed_gems:
        rails.append({"id": "completed_gems", "title": "Completed Gems", "content_type": "series", "items": completed_gems})
    if mini_series:
        rails.append({"id": "mini_series", "title": "Mini-Series", "content_type": "series", "items": mini_series})
    if most_episodes:
        rails.append({"id": "most_episodes", "title": "Most Episodes", "content_type": "series", "items": most_episodes})
    if recent:
        rails.append({"id": "recent_series", "title": "Recently Added", "content_type": "series", "items": recent})

    # Prepend per-user Continue Watching (series only)
    if user_id:
        _movies_cw, series_cw = await _build_continue_watching(db, user_id, hidden_filter)
        if series_cw:
            rails.insert(0, {"id": "continue_watching_series", "title": "Continue Watching", "content_type": "series", "items": series_cw})

    return _sanitize({"rails": rails})


async def get_movie_rails(rail_limit: int = 12, user_id: Optional[str] = None) -> dict:
    """Build movie-specific rails for the Movies page.

    Returns curated rails that leverage movie-specific metadata:
    - Trending         (sorted by popularity)
    - Top Rated        (vote_count ≥ 50, sorted by vote_average)
    - New Releases     (sorted by release_date desc)
    - Classics         (released before 2000, high rating)
    - Highest Rated    (sorted by vote_average desc, minimal vote_count)
    Plus the standard trending / top-rated / new release rails.
    """
    db = get_database()
    hidden_filter = await public_content_filter()

    # --- Curated rails (fetch concurrently) ---
    trending, top_rated, new_releases, classics, highest_rated = await asyncio.gather(
        db.movies.find(hidden_filter).sort("popularity", -1).limit(rail_limit).to_list(rail_limit),
        db.movies.find({"vote_count": {"$gte": 50}, **hidden_filter}).sort("vote_average", -1).limit(rail_limit).to_list(rail_limit),
        db.movies.find(hidden_filter).sort("release_date", -1).limit(rail_limit).to_list(rail_limit),
        db.movies.find({"release_date": {"$lt": "2000"}, "vote_count": {"$gte": 30}, "vote_average": {"$gte": 7.0}, **hidden_filter}).sort("vote_average", -1).limit(rail_limit).to_list(rail_limit),
        db.movies.find({"vote_count": {"$gte": 10}, **hidden_filter}).sort("vote_average", -1).limit(rail_limit).to_list(rail_limit),
    )

    # Sanitize all
    for doc_list in (trending, top_rated, new_releases, classics, highest_rated):
        for i, doc in enumerate(doc_list):
            doc_list[i] = _sanitize(doc)

    # Filter out misplaced series documents from movies collection
    for doc_list in (trending, top_rated, new_releases, classics, highest_rated):
        filtered = [d for d in doc_list if is_movie_doc(d)]
        doc_list.clear()
        doc_list.extend(filtered)

    rails: List[Dict[str, Any]] = []

    if trending:
        rails.append({"id": "trending_movies", "title": "Trending Now", "content_type": "movie", "items": trending})
    if top_rated:
        rails.append({"id": "top_rated_movies", "title": "Top Rated", "content_type": "movie", "items": top_rated})
    if new_releases:
        rails.append({"id": "new_releases", "title": "New Releases", "content_type": "movie", "items": new_releases})
    if classics:
        rails.append({"id": "classics", "title": "Classics", "content_type": "movie", "items": classics})
    if highest_rated:
        rails.append({"id": "highest_rated", "title": "Highest Rated", "content_type": "movie", "items": highest_rated})

    # Prepend per-user Continue Watching (movies only)
    if user_id:
        movies_cw, _series_cw = await _build_continue_watching(db, user_id, hidden_filter)
        if movies_cw:
            rails.insert(0, {"id": "continue_watching_movies", "title": "Continue Watching", "content_type": "movie", "items": movies_cw})

    return _sanitize({"rails": rails})


async def get_content_by_genre(genre_id: int, page: int = 1, limit: int = 20) -> dict:
    """Genre-filtered browse page data."""
    db = get_database()
    skip = (page - 1) * limit

    # Exclude items tagged with any *other* hidden genre too (cross-tag cascade).
    other_hidden = [g for g in await get_hidden_genre_ids() if g != genre_id]
    genre_filter: Dict[str, Any] = {
        "genres.genre_id": genre_id,
        "is_hidden": {"$ne": True},
    }
    if other_hidden:
        genre_filter = {
            "$and": [
                {"genres.genre_id": genre_id},
                {"genres.genre_id": {"$nin": other_hidden}},
                {"is_hidden": {"$ne": True}},
            ]
        }

    movies = await db.movies.find(genre_filter).sort("popularity", -1).skip(skip).limit(limit).to_list(limit)
    series_list = await db.series.find(genre_filter).sort("popularity", -1).skip(skip).limit(limit).to_list(limit)
    movie_total = await db.movies.count_documents(genre_filter)
    series_total = await db.series.count_documents(genre_filter)

    movies = [_sanitize(d) for d in movies]
    series_list = [_sanitize(d) for d in series_list]

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
    avg_value = avg_result[0]["avg"] if avg_result and avg_result[0].get("avg") is not None else 0
    average_rating = round(avg_value * 10) / 10

    return {
        "watchlist_count": watchlist_count,
        "completed_count": completed_count,
        "watching_count": watching_count,
        "ratings_count": ratings_count,
        "history_count": history_count,
        "average_rating": average_rating,
    }


async def get_movies_by_tmdb_ids(
    tmdb_ids: List[int],
    include_hidden: bool = False,
) -> List[dict]:
    """Batch fetch movie docs by tmdb_id. Single $in round-trip; order is NOT preserved.

    When include_hidden is False (default), applies the public visibility filter
    (per-doc is_hidden plus the hidden-genre cascade). Callers that need
    recommender-order should re-sort by their input list.
    """
    if not tmdb_ids:
        return []
    db = get_database()
    query: Dict[str, Any] = {"tmdb_id": {"$in": list(tmdb_ids)}}
    if not include_hidden:
        query = {**query, **(await public_content_filter())}
    cursor = db.movies.find(query)
    docs = [_sanitize(d) async for d in cursor]
    return [d for d in docs if is_movie_doc(d)]


async def get_series_by_tmdb_ids(
    tmdb_ids: List[int],
    include_hidden: bool = False,
) -> List[dict]:
    """Batch fetch series docs by tmdb_id. Mirror of get_movies_by_tmdb_ids."""
    if not tmdb_ids:
        return []
    db = get_database()
    query: Dict[str, Any] = {"tmdb_id": {"$in": list(tmdb_ids)}}
    if not include_hidden:
        query = {**query, **(await public_content_filter())}
    cursor = db.series.find(query)
    docs = [_sanitize(d) async for d in cursor]
    return [d for d in docs if is_series_doc(d)]


async def get_recent_activity(user_id: str, limit: int = 20) -> dict:
    """Recent activity feed for profile page."""
    db = get_database()

    recent_history = await db.watch_history.find({"user_id": user_id}).sort("last_watched_at", -1).limit(limit).to_list(limit)
    recent_ratings = await db.user_ratings.find({"user_id": user_id}).sort("created_at", -1).limit(limit).to_list(limit)
    recent_watchlist = await db.watchlist_items.find({"user_id": user_id}).sort("updated_at", -1).limit(limit).to_list(limit)

    recent_history = [_sanitize(d) for d in recent_history]
    recent_ratings = [_sanitize(d) for d in recent_ratings]
    recent_watchlist = [_sanitize(d) for d in recent_watchlist]

    return {
        "recent_history": recent_history,
        "recent_ratings": recent_ratings,
        "recent_watchlist": recent_watchlist,
    }
