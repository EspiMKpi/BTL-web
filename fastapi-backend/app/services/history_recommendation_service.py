"""
Per-user history-based recommender.

Reads the user's positive watch / favorite signals from MongoDB, treats each
as a seed, and aggregates the content-based neighbours produced by the
existing TF-IDF model (see RECOMMENDER_PLAN.md). No new model, no artifacts,
no caching, no `user_ratings` reads (same hard rule as the content-based
recommender — see HISTORY_RECOMMENDER_PLAN.md).

Single entry point:
    await for_user(user_id, content_type, n=10) -> list[tmdb_id]

Hydration to full Mongo docs is the router's job.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timezone
from typing import Iterable

from app.database import get_database
from app.services import recommendation_service

# Tunables ---------------------------------------------------------------------
# How long the user can be inactive before a positive signal halves in weight.
RECENCY_HALF_LIFE_DAYS = 60.0
# Minimum progress_seconds to treat a non-completed watch as a positive signal.
# 30 minutes — long enough to rule out "opened the page, bounced".
MIN_PROGRESS_SECONDS = 1800
# How many content-based neighbours to pull per seed before aggregation.
NEIGHBOURS_PER_SEED = 20
# Below this many seeds, return [] and let the home page hide the rail.
MIN_SEEDS_FOR_RECS = 3


def _recency_decay(when: datetime | None, *, half_life_days: float = RECENCY_HALF_LIFE_DAYS) -> float:
    """Exponential decay in (0, 1]. Returns 1.0 for missing/future dates."""
    if when is None:
        return 1.0
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    days = (datetime.now(timezone.utc) - when).total_seconds() / 86400.0
    if days <= 0:
        return 1.0
    return math.exp(-days * math.log(2) / half_life_days)


async def _build_seeds(db, user_id: str, content_type: str) -> dict[int, float]:
    """Map tmdb_id -> max signal weight across all positive sources."""
    seeds: dict[int, float] = {}

    # Completed OR watched >= MIN_PROGRESS_SECONDS, collapsed to one row per title.
    history_cursor = db.watch_history.aggregate([
        {"$match": {
            "user_id": user_id,
            "content_type": content_type,
            "$or": [
                {"completed": True},
                {"progress_seconds": {"$gte": MIN_PROGRESS_SECONDS}},
            ],
        }},
        {"$group": {
            "_id": "$tmdb_id",
            "last_watched_at": {"$max": "$last_watched_at"},
        }},
    ])
    async for row in history_cursor:
        tmdb_id = int(row["_id"])
        weight = _recency_decay(row.get("last_watched_at"))
        if weight > seeds.get(tmdb_id, 0.0):
            seeds[tmdb_id] = weight

    # Favorites — full weight, no decay (the bookmark is an active assertion).
    fav_cursor = db.watchlist_items.find({
        "user_id": user_id,
        "content_type": content_type,
        "is_favorite": True,
    }, {"tmdb_id": 1})
    async for row in fav_cursor:
        tmdb_id = int(row["tmdb_id"])
        if 1.0 > seeds.get(tmdb_id, 0.0):
            seeds[tmdb_id] = 1.0

    return seeds


async def _build_seen_set(db, user_id: str, content_type: str) -> set[int]:
    """Items the user has already touched — never recommend back."""
    seen: set[int] = set()

    history_cursor = db.watch_history.find(
        {"user_id": user_id, "content_type": content_type},
        {"tmdb_id": 1},
    )
    async for row in history_cursor:
        seen.add(int(row["tmdb_id"]))

    watchlist_cursor = db.watchlist_items.find(
        {"user_id": user_id, "content_type": content_type},
        {"tmdb_id": 1},
    )
    async for row in watchlist_cursor:
        seen.add(int(row["tmdb_id"]))

    return seen


def _aggregate_neighbours(
    content_type: str,
    seeds: dict[int, float],
    seen: set[int],
) -> Iterable[tuple[int, float]]:
    """For each seed, pull its TF-IDF neighbours and accumulate weighted scores.

    Score per candidate = sum over seeds of (seed_weight / (rank + 1)).
    The 1/(rank+1) decay is MRR-style: rank-1 neighbour ~ 10x rank-10's contribution.
    """
    scores: dict[int, float] = defaultdict(float)
    for seed_id, seed_weight in seeds.items():
        neighbours = recommendation_service.similar_to(
            content_type, seed_id, top_n=NEIGHBOURS_PER_SEED,
        )
        for rank, neighbour_id in enumerate(neighbours):
            if neighbour_id in seen or neighbour_id in seeds:
                continue
            scores[neighbour_id] += seed_weight / (rank + 1)
    return scores.items()


async def for_user(user_id: str, content_type: str, n: int = 10) -> list[int]:
    """Return up to *n* personalised tmdb_ids for the user.

    Returns [] when the user has too few positive signals (cold-start) or when
    every candidate was already in their seen-set. Raises
    `recommendation_service.RecommenderNotTrained` if the underlying TF-IDF
    artifact for *content_type* hasn't been built.
    """
    if content_type not in recommendation_service.SUPPORTED_CONTENT_TYPES:
        raise ValueError(
            f"unsupported content_type {content_type!r}; "
            f"expected one of {recommendation_service.SUPPORTED_CONTENT_TYPES}"
        )

    db = get_database()
    seeds = await _build_seeds(db, user_id, content_type)
    if len(seeds) < MIN_SEEDS_FOR_RECS:
        return []

    seen = await _build_seen_set(db, user_id, content_type)
    scored = _aggregate_neighbours(content_type, seeds, seen)
    ranked = sorted(scored, key=lambda kv: -kv[1])
    return [int(tmdb_id) for tmdb_id, _ in ranked[:n]]
