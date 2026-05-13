"""
VozFlix FastAPI backend — replaces the Express/TypeScript server.
Run with: uvicorn app.main:app --reload --port 8000
"""

import json
from contextlib import asynccontextmanager
from datetime import datetime

from bson import ObjectId
from fastapi import FastAPI, Request
from fastapi.encoders import ENCODERS_BY_TYPE
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings
from app.database import close_mongo_connection, connect_to_mongo
from app.routers import admin, auth, comments, content, history, profile, ratings, watchlist

# Teach FastAPI's jsonable_encoder how to serialize MongoDB ObjectId.
# This is the actual fix for the "ObjectId is not iterable" / "vars() argument
# must have __dict__" crashes — it runs BEFORE any Response.render() and
# applies globally to every route that returns raw dicts from MongoDB.
ENCODERS_BY_TYPE[ObjectId] = str


class _MongoEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class MongoJSONResponse(JSONResponse):
    """Defence in depth: even if a raw ObjectId/datetime slips past
    jsonable_encoder (e.g., a route returns a Response directly), this
    ensures the final JSON serialization step still succeeds."""
    def render(self, content) -> bytes:
        return json.dumps(content, cls=_MongoEncoder, ensure_ascii=False).encode("utf-8")


# Global rate limiter (in-memory, per-worker)
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()


app = FastAPI(
    title="VozFlix API",
    version="1.0.0",
    lifespan=lifespan,
    default_response_class=MongoJSONResponse,
)

# Rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — same origins as the Express cors() middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers
app.include_router(auth.router)
app.include_router(content.router)
app.include_router(watchlist.router)
app.include_router(history.router)
app.include_router(ratings.router)
app.include_router(profile.router)
app.include_router(comments.router)
app.include_router(admin.router)


@app.get("/api/test")
async def health_check():
    return {"status": "ok"}
