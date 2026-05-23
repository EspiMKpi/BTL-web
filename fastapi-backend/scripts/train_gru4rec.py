"""
Train a small GRU4Rec model per content_type for the "Up Next" rail.

For each content_type:
  1. Pull every user's chronological positive-signal watch sequence
     (completed=True OR progress_seconds >= 1800), deduped per (user, tmdb_id)
     to keep the most-recent occurrence.
  2. Build a 1-based item vocab (index 0 = pad).
  3. Generate sliding-window (context, target) pairs with left padding.
  4. Train a single-layer GRU with cross-entropy loss against the next item.
  5. Save state_dict + vocab + metadata under
     data/recommender/gru4rec/{movies|series}/.

Tuned for ~40 demo users × 15-40 watches each. CPU-only PyTorch is fine.
Set --epochs 0 for a dry run that builds the vocab + writes a randomly
initialised model (useful when only the artifact layout matters).
"""

import argparse
import asyncio
import io
import json
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 stdout/stderr so log lines with arrows / non-ASCII chars don't
# crash on Windows cp1252 consoles.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import close_mongo_connection, connect_to_mongo, get_database
from app.services.history_recommendation_service import GRU4RecModel

ARTIFACT_ROOT = Path(__file__).resolve().parents[1] / "data" / "recommender" / "gru4rec"
KIND = "gru4rec_v1"

# Hyperparameters (kept conservative — small data, no overfitting drama).
EMBED_DIM = 64
HIDDEN_DIM = 128
MAX_SEQ_LEN = 20
BATCH_SIZE = 64
LR = 1e-3
N_EPOCHS = 20
SEED = 42

# Keep in sync with seed script and inference layer.
MIN_PROGRESS_SECONDS = 1800
# Need at least this many positive interactions to contribute training pairs.
MIN_USER_SEQUENCE_LEN = 3

SUBDIR_BY_TYPE: dict[str, str] = {"movie": "movies", "series": "series"}


# ── Data plumbing ─────────────────────────────────────────────────────────

class SequenceDataset(Dataset):
    """(context, target) pairs with left-padded fixed-length contexts.

    Stored as numpy int64 arrays so PyTorch's default collate copies cleanly.
    """

    def __init__(self, contexts: np.ndarray, targets: np.ndarray):
        assert contexts.dtype == np.int64
        assert targets.dtype == np.int64
        self.contexts = contexts
        self.targets = targets

    def __len__(self) -> int:
        return len(self.targets)

    def __getitem__(self, idx: int):
        return self.contexts[idx], self.targets[idx]


async def _fetch_user_sequences(db, content_type: str) -> list[list[int]]:
    """Return [[tmdb_id ordered oldest -> newest], ...] across all users.

    Dedupes by (user, tmdb_id) — keep the most recent occurrence per title so
    the user model isn't biased by people re-watching the same movie three
    times. We collapse on tmdb_id because the recommender is item-level, not
    episode-level.
    """
    cursor = db.watch_history.aggregate([
        {"$match": {
            "content_type": content_type,
            "$or": [
                {"completed": True},
                {"progress_seconds": {"$gte": MIN_PROGRESS_SECONDS}},
            ],
        }},
        # Most recent first so $first picks the latest timestamp per title.
        {"$sort": {"last_watched_at": -1}},
        {"$group": {
            "_id": {"user_id": "$user_id", "tmdb_id": "$tmdb_id"},
            "last_watched_at": {"$first": "$last_watched_at"},
        }},
        # Resort ascending by user → time so the per-user chronology is correct.
        {"$sort": {"_id.user_id": 1, "last_watched_at": 1}},
        {"$group": {
            "_id": "$_id.user_id",
            "items": {"$push": {
                "tmdb_id": "$_id.tmdb_id",
                "ts": "$last_watched_at",
            }},
        }},
    ])
    sequences: list[list[int]] = []
    async for row in cursor:
        # row['items'] is already chronologically ordered (asc) per the prior
        # $sort + $push.
        seq = [int(it["tmdb_id"]) for it in row["items"]]
        if len(seq) >= MIN_USER_SEQUENCE_LEN:
            sequences.append(seq)
    return sequences


