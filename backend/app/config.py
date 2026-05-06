from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    server_port: int = Field(default=8080, validation_alias=AliasChoices("SERVER_PORT"))

    db_host: str = Field(default="localhost", validation_alias=AliasChoices("DB_HOST"))
    db_port: int = Field(default=3306, validation_alias=AliasChoices("DB_PORT"))
    db_name: str = Field(default="movie_db", validation_alias=AliasChoices("DB_NAME"))
    db_user: str = Field(default="root", validation_alias=AliasChoices("DB_USER"))
    db_password: str = Field(default="root", validation_alias=AliasChoices("DB_PASSWORD"))

    redis_host: str = Field(
        default="localhost",
        validation_alias=AliasChoices("SPRING_DATA_REDIS_HOST", "REDIS_HOST"),
    )
    redis_port: int = Field(
        default=6379,
        validation_alias=AliasChoices("SPRING_DATA_REDIS_PORT", "REDIS_PORT"),
    )

    tmdb_api_key: str = Field(default="", validation_alias=AliasChoices("TMDB_API_KEY"))
    tmdb_base_url: str = Field(
        default="https://api.themoviedb.org/3",
        validation_alias=AliasChoices("TMDB_BASE_URL"),
    )
    tmdb_image_base_url: str = Field(
        default="https://image.tmdb.org/t/p",
        validation_alias=AliasChoices("TMDB_IMAGE_BASE_URL"),
    )

    jwt_secret: str = Field(
        default="VozFlixSecretKey2024ThatIsLongEnoughForHS256Algorithm",
        validation_alias=AliasChoices("JWT_SECRET"),
    )
    jwt_expiration: int = Field(default=86400000, validation_alias=AliasChoices("JWT_EXPIRATION"))

    search_cache_ttl: int = Field(default=3600, validation_alias=AliasChoices("SEARCH_CACHE_TTL"))
    session_ttl: int = Field(default=86400, validation_alias=AliasChoices("SESSION_TTL"))

    @property
    def database_url(self) -> str:
        password = quote_plus(self.db_password)
        return f"mysql+pymysql://{self.db_user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    @property
    def tmdb_auth_params(self) -> dict[str, str]:
        return {"api_key": self.tmdb_api_key, "language": "en-US"}


@lru_cache
def get_settings() -> Settings:
    return Settings()