"""
Seed synthetic demo users + watch_history + watchlist favorites for the
recommender demo. Idempotent — re-run wipes and reseeds.

Run from fastapi-backend/:
    .venv\\Scripts\\python.exe scripts\\seed_demo_users.py
    .venv\\Scripts\\python.exe scripts\\seed_demo_users.py --wipe   # remove only

Why this exists: the live catalog (~300 TMDB titles) has too few real watch
records to drive FP-Growth or GRU4Rec into producing anything meaningful for a
demo. This script generates 40 demo users, each with 15-40 chronological
watch_history records biased by genre persona, plus ~30% with a few favorites.

Determinism: random.seed(42) ⇒ identical output every run (modulo current time
embedded in last_watched_at offsets, which we generate relative to now()).

All records carry `is_demo_seed=True` (users) or are wiped via the user_id
of those users (history + watchlist). The wipe path uses both flags so a
half-failed previous run is also cleaned.
"""

import argparse
import asyncio
import io
import os
import random
import sys
from datetime import datetime, timedelta, timezone

# Force UTF-8 stdout/stderr so progress lines don't crash on Windows cp1252.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)

from bson import ObjectId

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.security import hash_password
from app.database import close_mongo_connection, connect_to_mongo, get_database

SEED = 42
N_USERS = 40
WATCHES_PER_USER_RANGE = (15, 40)
FAVORITES_PER_USER_RANGE = (2, 5)
FAVORITES_USER_RATIO = 0.30          # 30% of demo users have favorites

# Outcome mix for each watch_history row
PROB_COMPLETED = 0.70                # full watch, completed=True
PROB_PARTIAL_POSITIVE = 0.20         # 30-120 min watched, completed=False (still positive)
PROB_BOUNCED = 0.10                  # <30 min watched (negative signal — filtered out by training)

PARTIAL_RANGE_SEC = (1800, 7200)     # 30 min .. 2 hr
BOUNCED_RANGE_SEC = (60, 1700)       # 1 min .. just under 30 min

# Days between consecutive watches in a user's history
WATCH_GAP_DAYS_RANGE = (1, 3)
# Series watches mix in episode/season metadata occasionally (not required by recommender)
SERIES_EPISODE_PROB = 0.5

PERSONAS = {
    # genre_id sets from TMDB. Bias = these IDs make up 80% of the user's picks.
    "action_fan":  [28, 12, 53, 80, 10752],
    "drama_fan":   [18, 10749, 36, 99],
    "scifi_fan":   [878, 14, 27, 9648],
    "comedy_fan":  [35, 16, 10751, 10402],
    "mixed":       [],  # no bias; uniform sample
}
PERSONA_BIAS = 0.80  # 80% of picks come from persona genres, 20% random


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def wipe(db) -> None:
    """Remove all is_demo_seed users + their history + their watchlist items."""
    demo_users = await db.users.find({"is_demo_seed": True}, {"_id": 1}).to_list(None)
    demo_user_ids = [str(u["_id"]) for u in demo_users]
    print(f"[wipe] Found {len(demo_user_ids)} demo users.")

    if demo_user_ids:
        h_res = await db.watch_history.delete_many({"user_id": {"$in": demo_user_ids}})
        w_res = await db.watchlist_items.delete_many({"user_id": {"$in": demo_user_ids}})
        u_res = await db.users.delete_many({"is_demo_seed": True})
        print(f"[wipe]  watch_history     : {h_res.deleted_count}")
        print(f"[wipe]  watchlist_items   : {w_res.deleted_count}")
        print(f"[wipe]  users             : {u_res.deleted_count}")
    else:
        # Defence in depth: also try email pattern in case a prior seed crashed
        # before tagging is_demo_seed (unlikely, but cheap).
        u_res = await db.users.delete_many({"email": {"$regex": r"^demo_user_\d+@vozflix\.demo$"}})
        print(f"[wipe] No is_demo_seed users; fallback by email pattern: {u_res.deleted_count} users")


