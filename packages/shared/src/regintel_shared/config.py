from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["local", "staging", "production"] = "local"
    log_level: str = "INFO"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    # Where the Streamlit UI reaches the API — same box today (localhost), but a
    # distinct setting so hosting the two on different domains is a config change,
    # not a code change.
    ui_api_base_url: str = "http://localhost:8000"

    postgres_dsn: str = "postgresql+psycopg://regintel:regintel@localhost:5432/regintel"

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "regintel_chunks"
    # Local fastembed model — no API key, zero cost, so cloning this repo needs no
    # embedding provider signup. 384 dims is bge-small's native output size.
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimensions: int = 384

    # Groq serves open-weight Llama models via a fast, free-tier API — chosen
    # specifically so this app can be shared without any paid API key. The `groq`
    # SDK already points at Groq's endpoint by default, no base_url needed. Confirm
    # current model availability at console.groq.com; Groq's hosted lineup changes.
    groq_api_key: str | None = None
    llm_model: str = "llama-3.3-70b-versatile"

    # HS256 wants >=32 bytes (RFC 7518 §3.2) — this default is long enough to avoid
    # PyJWT's InsecureKeyLengthWarning even as a placeholder; still MUST be replaced
    # for anything beyond local dev (see .env.example: `openssl rand -hex 32`).
    jwt_secret: str = "change-me-in-production-this-default-is-not-a-real-secret"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
