from __future__ import annotations

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="dev", alias="APP_ENV")
    app_name: str = Field(default="Gospel Resonance", alias="APP_NAME")
    admin_token: str = Field(default="change_me", alias="ADMIN_TOKEN")
    api_v1_prefix: str = "/api/v1"

    database_url: str = Field(
        default="postgresql+asyncpg://gospel:gospel@db:5432/gospel_resonance",
        alias="DATABASE_URL",
    )

    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL")
    openrouter_site_url: Optional[str] = Field(default=None, alias="OPENROUTER_SITE_URL")
    openrouter_app_title: Optional[str] = Field(default=None, alias="OPENROUTER_APP_TITLE")
    openrouter_chat_model: str = Field(default="x-ai/grok-4.1-fast", alias="OPENROUTER_CHAT_MODEL")
    openrouter_embed_model: str = Field(default="openai/text-embedding-3-large", alias="OPENROUTER_EMBED_MODEL")
    openrouter_embed_dimensions: int = Field(default=1536, alias="OPENROUTER_EMBED_DIMENSIONS")

    embedding_version: str = Field(default="v1", alias="EMBEDDING_VERSION")
    prompt_version: str = Field(default="v1", alias="PROMPT_VERSION")

    ask_max_input_chars: int = Field(default=4000, alias="ASK_MAX_INPUT_CHARS")
    ask_canonical_candidates: int = Field(default=12, alias="ASK_CANONICAL_CANDIDATES")
    ask_thomas_candidates: int = Field(default=8, alias="ASK_THOMAS_CANDIDATES")

    daily_timezone_default: str = Field(default="UTC", alias="DAILY_TIMEZONE_DEFAULT")
    digest_time_utc: str = Field(default="06:00", alias="DAILY_GENERATION_TIME_UTC")
    run_daily_on_startup: bool = Field(default=True, alias="RUN_DAILY_ON_STARTUP")
    ensure_daily_on_api_startup: bool = Field(default=True, alias="ENSURE_DAILY_ON_API_STARTUP")

    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")


settings = Settings()
