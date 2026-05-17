"""
Content-based recommender — inference layer.

Loads TF-IDF artifacts produced by `scripts/train_recommender.py` lazily on
first call (one matrix per content type: "movie", "series"). Computes
cosine similarity via sparse dot-product (mirrors Part 2 of the source
notebook); no dense N x N matrix is ever materialised.

Returns tmdb_ids only — callers hydrate full docs from MongoDB through the
existing library_service / movie_service paths.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from scipy import sparse

ARTIFACT_ROOT = Path(__file__).resolve().parents[2] / "data" / "recommender"
EXPECTED_KIND = "tfidf_overview_genres_v1"
SUBDIR_BY_TYPE: dict[str, str] = {"movie": "movies", "series": "series"}
SUPPORTED_CONTENT_TYPES: tuple[str, ...] = tuple(SUBDIR_BY_TYPE.keys())

_STATE: dict[str, dict] = {}


class RecommenderNotTrained(RuntimeError):
    """Artifacts for the requested content_type haven't been built yet."""


def _validate_content_type(content_type: str) -> None:
    if content_type not in SUBDIR_BY_TYPE:
        raise ValueError(
            f"unsupported content_type {content_type!r}; "
            f"expected one of {SUPPORTED_CONTENT_TYPES}"
        )


def _load(content_type: str) -> None:
    _validate_content_type(content_type)
    base = ARTIFACT_ROOT / SUBDIR_BY_TYPE[content_type]
    metadata_path = base / "metadata.json"
    if not metadata_path.exists():
        raise RecommenderNotTrained(
            f"No artifacts at {base}. Run scripts/train_recommender.py."
        )

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("kind") != EXPECTED_KIND:
        raise RuntimeError(
            f"Artifact kind mismatch for {content_type}: "
            f"expected {EXPECTED_KIND!r}, got {metadata.get('kind')!r}. "
            "Re-run scripts/train_recommender.py."
        )
    if metadata.get("content_type") != content_type:
        raise RuntimeError(
            f"Artifact content_type mismatch at {base}: "
            f"expected {content_type!r}, got {metadata.get('content_type')!r}."
        )

    vectorizer = joblib.load(base / "vectorizer.joblib")
    matrix = sparse.load_npz(base / "tfidf_matrix.npz")
    matrix = matrix.tocsr()  # row slicing is O(1) on CSR
    index = json.loads((base / "item_index.json").read_text(encoding="utf-8"))
    tmdb_ids = [int(x) for x in index["tmdb_ids"]]
    id_to_idx = {tid: i for i, tid in enumerate(tmdb_ids)}

    _STATE[content_type] = {
        "vectorizer": vectorizer,
        "matrix": matrix,
        "tmdb_ids": tmdb_ids,
        "id_to_idx": id_to_idx,
        "metadata": metadata,
        "loaded_at": datetime.now(timezone.utc).isoformat(),
    }


def similar_to(content_type: str, tmdb_id: int, top_n: int = 10) -> list[int]:
    """Return the top-N most similar tmdb_ids, excluding the query item itself.

    Raises RecommenderNotTrained if artifacts for this content_type haven't been
    built. Returns [] if the tmdb_id isn't in the trained index (e.g. seeded
    after the last training run, or hidden at train time).
    """
    _validate_content_type(content_type)
    if content_type not in _STATE:
        _load(content_type)
    state = _STATE[content_type]

    idx = state["id_to_idx"].get(int(tmdb_id))
    if idx is None:
        return []

    matrix: sparse.csr_matrix = state["matrix"]
    query = matrix[idx]
    sims = query.dot(matrix.T).toarray().ravel()
    sims[idx] = -1.0  # exclude self

    if top_n >= len(sims):
        order = np.argsort(sims)[::-1]
    else:
        top = np.argpartition(sims, -top_n)[-top_n:]
        order = top[np.argsort(sims[top])[::-1]]

    tmdb_ids = state["tmdb_ids"]
    return [int(tmdb_ids[i]) for i in order if sims[i] > 0]


def reload(content_type: str | None = None) -> None:
    """Drop cached state so the next call re-reads from disk.

    Pass None to drop all; pass "movie" / "series" to drop one. Doesn't load
    eagerly — load happens on the next similar_to() call.
    """
    if content_type is None:
        _STATE.clear()
        return
    _validate_content_type(content_type)
    _STATE.pop(content_type, None)


def loaded_state() -> dict[str, dict]:
    """Diagnostic: which content types are loaded, and their metadata. No load."""
    return {ct: {"metadata": s["metadata"], "loaded_at": s["loaded_at"]}
            for ct, s in _STATE.items()}
