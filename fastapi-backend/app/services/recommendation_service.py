"""
FP-Growth recommender — inference layer.

Looks up association rules (1-item antecedent → ranked consequents) built by
`scripts/train_fpgrowth.py`. Powers GET /api/recommendations/related/{type}/{tmdb_id}.

Artifact layout per content_type:
    data/recommender/fpgrowth/{movies|series}/
        rules.json      { "<tmdb_id>": [tmdb_id, ...] }
        metadata.json   { kind, content_type, min_support, min_confidence, ... }

Lazy load on first call, per content_type. Returns [] when the tmdb_id has no
rule (cold-start item), and raises RecommenderNotTrained when the artifact
directory hasn't been built yet.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ARTIFACT_ROOT = Path(__file__).resolve().parents[2] / "data" / "recommender" / "fpgrowth"
EXPECTED_KIND = "fpgrowth_v1"
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
    rules_path = base / "rules.json"
    if not metadata_path.exists() or not rules_path.exists():
        raise RecommenderNotTrained(
            f"No FP-Growth artifacts at {base}. Run scripts/train_fpgrowth.py."
        )

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("kind") != EXPECTED_KIND:
        raise RuntimeError(
            f"Artifact kind mismatch for {content_type}: "
            f"expected {EXPECTED_KIND!r}, got {metadata.get('kind')!r}. "
            "Re-run scripts/train_fpgrowth.py."
        )
    if metadata.get("content_type") != content_type:
        raise RuntimeError(
            f"Artifact content_type mismatch at {base}: "
            f"expected {content_type!r}, got {metadata.get('content_type')!r}."
        )

    raw_rules = json.loads(rules_path.read_text(encoding="utf-8"))
    # rules.json stores keys as strings (JSON requirement); parse to int.
    rules: dict[int, list[int]] = {
        int(k): [int(x) for x in v] for k, v in raw_rules.items()
    }

    _STATE[content_type] = {
        "rules": rules,
        "metadata": metadata,
        "loaded_at": datetime.now(timezone.utc).isoformat(),
    }


def related_items(content_type: str, tmdb_id: int, top_n: int = 10) -> list[int]:
    """Return up to *top_n* related tmdb_ids for *tmdb_id*, ranked by lift.

    Empty list when *tmdb_id* doesn't appear as an antecedent in any rule
    (cold-start item — was never co-watched with anything above the support
    / confidence thresholds at train time).

    Raises RecommenderNotTrained if artifacts haven't been built for this
    content_type yet.
    """
    _validate_content_type(content_type)
    if content_type not in _STATE:
        _load(content_type)

    rules = _STATE[content_type]["rules"]
    consequents = rules.get(int(tmdb_id), [])
    return consequents[:top_n]


def reload(content_type: str | None = None) -> None:
    """Drop cached state so the next call re-reads from disk."""
    if content_type is None:
        _STATE.clear()
        return
    _validate_content_type(content_type)
    _STATE.pop(content_type, None)


def loaded_state() -> dict[str, dict]:
    """Diagnostic: which content types are loaded, and their metadata. No load."""
    return {
        ct: {"metadata": s["metadata"], "loaded_at": s["loaded_at"]}
        for ct, s in _STATE.items()
    }
