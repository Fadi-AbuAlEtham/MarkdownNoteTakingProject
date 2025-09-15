from typing import Optional

from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Note Markdown API"
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:root1234@localhost:5432/markdown_notes"
    )
    DATABASE_URL_SYNC: str = Field(
        default="postgresql+psycopg2://postgres:root1234@localhost:5432/markdown_notes"
    )
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    CACHE_TTL: int = 90

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


class GrammarSettings(BaseSettings):
    BASE_URL: str = "https://api.languagetool.org"
    API_KEY: Optional[str] = None
    AUTH_HEADER: Optional[str] = None
    LEVEL: str = "default"

    model_config = SettingsConfigDict(
        env_prefix="LT_",
        extra="ignore",
        env_file=".env",
        case_sensitive=False,
    )


class SummarizeSettings(BaseSettings):
    GEMINI_API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    )
    GEMINI_MODEL: str = "gemini-1.5-flash"
    MAX_CHARS_PER_CALL: int = 12000
    LANGUAGE: str = "en"

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", case_sensitive=False
    )


settings = Settings()
