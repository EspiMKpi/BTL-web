from typing import Literal

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=255)


class AuthResponse(BaseModel):
    userId: int
    username: str
    email: str
    role: str
    token: str


class ThemeUpdateRequest(BaseModel):
    theme: Literal["light", "dark"]
    userId: int | None = None


class WatchlistAddRequest(BaseModel):
    userId: int
    tmdbId: int
    contentType: Literal["movie", "series"] = "movie"
    status: Literal["continue", "wishlist", "completed", "favorites"] = "wishlist"


class WatchlistUpdateRequest(BaseModel):
    watchlistId: int
    status: Literal["continue", "wishlist", "completed", "favorites"] | None = None
    progressSeconds: int | None = None