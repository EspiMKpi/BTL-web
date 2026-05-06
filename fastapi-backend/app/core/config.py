"""
Application configuration — loaded from .env file.
Mirrors the Node.js process.env.* pattern.
"""

from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    # MongoDB
    MONGODB_URI: str = ""
    DB_NAME: str = "movie_db"

    # TMDB
    TMDB_API_KEY: str = ""

    # JWT — must match the existing Node .env so tokens stay compatible
    JWT_SECRET: str = "vozflix_jwt_secret_change_me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_DAYS: int = 7

    # CORS origins (JSON array string in .env)
    CORS_ORIGINS: str = '["http://localhost:5173","http://localhost:3000"]'

    @property
    def cors_origins_list(self) -> List[str]:
        return json.loads(self.CORS_ORIGINS)

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
