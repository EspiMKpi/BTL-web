"""
Train the content-based recommender artifacts.

Reads movies and series from MongoDB, builds a TF-IDF model over
`overview + genre names` for each, and writes per-content-type artifacts under
`fastapi-backend/data/recommender/{movies,series}/`:
    - vectorizer.joblib
    - tfidf_matrix.npz
    - item_index.json
    - metadata.json

Run from the fastapi-backend/ directory:
    .\.venv\Scripts\python.exe scripts\train_recommender.py

Idempotent. Hidden items (is_hidden=True) are excluded. The `user_ratings`
collection is intentionally NOT read — training features are TMDB-sourced only
(see RECOMMENDER_PLAN.md, Scope discipline).

Movie→movie and series→series recommendations stay separate (one matrix per
collection); there is no cross-type similarity.
"""

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import close_mongo_connection, connect_to_mongo, get_database

ARTIFACT_ROOT = Path(__file__).resolve().parents[1] / "data" / "recommender"
KIND = "tfidf_overview_genres_v1"
MAX_FEATURES = 25_000


@dataclass(frozen=True)
class CorpusConfig:
    content_type: str       # "movie" | "series" — written into metadata.json
    collection: str         # MongoDB collection name
    title_field: str        # "title" for movies, "name" for series
    subdir: str             # subdirectory name under ARTIFACT_ROOT


CONFIGS: list[CorpusConfig] = [
    CorpusConfig(content_type="movie", collection="movies", title_field="title", subdir="movies"),
    CorpusConfig(content_type="series", collection="series", title_field="name", subdir="series"),
]


def build_soup(overview: str, genre_names: list[str]) -> str:
    """`overview + genre names`, space-joined. Empty if both are empty."""
    parts = []
    if overview:
        parts.append(overview)
    if genre_names:
        parts.append(" ".join(genre_names))
    return " ".join(parts).strip()


async def load_corpus(cfg: CorpusConfig) -> tuple[list[int], list[str], list[str]]:
    """Return (tmdb_ids, titles, soups) for all visible items with non-empty soup."""
    db = get_database()
    projection = {
        "_id": 0,
        "tmdb_id": 1,
        cfg.title_field: 1,
        "overview": 1,
        "genres.name": 1,
        "is_hidden": 1,
    }
    cursor = db[cfg.collection].find({"is_hidden": {"$ne": True}}, projection)

    tmdb_ids: list[int] = []
    titles: list[str] = []
    soups: list[str] = []
    skipped_no_id = 0
    skipped_empty = 0

    async for doc in cursor:
        tmdb_id = doc.get("tmdb_id")
        if tmdb_id is None:
            skipped_no_id += 1
            continue
        overview = (doc.get("overview") or "").strip()
        genre_names = [g.get("name", "") for g in (doc.get("genres") or []) if g.get("name")]
        soup = build_soup(overview, genre_names)
        if not soup:
            skipped_empty += 1
            continue
        tmdb_ids.append(int(tmdb_id))
        titles.append(doc.get(cfg.title_field) or "")
        soups.append(soup)

    if skipped_no_id:
        print(f"  Skipped {skipped_no_id} docs with no tmdb_id")
    if skipped_empty:
        print(f"  Skipped {skipped_empty} docs with empty overview + genres")
    return tmdb_ids, titles, soups


def fit_and_persist(
    cfg: CorpusConfig,
    tmdb_ids: list[int],
    titles: list[str],
    soups: list[str],
) -> dict:
    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=MAX_FEATURES,
        dtype=np.float32,
    )
    matrix = vectorizer.fit_transform(soups)

    out_dir = ARTIFACT_ROOT / cfg.subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizer, out_dir / "vectorizer.joblib")
    sparse.save_npz(out_dir / "tfidf_matrix.npz", matrix)
    (out_dir / "item_index.json").write_text(
        json.dumps({"tmdb_ids": tmdb_ids, "titles": titles}, ensure_ascii=False),
        encoding="utf-8",
    )
    metadata = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "content_type": cfg.content_type,
        "n_items": len(tmdb_ids),
        "vocab_size": len(vectorizer.vocabulary_),
        "kind": KIND,
    }
    (out_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )
    return metadata


async def train_one(cfg: CorpusConfig) -> dict | None:
    print(f"\n[{cfg.content_type}] Loading from `{cfg.collection}`...")
    t0 = time.monotonic()
    tmdb_ids, titles, soups = await load_corpus(cfg)
    print(f"  {len(tmdb_ids)} items loaded in {time.monotonic() - t0:.2f}s")

    if not tmdb_ids:
        print(f"  No trainable {cfg.content_type} items found — skipping. "
              f"Run scripts/seed_tmdb.py first if the collection is empty.")
        return None

    print(f"[{cfg.content_type}] Fitting TF-IDF (max_features={MAX_FEATURES})...")
    t1 = time.monotonic()
    metadata = fit_and_persist(cfg, tmdb_ids, titles, soups)
    print(f"  fit + persist done in {time.monotonic() - t1:.2f}s")
    print(f"  artifacts -> {ARTIFACT_ROOT / cfg.subdir}")
    return metadata


async def main() -> None:
    print("Connecting to MongoDB...")
    await connect_to_mongo()
    try:
        results: dict[str, dict] = {}
        for cfg in CONFIGS:
            meta = await train_one(cfg)
            if meta:
                results[cfg.content_type] = meta

        print("\n=== Summary ===")
        print(json.dumps(results, indent=2))
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
