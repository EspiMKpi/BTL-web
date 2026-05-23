"""
Train FP-Growth association rules for the "Vì bạn đã xem ..." rail.

Builds one rule table per content_type (movies, series). For each content_type:

  1. Pull watch_history rows that are POSITIVE signals (completed=True OR
     progress_seconds >= 1800).
  2. Group by user_id → transactions. Drop transactions with < 2 items.
  3. Mine frequent itemsets (mlxtend.frequent_patterns.fpgrowth), then derive
     association rules with min_confidence threshold.
  4. Keep only 1-item antecedents (so inference is a single dict lookup) and
     rank consequents by lift desc. Cap top-20 consequents / antecedent.
  5. Write artifacts to data/recommender/fpgrowth/{movies|series}/.

Run from fastapi-backend/:
    .venv\\Scripts\\python.exe scripts\\train_fpgrowth.py
    .venv\\Scripts\\python.exe scripts\\train_fpgrowth.py --min-support 0.03

If --min-support results in < 10 rules, retries with progressively smaller
values down to 0.01. This guards demo runs where the seed data has thinner
co-watch overlap than expected.
"""

import argparse
import asyncio
import io
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Windows console defaults to cp1252 — force UTF-8 so non-ASCII path chars
# and arrow glyphs in our own log lines don't crash the script.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)

import pandas as pd
from mlxtend.frequent_patterns import association_rules, fpgrowth
from mlxtend.preprocessing import TransactionEncoder

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import close_mongo_connection, connect_to_mongo, get_database

ARTIFACT_ROOT = Path(__file__).resolve().parents[1] / "data" / "recommender" / "fpgrowth"
KIND = "fpgrowth_v1"

# Same positive-signal threshold as the inference layer / seed script. Keep
# in sync — drifting these creates silent train/serve skew.
MIN_PROGRESS_SECONDS = 1800

# Per-antecedent cap (rules.json size bound).
TOP_K_CONSEQUENTS = 20
# If the configured min_support is too strict, halve it until we get at least
# this many rules — or until we hit MIN_SUPPORT_FLOOR, whichever first.
MIN_RULES_TARGET = 10
MIN_SUPPORT_FLOOR = 0.01

SUBDIR_BY_TYPE: dict[str, str] = {"movie": "movies", "series": "series"}


async def _build_transactions(db, content_type: str) -> list[list[int]]:
    """Per-user lists of distinct positive-signal tmdb_ids."""
    cursor = db.watch_history.aggregate([
        {"$match": {
            "content_type": content_type,
            "$or": [
                {"completed": True},
                {"progress_seconds": {"$gte": MIN_PROGRESS_SECONDS}},
            ],
        }},
        {"$group": {
            "_id": "$user_id",
            "tmdb_ids": {"$addToSet": "$tmdb_id"},
        }},
    ])
    transactions: list[list[int]] = []
    async for row in cursor:
        ids = [int(t) for t in row["tmdb_ids"] if t is not None]
        if len(ids) >= 2:
            transactions.append(ids)
    return transactions


def _mine_rules(
    transactions: list[list[int]],
    min_support: float,
    min_confidence: float,
) -> tuple[pd.DataFrame, float]:
    """Mine rules at *min_support*; if too few, halve support down to floor."""
    te = TransactionEncoder()
    one_hot = te.fit_transform(transactions)
    df = pd.DataFrame(one_hot, columns=te.columns_)

    support = min_support
    while True:
        itemsets = fpgrowth(df, min_support=support, use_colnames=True)
        if itemsets.empty:
            rules_df = pd.DataFrame()
        else:
            rules_df = association_rules(
                itemsets, metric="confidence", min_threshold=min_confidence,
            )

        # Filter to 1-item antecedents only (lookup table shape).
        if not rules_df.empty:
            rules_df = rules_df[rules_df["antecedents"].apply(lambda s: len(s) == 1)]

        if len(rules_df) >= MIN_RULES_TARGET or support <= MIN_SUPPORT_FLOOR:
            return rules_df, support
        support = max(MIN_SUPPORT_FLOOR, support / 2)
        print(f"    only {len(rules_df)} rules at support={support * 2:.4f}; "
              f"retrying with support={support:.4f}")


