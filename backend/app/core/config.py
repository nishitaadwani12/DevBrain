"""Application settings loaded from environment / .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Google Gemini
    gemini_api_key: str = ""
    embedding_model: str = "gemini-embedding-001"
    chat_model: str = "gemini-3.6-flash"
    # Lighter/faster model with higher free-tier limits for the multi-call agent loop.
    agent_model: str = "gemini-flash-lite-latest"
    embedding_dim: int = 768  # request 768-dim output to match the pgvector column

    # Supabase / Postgres
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_anon_key: str = ""
    supabase_jwt_secret: str = ""  # HS256 secret used to verify auth tokens
    database_url: str = ""

    # Auth — when true, endpoints require a valid Supabase JWT. Disable only for
    # local single-user development.
    auth_enabled: bool = True
    dev_user_id: str = "00000000-0000-0000-0000-000000000000"

    # App
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
