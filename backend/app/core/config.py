"""Application configuration loaded from environment variables."""

import json
from functools import lru_cache
from typing import Annotated

from pydantic import BeforeValidator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _parse_list(value):
    if isinstance(value, str):
        if value.strip().startswith("["):
            value = json.loads(value)
        else:
            value = [item.strip() for item in value.split(",") if item.strip()]
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Newsroom Backend"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://localhost:5432/ai_newsroom"
    cors_origins: Annotated[list[str], NoDecode, BeforeValidator(_parse_list)] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    llm_provider: str = "ollama"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_timeout_seconds: float = 60.0


@lru_cache
def get_settings() -> Settings:
    return Settings()