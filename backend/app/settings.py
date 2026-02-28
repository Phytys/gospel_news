from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_env: str = Field(default="dev", alias="APP_ENV")
    app_base_url: str = Field(default="http://localhost:8000", alias="APP_BASE_URL")
    admin_token: str = Field(default="change_me", alias="ADMIN_TOKEN")

    # DB
    database_url: str = Field(
        default="postgresql+asyncpg://gospellens:gospellens@db:5432/gospellens",
        alias="DATABASE_URL",
    )

    # OpenRouter
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL")
    openrouter_site_url: Optional[str] = Field(default=None, alias="OPENROUTER_SITE_URL")
    openrouter_app_title: Optional[str] = Field(default=None, alias="OPENROUTER_APP_TITLE")

    openrouter_chat_model: str = Field(default="x-ai/grok-4.1-fast", alias="OPENROUTER_CHAT_MODEL")
    openrouter_embed_model: str = Field(default="openai/text-embedding-3-large", alias="OPENROUTER_EMBED_MODEL")
    openrouter_embed_dimensions: int = Field(default=1536, alias="OPENROUTER_EMBED_DIMENSIONS")

    # Digest schedule
    digest_time_sgt: str = Field(default="06:30", alias="DIGEST_TIME_SGT")
    stories_per_day: int = Field(default=3, alias="STORIES_PER_DAY")
    run_digest_on_startup: bool = Field(default=False, alias="RUN_DIGEST_ON_STARTUP")

    # RSS sources
    rss_sources_file: str = Field(default="/app/config/rss_sources.json", alias="RSS_SOURCES_FILE")

    # Retrieval
    canonical_top_k: int = Field(default=20, alias="CANONICAL_TOP_K")
    thomas_top_k: int = Field(default=10, alias="THOMAS_TOP_K")


settings = Settings()
