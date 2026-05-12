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