def _to_lookup(rules_df: pd.DataFrame) -> dict[int, list[int]]:
    """Group rules by 1-item antecedent and sort consequents by lift desc."""
    grouped: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for _, row in rules_df.iterrows():
        ante = next(iter(row["antecedents"]))           # frozenset of 1
        for cons in row["consequents"]:
            grouped[int(ante)].append((int(cons), float(row["lift"])))

    lookup: dict[int, list[int]] = {}
    for ante, items in grouped.items():
        # Dedupe consequents (multiple rules can pair the same items via
        # different conditioning) — keep the max-lift instance.
        best: dict[int, float] = {}
        for cons, lift in items:
            if cons == ante:
                continue
            if lift > best.get(cons, float("-inf")):
                best[cons] = lift
        ranked = sorted(best.items(), key=lambda kv: -kv[1])
        lookup[ante] = [c for c, _ in ranked[:TOP_K_CONSEQUENTS]]
    return lookup


def _write_artifacts(
    content_type: str,
    lookup: dict[int, list[int]],
    *,
    used_support: float,
    requested_support: float,
    min_confidence: float,
    n_transactions: int,
) -> Path:
    subdir = ARTIFACT_ROOT / SUBDIR_BY_TYPE[content_type]
    subdir.mkdir(parents=True, exist_ok=True)

    (subdir / "rules.json").write_text(
        json.dumps({str(k): v for k, v in lookup.items()}, ensure_ascii=False),
        encoding="utf-8",
    )
    (subdir / "metadata.json").write_text(
        json.dumps({
            "kind": KIND,
            "content_type": content_type,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "min_support_requested": requested_support,
            "min_support_used": used_support,
            "min_confidence": min_confidence,
            "min_progress_seconds": MIN_PROGRESS_SECONDS,
            "top_k_consequents": TOP_K_CONSEQUENTS,
            "n_transactions": n_transactions,
            "n_antecedents": len(lookup),
            "n_total_pairs": sum(len(v) for v in lookup.values()),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return subdir


async def _train_one(db, content_type: str, min_support: float, min_confidence: float) -> None:
    print(f"\n[fpgrowth] === content_type={content_type} ===")
    transactions = await _build_transactions(db, content_type)
    print(f"[fpgrowth] usable transactions: {len(transactions)}")
    if len(transactions) < 2:
        print("[fpgrowth] [!]  not enough transactions to mine rules — skipping. "
              "Run scripts/seed_demo_users.py first.")
        return

    rules_df, used_support = _mine_rules(transactions, min_support, min_confidence)
    print(f"[fpgrowth] mined {len(rules_df)} rules at support={used_support:.4f}, "
          f"confidence={min_confidence:.2f}")

    if rules_df.empty:
        # Still write artifacts so the inference layer doesn't crash with
        # RecommenderNotTrained; just an empty rules.json (every item is
        # cold-start -> []).
        lookup: dict[int, list[int]] = {}
        print("[fpgrowth] [!]  no rules survived filters — writing empty rules.json")
    else:
        lookup = _to_lookup(rules_df)
        print(f"[fpgrowth] {len(lookup)} unique antecedents, "
              f"{sum(len(v) for v in lookup.values())} total pairs")

    out_dir = _write_artifacts(
        content_type, lookup,
        used_support=used_support,
        requested_support=min_support,
        min_confidence=min_confidence,
        n_transactions=len(transactions),
    )
    print(f"[fpgrowth] artifacts → {out_dir}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Train FP-Growth recommender.")
    parser.add_argument("--min-support", type=float, default=0.05,
                        help="Initial min_support for fpgrowth (default 0.05). "
                             "Halved down to %.2f if < %d rules survive." %
                             (MIN_SUPPORT_FLOOR, MIN_RULES_TARGET))
    parser.add_argument("--min-confidence", type=float, default=0.2,
                        help="min_confidence for association_rules (default 0.2).")
    parser.add_argument("--content-type", choices=("movie", "series", "both"),
                        default="both")
    args = parser.parse_args()

    await connect_to_mongo()
    db = get_database()
    try:
        types = ("movie", "series") if args.content_type == "both" else (args.content_type,)
        for ct in types:
            await _train_one(db, ct, args.min_support, args.min_confidence)
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
