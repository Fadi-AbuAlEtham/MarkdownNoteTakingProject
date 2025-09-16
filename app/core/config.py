from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pydantic import AliasChoices


class Settings(BaseSettings):
    APP_NAME: str = "Note Markdown API"
    DATABASE_URL: str = Field(..., description="Async DB URL")
    DATABASE_URL_SYNC: str = Field(..., description="Sync DB URL")
    DB_ECHO: bool = Field(False, description="SQL echo (true/false)")

    REDIS_HOST: str = Field(..., description="Redis host")
    REDIS_PORT: int = Field(6379)
    REDIS_DB: int = Field(0)
    CACHE_TTL: int = Field(90)

    SECRET_KEY: SecretStr = Field(..., description="JWT secret")
    ALGORITHM: str = Field("HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class GrammarSettings(BaseSettings):
    BASE_URL: str = Field("https://api.languagetool.org")
    API_KEY: Optional[str] = None
    AUTH_HEADER: Optional[str] = None
    LEVEL: str = "default"

    model_config = SettingsConfigDict(env_prefix="LT_", env_file=".env", extra="ignore")


class SummarizeSettings(BaseSettings):
    GEMINI_API_KEY: str = Field(
        default="", validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY")
    )
    GEMINI_MODEL: str = "gemini-1.5-flash"
    MAX_CHARS_PER_CALL: int = 12000
    LANGUAGE: str = "en"

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", case_sensitive=False
    )