def _build_vocab(sequences: list[list[int]]) -> tuple[dict[int, int], list[int]]:
    """Return (tmdb_to_idx, idx_to_tmdb). Index 0 is RESERVED for pad."""
    seen: set[int] = set()
    ordered: list[int] = []
    for seq in sequences:
        for t in seq:
            if t not in seen:
                seen.add(t)
                ordered.append(t)
    # idx_to_tmdb[0] = 0 sentinel (pad). Real items start at index 1.
    idx_to_tmdb = [0] + ordered
    tmdb_to_idx = {t: i + 1 for i, t in enumerate(ordered)}
    return tmdb_to_idx, idx_to_tmdb


def _build_training_pairs(
    sequences: list[list[int]],
    tmdb_to_idx: dict[int, int],
    max_seq_len: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Sliding window: for each position t >= 1 in a sequence, emit
    (sequence[max(0, t-max_seq_len):t], sequence[t])."""
    contexts: list[list[int]] = []
    targets: list[int] = []
    for seq in sequences:
        idx_seq = [tmdb_to_idx[t] for t in seq if t in tmdb_to_idx]
        for t in range(1, len(idx_seq)):
            ctx = idx_seq[max(0, t - max_seq_len):t]
            tgt = idx_seq[t]
            # Left pad to max_seq_len with index 0.
            padded = [0] * (max_seq_len - len(ctx)) + ctx
            contexts.append(padded)
            targets.append(tgt)
    if not contexts:
        return (
            np.zeros((0, max_seq_len), dtype=np.int64),
            np.zeros((0,), dtype=np.int64),
        )
    return (
        np.asarray(contexts, dtype=np.int64),
        np.asarray(targets, dtype=np.int64),
    )


# ── Training ──────────────────────────────────────────────────────────────

def _train(
    model: GRU4RecModel,
    loader: DataLoader,
    n_epochs: int,
    lr: float,
    device: torch.device,
) -> list[float]:
    """Train in-place. Returns per-epoch mean loss for the metadata file."""
    optim = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.CrossEntropyLoss()
    epoch_losses: list[float] = []
    model.train()
    for epoch in range(n_epochs):
        running, n = 0.0, 0
        for ctx, tgt in loader:
            ctx = ctx.to(device)
            tgt = tgt.to(device)
            optim.zero_grad()
            logits = model(ctx)               # (B, V)
            loss = loss_fn(logits, tgt)
            loss.backward()
            optim.step()
            running += float(loss.item()) * len(tgt)
            n += len(tgt)
        epoch_loss = running / max(n, 1)
        epoch_losses.append(epoch_loss)
        print(f"[gru4rec]   epoch {epoch + 1:>2}/{n_epochs}  loss={epoch_loss:.4f}")
    model.eval()
    return epoch_losses


def _write_artifacts(
    content_type: str,
    model: GRU4RecModel,
    tmdb_to_idx: dict[int, int],
    idx_to_tmdb: list[int],
    *,
    embed_dim: int,
    hidden_dim: int,
    max_seq_len: int,
    n_sequences: int,
    n_pairs: int,
    epoch_losses: list[float],
) -> Path:
    subdir = ARTIFACT_ROOT / SUBDIR_BY_TYPE[content_type]
    subdir.mkdir(parents=True, exist_ok=True)

    torch.save(model.state_dict(), subdir / "model.pt")
    (subdir / "item_vocab.json").write_text(
        json.dumps({
            "tmdb_to_idx": {str(k): v for k, v in tmdb_to_idx.items()},
            "idx_to_tmdb": idx_to_tmdb,
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (subdir / "metadata.json").write_text(
        json.dumps({
            "kind": KIND,
            "content_type": content_type,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "embed_dim": embed_dim,
            "hidden_dim": hidden_dim,
            "max_seq_len": max_seq_len,
            "n_items": len(idx_to_tmdb) - 1,  # excluding pad
            "n_user_sequences": n_sequences,
            "n_training_pairs": n_pairs,
            "epoch_losses": epoch_losses,
            "min_progress_seconds": MIN_PROGRESS_SECONDS,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return subdir


async def _train_one(
    db,
    content_type: str,
    *,
    embed_dim: int,
    hidden_dim: int,
    max_seq_len: int,
    batch_size: int,
    n_epochs: int,
    lr: float,
) -> None:
    print(f"\n[gru4rec] === content_type={content_type} ===")
    sequences = await _fetch_user_sequences(db, content_type)
    print(f"[gru4rec] usable user sequences: {len(sequences)}")
    if not sequences:
        print("[gru4rec] [!]  no sequences. Run scripts/seed_demo_users.py first.")
        return

    tmdb_to_idx, idx_to_tmdb = _build_vocab(sequences)
    print(f"[gru4rec] vocab size (incl. pad): {len(idx_to_tmdb)}")

    contexts, targets = _build_training_pairs(sequences, tmdb_to_idx, max_seq_len)
    print(f"[gru4rec] training pairs: {len(targets)}")
    if len(targets) == 0:
        print("[gru4rec] [!]  no training pairs after windowing — skipping training.")
        # Still write artifacts (untrained model) so inference doesn't crash.
        model = GRU4RecModel(vocab_size=len(idx_to_tmdb), embed_dim=embed_dim, hidden_dim=hidden_dim)
        _write_artifacts(
            content_type, model, tmdb_to_idx, idx_to_tmdb,
            embed_dim=embed_dim, hidden_dim=hidden_dim, max_seq_len=max_seq_len,
            n_sequences=len(sequences), n_pairs=0, epoch_losses=[],
        )
        return

    device = torch.device("cpu")
    model = GRU4RecModel(
        vocab_size=len(idx_to_tmdb), embed_dim=embed_dim, hidden_dim=hidden_dim,
    ).to(device)

    epoch_losses: list[float] = []
    if n_epochs > 0:
        # Cap batch size at dataset size to avoid empty loader issues.
        effective_bs = min(batch_size, len(targets))
        ds = SequenceDataset(contexts, targets)
        loader = DataLoader(
            ds, batch_size=effective_bs, shuffle=True, drop_last=False,
        )
        epoch_losses = _train(model, loader, n_epochs, lr, device)
    else:
        print("[gru4rec] --epochs 0 — skipping training, saving randomly initialised model.")

    out_dir = _write_artifacts(
        content_type, model, tmdb_to_idx, idx_to_tmdb,
        embed_dim=embed_dim, hidden_dim=hidden_dim, max_seq_len=max_seq_len,
        n_sequences=len(sequences), n_pairs=int(len(targets)),
        epoch_losses=epoch_losses,
    )
    print(f"[gru4rec] artifacts → {out_dir}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Train GRU4Rec recommender.")
    parser.add_argument("--epochs", type=int, default=N_EPOCHS)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--embed-dim", type=int, default=EMBED_DIM)
    parser.add_argument("--hidden-dim", type=int, default=HIDDEN_DIM)
    parser.add_argument("--max-seq-len", type=int, default=MAX_SEQ_LEN)
    parser.add_argument("--lr", type=float, default=LR)
    parser.add_argument("--content-type", choices=("movie", "series", "both"),
                        default="both")
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    await connect_to_mongo()
    db = get_database()
    try:
        types = ("movie", "series") if args.content_type == "both" else (args.content_type,)
        for ct in types:
            await _train_one(
                db, ct,
                embed_dim=args.embed_dim,
                hidden_dim=args.hidden_dim,
                max_seq_len=args.max_seq_len,
                batch_size=args.batch_size,
                n_epochs=args.epochs,
                lr=args.lr,
            )
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