async def _load_catalog(db) -> tuple[list[dict], list[dict]]:
    """Return (movies, series) catalog rows with tmdb_id + genre_ids."""
    movies = await db.movies.find(
        {"is_hidden": {"$ne": True}},
        {"tmdb_id": 1, "genres": 1},
    ).to_list(None)
    series = await db.series.find(
        {"is_hidden": {"$ne": True}},
        {"tmdb_id": 1, "genres": 1},
    ).to_list(None)

    def _flatten(doc: dict) -> dict:
        return {
            "tmdb_id": int(doc["tmdb_id"]),
            "genre_ids": [int(g.get("genre_id")) for g in doc.get("genres", []) if g.get("genre_id") is not None],
        }

    return [_flatten(m) for m in movies], [_flatten(s) for s in series]


def _pick_titles(
    rng: random.Random,
    persona: str,
    pool: list[dict],
    k: int,
) -> list[int]:
    """Sample k tmdb_ids from *pool*, biased toward the persona's genre set.

    80% drawn (without replacement) from items overlapping persona genres,
    20% drawn uniformly from the rest. If persona is 'mixed' or there are not
    enough biased items, falls back to uniform.
    """
    if not pool or k <= 0:
        return []
    bias_genres = set(PERSONAS.get(persona) or [])
    if not bias_genres:
        sample = rng.sample(pool, min(k, len(pool)))
        return [it["tmdb_id"] for it in sample]

    in_bias = [it for it in pool if any(g in bias_genres for g in it["genre_ids"])]
    out_bias = [it for it in pool if it not in in_bias]

    n_bias = min(int(round(k * PERSONA_BIAS)), len(in_bias))
    n_rand = k - n_bias
    # If the bias pool is too thin, top up from out_bias.
    if n_bias < int(round(k * PERSONA_BIAS)):
        n_rand = min(k - n_bias, len(out_bias))

    chosen = rng.sample(in_bias, n_bias) if in_bias else []
    chosen += rng.sample(out_bias, n_rand) if out_bias and n_rand > 0 else []
    rng.shuffle(chosen)
    return [it["tmdb_id"] for it in chosen[:k]]


def _build_watch_history_rows(
    rng: random.Random,
    user_id: str,
    persona: str,
    movies_pool: list[dict],
    series_pool: list[dict],
) -> list[dict]:
    """One user's chronological watch history. Returns rows ready to insert."""
    n_watches = rng.randint(*WATCHES_PER_USER_RANGE)
    # Roughly 60/40 movies / series, jittered slightly per user.
    n_movies = int(round(n_watches * rng.uniform(0.5, 0.7)))
    n_series = n_watches - n_movies

    movie_ids = _pick_titles(rng, persona, movies_pool, n_movies)
    series_ids = _pick_titles(rng, persona, series_pool, n_series)

    # Interleave so the sequence isn't all-movies-then-all-series.
    sequence: list[tuple[str, int]] = (
        [("movie", t) for t in movie_ids]
        + [("series", t) for t in series_ids]
    )
    rng.shuffle(sequence)

    now = _now_utc()
    # Walk backwards from now() so the oldest record is in the deepest past.
    when = now - timedelta(hours=rng.randint(0, 24))
    rows: list[dict] = []
    for content_type, tmdb_id in reversed(sequence):
        # Outcome mix
        roll = rng.random()
        if roll < PROB_COMPLETED:
            progress_seconds = rng.randint(5400, 9000)  # 90-150 min
            completed = True
        elif roll < PROB_COMPLETED + PROB_PARTIAL_POSITIVE:
            progress_seconds = rng.randint(*PARTIAL_RANGE_SEC)
            completed = False
        else:
            progress_seconds = rng.randint(*BOUNCED_RANGE_SEC)
            completed = False

        season_number = None
        episode_number = None
        if content_type == "series" and rng.random() < SERIES_EPISODE_PROB:
            season_number = rng.randint(1, 3)
            episode_number = rng.randint(1, 12)

        rows.append({
            "_id": ObjectId(),
            "user_id": user_id,
            "content_type": content_type,
            "tmdb_id": tmdb_id,
            "season_number": season_number,
            "episode_number": episode_number,
            "progress_seconds": progress_seconds,
            "completed": completed,
            "last_watched_at": when,
            "created_at": when,
        })
        when -= timedelta(days=rng.randint(*WATCH_GAP_DAYS_RANGE),
                          hours=rng.randint(0, 12))

    # Insert in chronological order so MongoDB scans match real-world insert order.
    rows.reverse()
    return rows


