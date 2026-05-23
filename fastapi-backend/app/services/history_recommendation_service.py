"""
GRU4Rec sequential recommender — inference layer.

Predicts the next-N items a user is most likely to watch given their last
MAX_SEQ_LEN positive interactions, sorted oldest → newest. Powers
GET /api/recommendations/next/{content_type}.

Artifact layout per content_type:
    data/recommender/gru4rec/{movies|series}/
        model.pt          torch state_dict
        item_vocab.json   { "tmdb_to_idx": {<tmdb_id>: <idx>}, "idx_to_tmdb": [<tmdb_id>, ...] }
        metadata.json     { kind, content_type, embed_dim, hidden_dim, max_seq_len, ... }

The first prediction call for each content_type lazy-loads the model + vocab.
TTLCache (10 min) shields the model from repeated forward passes for the
same (user_id, content_type, limit) tuple — the user's watch_history doesn't
change minute-to-minute and torch CPU inference isn't free.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import torch
import torch.nn as nn
from cachetools import TTLCache

from app.database import get_database
from app.services.recommendation_service import (
    RecommenderNotTrained,
    SUPPORTED_CONTENT_TYPES,
)

logger = logging.getLogger(__name__)

ARTIFACT_ROOT = Path(__file__).resolve().parents[2] / "data" / "recommender" / "gru4rec"
EXPECTED_KIND = "gru4rec_v1"
SUBDIR_BY_TYPE: dict[str, str] = {"movie": "movies", "series": "series"}

# Same positive signal threshold as the previous history recommender (kept so
# seed_demo_users.py and training share one definition).
MIN_PROGRESS_SECONDS = 1800
# Below this many positive interactions, return [] (frontend hides the rail).
MIN_SEQUENCE_LEN = 3

_STATE: dict[str, dict] = {}
# Predictions cache: key = (user_id, content_type, limit). 10 min TTL is short
# enough that a user's freshly-watched item flows through after a coffee break.
_predict_cache: TTLCache = TTLCache(maxsize=512, ttl=600)


class GRU4RecModel(nn.Module):
    """Single-layer GRU over item embeddings. Output = logits over the vocab.

    `vocab_size` MUST include the pad slot at index 0 (so the embedding matrix
    has one extra row). We never predict index 0 — `forward` masks it.
    """

    def __init__(self, vocab_size: int, embed_dim: int = 64, hidden_dim: int = 128):
        super().__init__()
        self.item_emb = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.gru = nn.GRU(embed_dim, hidden_dim, batch_first=True)
        self.head = nn.Linear(hidden_dim, vocab_size)

    def forward(self, seq: torch.Tensor) -> torch.Tensor:
        # seq: (B, T) int64 with 0 = pad
        emb = self.item_emb(seq)          # (B, T, E)
        out, _ = self.gru(emb)            # (B, T, H)
        last = out[:, -1, :]              # (B, H) — final timestep
        logits = self.head(last)          # (B, V)
        logits[:, 0] = float("-inf")      # never predict pad
        return logits


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
    vocab_path = base / "item_vocab.json"
    model_path = base / "model.pt"
    if not all(p.exists() for p in (metadata_path, vocab_path, model_path)):
        raise RecommenderNotTrained(
            f"No GRU4Rec artifacts at {base}. Run scripts/train_gru4rec.py."
        )

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("kind") != EXPECTED_KIND:
        raise RuntimeError(
            f"Artifact kind mismatch for {content_type}: "
            f"expected {EXPECTED_KIND!r}, got {metadata.get('kind')!r}. "
            "Re-run scripts/train_gru4rec.py."
        )
    if metadata.get("content_type") != content_type:
        raise RuntimeError(
            f"Artifact content_type mismatch at {base}: "
            f"expected {content_type!r}, got {metadata.get('content_type')!r}."
        )

    vocab_raw = json.loads(vocab_path.read_text(encoding="utf-8"))
    tmdb_to_idx: dict[int, int] = {int(k): int(v) for k, v in vocab_raw["tmdb_to_idx"].items()}
    idx_to_tmdb: list[int] = [int(x) for x in vocab_raw["idx_to_tmdb"]]
    vocab_size = len(idx_to_tmdb)  # includes pad at index 0

    model = GRU4RecModel(
        vocab_size=vocab_size,
        embed_dim=int(metadata["embed_dim"]),
        hidden_dim=int(metadata["hidden_dim"]),
    )
    state = torch.load(model_path, map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    model.eval()

    _STATE[content_type] = {
        "model": model,
        "tmdb_to_idx": tmdb_to_idx,
        "idx_to_tmdb": idx_to_tmdb,
        "max_seq_len": int(metadata["max_seq_len"]),
        "metadata": metadata,
        "loaded_at": datetime.now(timezone.utc).isoformat(),
    }


async def _fetch_recent_positive_items(
    user_id: str,
    content_type: str,
    limit: int,
) -> list[int]:
    """Most recent (<= limit) positive-signal tmdb_ids, oldest -> newest."""
    db = get_database()
    cursor = db.watch_history.aggregate([
        {"$match": {
            "user_id": user_id,
            "content_type": content_type,
            "$or": [
                {"completed": True},
                {"progress_seconds": {"$gte": MIN_PROGRESS_SECONDS}},
            ],
        }},
        {"$sort": {"last_watched_at": -1}},
        {"$group": {
            "_id": "$tmdb_id",
            "last_watched_at": {"$first": "$last_watched_at"},
        }},
        {"$sort": {"last_watched_at": -1}},
        {"$limit": limit},
    ])
    rows = [row async for row in cursor]
    # We sorted desc to get the most recent N, now flip to oldest -> newest
    # because GRU4Rec consumes the sequence in chronological order.
    rows.reverse()
    return [int(row["_id"]) for row in rows]


def _predict(
    state: dict,
    seq_idx: list[int],
    seen_idx: set[int],
    top_n: int,
) -> list[int]:
    """Forward + topk + mask seen items. Returns tmdb_ids (recommender order)."""
    max_len = state["max_seq_len"]
    if len(seq_idx) > max_len:
        seq_idx = seq_idx[-max_len:]
    # Left-pad with 0 so the GRU sees the sequence ending at the last timestep.
    padded = [0] * (max_len - len(seq_idx)) + seq_idx
    seq = torch.tensor([padded], dtype=torch.long)

    with torch.no_grad():
        logits = state["model"](seq)  # (1, V)

    logits = logits.squeeze(0)
    # Mask out seen items so we don't recommend back what the user already touched.
    for idx in seen_idx:
        if 0 <= idx < logits.shape[0]:
            logits[idx] = float("-inf")

    k = min(top_n, logits.shape[0])
    top_idx = torch.topk(logits, k).indices.tolist()
    idx_to_tmdb = state["idx_to_tmdb"]
    out: list[int] = []
    for idx in top_idx:
        # Skip pad (already -inf) and any -inf-masked entries.
        if idx == 0:
            continue
        out.append(int(idx_to_tmdb[idx]))
    return out[:top_n]


async def next_in_sequence(user_id: str, content_type: str, n: int = 10) -> list[int]:
    """Return up to *n* tmdb_ids predicted to come next in the user's sequence.

    Cold-start contract: returns [] when the user has fewer than
    MIN_SEQUENCE_LEN positive interactions known to the trained vocab. The
    frontend hides the rail in that case.

    Raises `RecommenderNotTrained` if the artifact for *content_type* hasn't
    been built yet.
    """
    _validate_content_type(content_type)

    cache_key = (user_id, content_type, n)
    cached = _predict_cache.get(cache_key)
    if cached is not None:
        return cached

    if content_type not in _STATE:
        _load(content_type)
    state = _STATE[content_type]

    # Pull a bit more than max_seq_len so OOV items can be dropped without
    # leaving us short. Anything beyond max_seq_len gets truncated in _predict.
    fetch_limit = state["max_seq_len"] * 2
    recent_ids = await _fetch_recent_positive_items(user_id, content_type, fetch_limit)

    tmdb_to_idx: dict[int, int] = state["tmdb_to_idx"]
    seq_idx = [tmdb_to_idx[t] for t in recent_ids if t in tmdb_to_idx]
    if len(seq_idx) < MIN_SEQUENCE_LEN:
        _predict_cache[cache_key] = []
        return []

    seen_idx: set[int] = set(seq_idx)
    result = _predict(state, seq_idx, seen_idx, top_n=n)
    _predict_cache[cache_key] = result
    return result


def reload(content_type: str | None = None) -> None:
    """Drop cached model state + prediction cache."""
    _predict_cache.clear()
    if content_type is None:
        _STATE.clear()
        return
    _validate_content_type(content_type)
    _STATE.pop(content_type, None)


def loaded_state() -> dict[str, dict]:
    """Diagnostic: which content types are loaded, and their metadata."""
    return {
        ct: {"metadata": s["metadata"], "loaded_at": s["loaded_at"]}
        for ct, s in _STATE.items()
    }
