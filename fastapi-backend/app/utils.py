"""Shared utilities used across services and routers."""

import re
from datetime import datetime
from typing import Any

from bson import ObjectId


# Characters that have special meaning in MongoDB regex queries
_MONGO_REGEX_SPECIAL = re.compile(r'[.*+?^${}()|\\[\]]')


def sanitize(value: Any) -> Any:
    """Recursively convert ObjectId and datetime to JSON-serializable types."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    return value


def escape_mongo_regex(value: str) -> str:
    """Escape special regex characters for safe use in MongoDB $regex queries."""
    return _MONGO_REGEX_SPECIAL.sub(r'\\\g<0>', value)


# ─── Document-type detection helpers ──────────────────────────────────
# Used by movieService, seriesService, libraryService, and content router
# to reject documents that ended up in the wrong MongoDB collection.

def is_movie_doc(doc: dict) -> bool:
    """Return True if *doc* (from the movies collection) is actually a movie."""
    if doc.get("seasons") or doc.get("number_of_seasons"):
        return False
    if doc.get("first_air_date") and not doc.get("release_date"):
        return False
    return True


def is_series_doc(doc: dict) -> bool:
    """Return True if *doc* (from the series collection) is actually a TV series."""
    if doc.get("title") and not doc.get("name"):
        return False
    if doc.get("release_date") and not doc.get("first_air_date"):
        return False
    return True
