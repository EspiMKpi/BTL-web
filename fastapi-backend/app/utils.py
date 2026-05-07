"""Shared utilities used across services and routers."""

from datetime import datetime
from typing import Any

from bson import ObjectId


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
