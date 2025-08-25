from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Tasks API"
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:root1234@localhost:5432/markdown_notes"
    )
    DATABASE_URL_SYNC: str = Field(
        default="postgresql+psycopg2://postgres:root1234@localhost:5432/markdown_notes"
    )
    # AMQP_URL: str = "amqp://guest:guest@rabbitmq/"
    # AMQP_EXCHANGE: str = "tasks"
    # AMQP_EVENT_QUEUE: str = "tasks.events"
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    CACHE_TTL: int = 90

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
