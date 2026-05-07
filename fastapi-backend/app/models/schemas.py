"""
Pydantic models that mirror the existing TypeScript interfaces in database/src/types.ts
and the Mongoose model documents.

All response models map MongoDB _id → id (string) for frontend compatibility.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ─── Embedded sub-documents ───────────────────────────────────────────────

class GenreOut(BaseModel):
    genre_id: int
    name: str


class CastOut(BaseModel):
    person_id: int
    name: str
    profile_path: Optional[str] = None
    character_name: str = ""
    cast_order: int = 0


class CrewOut(BaseModel):
    person_id: int
    name: str
    profile_path: Optional[str] = None
    job: str = ""


class EpisodeOut(BaseModel):
    episode_number: int
    name: str = ""
    overview: str = ""
    still_path: Optional[str] = None
    air_date: Optional[str] = None
    runtime: Optional[int] = None
    vote_average: float = 0
    vote_count: int = 0
    season_number: int


class SeasonOut(BaseModel):
    season_number: int
    name: str = ""
    overview: str = ""
    poster_path: Optional[str] = None
    air_date: Optional[str] = None
    episode_count: int = 0
    episodes: List[EpisodeOut] = []


# ─── Movie ────────────────────────────────────────────────────────────────

class MovieOut(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    tmdb_id: int
    title: str
    original_title: Optional[str] = None
    tagline: Optional[str] = None
    overview: str = ""
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    release_date: Optional[str] = None
    original_language: Optional[str] = None
    popularity: float = 0
    vote_average: float = 0
    vote_count: int = 0
    adult: bool = False
    video: bool = False
    runtime: Optional[int] = None
    budget: int = 0
    revenue: int = 0
    status: Optional[str] = None
    imdb_id: Optional[str] = None
    homepage: Optional[str] = None
    genres: List[GenreOut] = []
    cast: List[CastOut] = []
    crew: List[CrewOut] = []
    production_countries_json: List[Dict[str, Any]] = []
    spoken_languages_json: List[Dict[str, Any]] = []
    raw_data: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"populate_by_name": True}


# ─── Series ───────────────────────────────────────────────────────────────

class SeriesOut(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    tmdb_id: int
    name: str
    original_name: Optional[str] = None
    tagline: Optional[str] = None
    overview: str = ""
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    first_air_date: Optional[str] = None
    last_air_date: Optional[str] = None
    original_language: Optional[str] = None
    popularity: float = 0
    vote_average: float = 0
    vote_count: int = 0
    adult: bool = False
    episode_run_time: List[int] = []
    type: Optional[str] = None
    status: Optional[str] = None
    imdb_id: Optional[str] = None
    homepage: Optional[str] = None
    number_of_seasons: int = 0
    number_of_episodes: int = 0
    genres: List[GenreOut] = []
    cast: List[CastOut] = []
    crew: List[CrewOut] = []
    seasons: List[SeasonOut] = []
    networks_json: List[Dict[str, Any]] = []
    production_countries_json: List[Dict[str, Any]] = []
    spoken_languages_json: List[Dict[str, Any]] = []
    raw_data: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"populate_by_name": True}


# ─── User ─────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    email: str
    username: str = ""
    avatar_url: Optional[str] = None
    role: str = "user"
    is_active: bool = True
    created_at: Optional[datetime] = None

    model_config = {"populate_by_name": True}


# ─── Auth payloads ────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: UserOut


# ─── Watch History ────────────────────────────────────────────────────────

class WatchHistoryOut(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    content_type: str  # "movie" | "series"
    tmdb_id: int
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    progress_seconds: int = 0
    completed: bool = False
    last_watched_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"populate_by_name": True}


class ProgressUpdateRequest(BaseModel):
    content_type: str
    tmdb_id: int
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    progress_seconds: int = 0
    completed: bool = False


# ─── Watchlist Item ───────────────────────────────────────────────────────

class WatchlistItemOut(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    content_type: str
    tmdb_id: int
    status: str = "plan_to_watch"
    progress_seconds: int = 0
    current_season: Optional[int] = None
    current_episode: Optional[int] = None
    is_bookmarked: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"populate_by_name": True}


class WatchlistAddRequest(BaseModel):
    content_type: str
    tmdb_id: int
    status: str = "plan_to_watch"
    is_bookmarked: bool = True


class WatchlistUpdateRequest(BaseModel):
    status: Optional[str] = None
    progress_seconds: Optional[int] = None
    current_season: Optional[int] = None
    current_episode: Optional[int] = None
    is_bookmarked: Optional[bool] = None


# ─── User Rating ──────────────────────────────────────────────────────────

class UserRatingOut(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    content_type: str
    tmdb_id: int
    rating: float
    review: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"populate_by_name": True}


class RatingCreateRequest(BaseModel):
    content_type: str
    tmdb_id: int
    rating: float
    review: Optional[str] = None


class RatingDeleteRequest(BaseModel):
    content_type: str
    tmdb_id: int


# ─── Profile ──────────────────────────────────────────────────────────────

class ProfileUpdateRequest(BaseModel):
    username: Optional[str] = None
    avatar_url: Optional[str] = None


class ProfileStatsOut(BaseModel):
    watchlist_count: int = 0
    completed_count: int = 0
    watching_count: int = 0
    ratings_count: int = 0
    history_count: int = 0
    average_rating: float = 0


# ─── Comments ─────────────────────────────────────────────────────────────

class CommentOut(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    username: str = ""
    content_type: str  # "movie" | "series"
    tmdb_id: int
    text: str
    created_at: Optional[datetime] = None

    model_config = {"populate_by_name": True}


class CommentCreateRequest(BaseModel):
    content_type: str
    tmdb_id: int
    text: str


# ─── Admin ────────────────────────────────────────────────────────────────

class AdminUserOut(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    email: str
    username: str = ""
    role: str = "user"
    is_active: bool = True
    is_banned: bool = False
    created_at: Optional[datetime] = None

    model_config = {"populate_by_name": True}


class AdminMovieOut(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    tmdb_id: int
    title: str
    poster_path: Optional[str] = None
    is_hidden: bool = False
    vote_average: float = 0

    model_config = {"populate_by_name": True}


class BanUserRequest(BaseModel):
    is_banned: bool


class HideMovieRequest(BaseModel):
    is_hidden: bool


class HideGenreRequest(BaseModel):
    is_hidden: bool