def _build_favorites_rows(
    rng: random.Random,
    user_id: str,
    watch_rows: list[dict],
) -> list[dict]:
    """Pick a handful of completed titles and mark them favorite in watchlist_items."""
    completed_rows = [r for r in watch_rows if r["completed"]]
    if not completed_rows:
        return []
    n_favs = min(rng.randint(*FAVORITES_PER_USER_RANGE), len(completed_rows))
    picks = rng.sample(completed_rows, n_favs)
    now = _now_utc()
    out: list[dict] = []
    for src in picks:
        out.append({
            "_id": ObjectId(),
            "user_id": user_id,
            "content_type": src["content_type"],
            "tmdb_id": src["tmdb_id"],
            "status": "completed",
            "is_favorite": True,
            "is_bookmarked": False,
            "progress_seconds": src["progress_seconds"],
            "created_at": now,
            "updated_at": now,
        })
    return out


async def seed(db) -> None:
    rng = random.Random(SEED)

    movies_pool, series_pool = await _load_catalog(db)
    if not movies_pool and not series_pool:
        print("[seed] [!] Catalog is empty. Run scripts/seed_tmdb.py first.")
        return
    print(f"[seed] Catalog: {len(movies_pool)} movies, {len(series_pool)} series.")

    persona_names = list(PERSONAS.keys())
    now = _now_utc()

    user_docs: list[dict] = []
    history_rows_all: list[dict] = []
    favorites_rows_all: list[dict] = []
    favorites_user_count = int(round(N_USERS * FAVORITES_USER_RATIO))
    favorites_user_indices = set(rng.sample(range(N_USERS), favorites_user_count))

    password_hash = hash_password("Demo1234!")

    for i in range(N_USERS):
        persona = persona_names[i % len(persona_names)]
        user_id = ObjectId()
        email = f"demo_user_{i:03d}@vozflix.demo"
        user_docs.append({
            "_id": user_id,
            "email": email,
            "password": password_hash,
            "username": f"demo_user_{i:03d}",
            "avatar_url": None,
            "role": "user",
            "is_active": True,
            "is_banned": False,
            "is_demo_seed": True,
            "persona": persona,
            "created_at": now,
            "updated_at": now,
        })

        watch_rows = _build_watch_history_rows(
            rng, str(user_id), persona, movies_pool, series_pool,
        )
        history_rows_all.extend(watch_rows)

        if i in favorites_user_indices:
            favorites_rows_all.extend(
                _build_favorites_rows(rng, str(user_id), watch_rows)
            )

    # Bulk insert
    if user_docs:
        await db.users.insert_many(user_docs)
    if history_rows_all:
        await db.watch_history.insert_many(history_rows_all)
    if favorites_rows_all:
        # watchlist_items has a unique (user_id, tmdb_id) index — guard against
        # the rare collision when the same user got the same favorite twice
        # by inserting individually with upsert semantics.
        for row in favorites_rows_all:
            await db.watchlist_items.update_one(
                {"user_id": row["user_id"], "tmdb_id": row["tmdb_id"]},
                {"$set": row},
                upsert=True,
            )

    print(f"[seed]  users             : {len(user_docs)}")
    print(f"[seed]  watch_history     : {len(history_rows_all)}")
    print(f"[seed]  watchlist favorites: {len(favorites_rows_all)}")
    print(f"[seed]  random seed       : {SEED}")
    print(f"[seed]  [ok] done. Login any demo_user_NNN@vozflix.demo with password 'Demo1234!'")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo users for recommender training.")
    parser.add_argument("--wipe", action="store_true",
                        help="Only wipe is_demo_seed users + their history + favorites, then exit.")
    parser.add_argument("--no-wipe", action="store_true",
                        help="Skip the wipe step at the start of a seed run.")
    args = parser.parse_args()

    await connect_to_mongo()
    db = get_database()
    try:
        if args.wipe:
            await wipe(db)
        else:
            if not args.no_wipe:
                await wipe(db)
            await seed(db)
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
