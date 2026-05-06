from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import jwt
import redis
from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import Genre, User, WatchlistItem
from .schemas import AuthResponse, LoginRequest, RegisterRequest, ThemeUpdateRequest, WatchlistAddRequest, WatchlistUpdateRequest


settings = get_settings()
app = FastAPI(title="VozFlix FastAPI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    app.state.http_client = httpx.Client(timeout=20.0)
    app.state.redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)


@app.on_event("shutdown")
def shutdown_event() -> None:
    client: httpx.Client | None = getattr(app.state, "http_client", None)
    if client is not None:
        client.close()

    redis_client: redis.Redis | None = getattr(app.state, "redis", None)
    if redis_client is not None:
        redis_client.close()


def legacy_password_hash(password: str) -> str:
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest).decode("utf-8")


def create_jwt(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "userId": user.user_id,
        "username": user.username,
        "role": user.role,
        "sub": user.username,
        "iat": now,
        "exp": now + timedelta(milliseconds=settings.jwt_expiration),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_jwt(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def get_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def get_current_user_id(authorization: str | None = Header(default=None)) -> int | None:
    token = get_bearer_token(authorization)
    if not token:
        return None
    claims = decode_jwt(token)
    user_id = claims.get("userId")
    return int(user_id) if user_id is not None else None


def redis_client() -> redis.Redis | None:
    return getattr(app.state, "redis", None)


def http_client() -> httpx.Client:
    client = getattr(app.state, "http_client", None)
    if client is None:
        raise HTTPException(status_code=500, detail="HTTP client unavailable")
    return client


def tmdb_request(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    if not settings.tmdb_api_key:
        raise HTTPException(status_code=500, detail="TMDB API key is not configured")

    query_params = dict(settings.tmdb_auth_params)
    if params:
        query_params.update({key: value for key, value in params.items() if value is not None})

    response = http_client().get(f"{settings.tmdb_base_url}{path}", params=query_params)
    response.raise_for_status()
    return response.json()


def redis_get_json(key: str) -> Any | None:
    client = redis_client()
    if client is None:
        return None
    raw_value = client.get(key)
    if raw_value is None:
        return None
    return json.loads(raw_value)


def redis_set_json(key: str, value: Any, ttl: int) -> None:
    client = redis_client()
    if client is None:
        return
    client.setex(key, ttl, json.dumps(value, ensure_ascii=False))


def normalize_genres_payload(genres: list[Genre]) -> dict[str, Any]:
    return {"genres": [{"id": genre.genre_id, "name": genre.name} for genre in genres]}


def upsert_genres(session: Session, genres: list[dict[str, Any]]) -> None:
    for genre in genres:
        genre_id = genre.get("id")
        name = genre.get("name")
        if genre_id is None or not name:
            continue

        existing = session.get(Genre, int(genre_id))
        if existing is None:
            session.add(Genre(genre_id=int(genre_id), name=str(name)))
        else:
            existing.name = str(name)


def watchlist_item_to_dict(item: WatchlistItem) -> dict[str, Any]:
    return {
        "watchlistId": item.watchlist_id,
        "userId": item.user_id,
        "contentType": item.content_type,
        "tmdbId": item.tmdb_id,
        "status": item.status,
        "progressSeconds": item.progress_seconds,
        "currentEpisode": item.current_episode,
        "currentSeason": item.current_season,
        "rating": float(item.rating) if item.rating is not None else None,
        "review": item.review,
        "isBookmarked": item.is_bookmarked,
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/register", response_model=AuthResponse)
def register_user(request: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    if db.scalar(select(User).where(User.email == request.email)) is not None:
        raise HTTPException(status_code=400, detail="Email already exists")
    if db.scalar(select(User).where(User.username == request.username)) is not None:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(
        username=request.username,
        email=request.email,
        password_hash=legacy_password_hash(request.password),
        role="user",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_jwt(user)
    return AuthResponse(
        userId=user.user_id,
        username=user.username,
        email=user.email,
        role=user.role,
        token=token,
    )


@app.post("/api/auth/login", response_model=AuthResponse)
def login_user(request: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.scalar(select(User).where(User.email == request.email))
    if user is None or legacy_password_hash(request.password) != user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    token = create_jwt(user)
    return AuthResponse(
        userId=user.user_id,
        username=user.username,
        email=user.email,
        role=user.role,
        token=token,
    )


@app.get("/api/session/theme")
def get_theme(user_id: int | None = Depends(get_current_user_id)) -> dict[str, str]:
    if user_id is None:
        return {"theme": "light"}

    theme = redis_get_json(f"session:theme:{user_id}")
    return {"theme": theme if theme in {"light", "dark"} else "light"}


@app.put("/api/session/theme")
def set_theme(payload: ThemeUpdateRequest, user_id: int | None = Depends(get_current_user_id)) -> dict[str, str]:
    target_user_id = payload.userId or user_id
    if target_user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    redis_set_json(f"session:theme:{target_user_id}", payload.theme, settings.session_ttl)
    return {"theme": payload.theme}


@app.get("/api/movies/popular")
def get_popular_movies(page: int = 1) -> dict[str, Any]:
    return tmdb_request("/movie/popular", {"page": page})


@app.get("/api/movies/top-rated")
def get_top_rated_movies(page: int = 1) -> dict[str, Any]:
    return tmdb_request("/movie/top_rated", {"page": page})


@app.get("/api/movies/now-playing")
def get_now_playing_movies(page: int = 1) -> dict[str, Any]:
    return tmdb_request("/movie/now_playing", {"page": page})


@app.get("/api/movies/search")
def search_movies(query: str, page: int = 1) -> dict[str, Any]:
    return tmdb_request("/search/movie", {"query": query, "page": page})


@app.get("/api/movies/discover")
def discover_movies(
    page: int = 1,
    sort_by: str | None = Query(default=None, alias="sort_by"),
    with_genres: str | None = Query(default=None, alias="with_genres"),
    primary_release_year: int | None = Query(default=None, alias="primary_release_year"),
) -> dict[str, Any]:
    return tmdb_request(
        "/discover/movie",
        {
            "page": page,
            "sort_by": sort_by,
            "with_genres": with_genres,
            "primary_release_year": primary_release_year,
        },
    )


@app.post("/api/movies/sync/genres")
def sync_movie_genres(db: Session = Depends(get_db)) -> dict[str, str]:
    response = tmdb_request("/genre/movie/list")
    upsert_genres(db, response.get("genres", []))
    db.commit()
    return {"message": "Genres synced successfully"}


@app.post("/api/movies/sync/all")
def sync_all_movies() -> dict[str, str]:
    tmdb_request("/genre/movie/list")
    tmdb_request("/movie/popular")
    tmdb_request("/movie/top_rated")
    tmdb_request("/movie/now_playing")
    return {"message": "Full sync completed successfully"}


@app.get("/api/movies/genres")
def get_movie_genres(db: Session = Depends(get_db)) -> dict[str, Any]:
    genres = list(db.scalars(select(Genre).order_by(Genre.name)).all())
    if genres:
        return normalize_genres_payload(genres)
    return tmdb_request("/genre/movie/list")


@app.get("/api/movies/cached")
def get_cached_movies(limit: int = 20, offset: int = 0) -> dict[str, Any]:
    return {"results": [], "total": 0, "limit": limit, "offset": offset}


@app.get("/api/movies/{movie_id}")
def get_movie_details(movie_id: int) -> dict[str, Any]:
    return tmdb_request(f"/movie/{movie_id}")


@app.get("/api/movies/{movie_id}/credits")
def get_movie_credits(movie_id: int) -> dict[str, Any]:
    return tmdb_request(f"/movie/{movie_id}/credits")


@app.get("/api/movies/{movie_id}/images")
def get_movie_images(movie_id: int) -> dict[str, Any]:
    return tmdb_request(f"/movie/{movie_id}/images")


@app.get("/api/series/popular")
def get_popular_series(page: int = 1) -> dict[str, Any]:
    return tmdb_request("/tv/popular", {"page": page})


@app.get("/api/series/top-rated")
def get_top_rated_series(page: int = 1) -> dict[str, Any]:
    return tmdb_request("/tv/top_rated", {"page": page})


@app.get("/api/series/search")
def search_series(query: str, page: int = 1) -> dict[str, Any]:
    return tmdb_request("/search/tv", {"query": query, "page": page})


@app.get("/api/series/discover")
def discover_series(
    page: int = 1,
    sort_by: str | None = Query(default=None, alias="sort_by"),
    with_genres: str | None = Query(default=None, alias="with_genres"),
) -> dict[str, Any]:
    return tmdb_request(
        "/discover/tv",
        {
            "page": page,
            "sort_by": sort_by,
            "with_genres": with_genres,
        },
    )


@app.post("/api/series/sync/genres")
def sync_series_genres(db: Session = Depends(get_db)) -> dict[str, str]:
    response = tmdb_request("/genre/tv/list")
    upsert_genres(db, response.get("genres", []))
    db.commit()
    return {"message": "Genres synced successfully"}


@app.post("/api/series/sync/all")
def sync_all_series() -> dict[str, str]:
    tmdb_request("/genre/tv/list")
    tmdb_request("/tv/popular")
    tmdb_request("/tv/top_rated")
    return {"message": "Full TV sync completed successfully"}


@app.get("/api/series/genres")
def get_series_genres(db: Session = Depends(get_db)) -> dict[str, Any]:
    genres = list(db.scalars(select(Genre).order_by(Genre.name)).all())
    if genres:
        return normalize_genres_payload(genres)
    return tmdb_request("/genre/tv/list")


@app.get("/api/series/cached")
def get_cached_series(limit: int = 20, offset: int = 0) -> dict[str, Any]:
    return {"results": [], "total": 0, "limit": limit, "offset": offset}


@app.get("/api/series/{tv_id}")
def get_series_details(tv_id: int) -> dict[str, Any]:
    return tmdb_request(f"/tv/{tv_id}")


@app.get("/api/series/{tv_id}/season/{season_number}")
def get_series_season(tv_id: int, season_number: int) -> dict[str, Any]:
    return tmdb_request(f"/tv/{tv_id}/season/{season_number}")


@app.get("/api/series/{tv_id}/credits")
def get_series_credits(tv_id: int) -> dict[str, Any]:
    return tmdb_request(f"/tv/{tv_id}/credits")


def cached_search(endpoint: str, query: str, page: int) -> dict[str, Any]:
    cache_key = f"search:{endpoint}:{query.lower().strip()}:{page}"
    cached = redis_get_json(cache_key)
    if cached is not None:
        return cached

    response = tmdb_request(endpoint, {"query": query, "page": page})
    redis_set_json(cache_key, response, settings.search_cache_ttl)
    return response


@app.get("/api/search")
def search_all(query: str, page: int = 1) -> dict[str, Any]:
    return cached_search("/search/multi", query, page)


@app.get("/api/search/movies")
def search_movies_cached(query: str, page: int = 1) -> dict[str, Any]:
    return cached_search("/search/movie", query, page)


@app.get("/api/search/series")
def search_series_cached(query: str, page: int = 1) -> dict[str, Any]:
    return cached_search("/search/tv", query, page)


@app.post("/api/watchlist/add")
def add_watchlist_item(payload: WatchlistAddRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    existing = db.scalar(
        select(WatchlistItem).where(
            WatchlistItem.user_id == payload.userId,
            WatchlistItem.tmdb_id == payload.tmdbId,
            WatchlistItem.content_type == payload.contentType,
        )
    )

    action = "added"
    if existing is not None:
        db.delete(existing)
        db.commit()
        action = "removed"

    item = WatchlistItem(
        user_id=payload.userId,
        content_type=payload.contentType,
        tmdb_id=payload.tmdbId,
        status=payload.status,
        progress_seconds=0,
        current_episode=1,
        current_season=1,
        is_bookmarked=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return {"success": True, "action": action, "item": watchlist_item_to_dict(item)}


@app.post("/api/watchlist/update")
def update_watchlist_item(payload: WatchlistUpdateRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    item = db.get(WatchlistItem, payload.watchlistId)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    if payload.status is not None:
        item.status = payload.status
    if payload.progressSeconds is not None:
        item.progress_seconds = payload.progressSeconds

    db.commit()
    db.refresh(item)
    return {"success": True, "item": watchlist_item_to_dict(item)}


@app.get("/api/watchlist/{user_id}")
def get_watchlist(user_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    items = list(db.scalars(select(WatchlistItem).where(WatchlistItem.user_id == user_id)).all())
    mapped = [watchlist_item_to_dict(item) for item in items]
    return {"items": mapped, "total": len(mapped)}


@app.get("/api/watchlist/{user_id}/{status}")
def get_watchlist_by_status(user_id: int, status: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    items = list(
        db.scalars(
            select(WatchlistItem).where(
                WatchlistItem.user_id == user_id,
                WatchlistItem.status == status,
            )
        ).all()
    )
    mapped = [watchlist_item_to_dict(item) for item in items]
    return {"items": mapped, "total": len(mapped)}


@app.delete("/api/watchlist/{watchlist_id}")
def delete_watchlist_item(watchlist_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    item = db.get(WatchlistItem, watchlist_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(item)
    db.commit()
    return {"success": True}