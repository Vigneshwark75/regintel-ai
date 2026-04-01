from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["local", "staging", "production"] = "local"
    log_level: str = "INFO"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    postgres_dsn: str = "postgresql+psycopg://regintel:regintel@localhost:5432/regintel"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "regintel_chunks"

    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    llm_provider: Literal["anthropic", "openai"] = "anthropic"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
