from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Tasks API"
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/markdown_notes"
    # AMQP_URL: str = "amqp://guest:guest@rabbitmq/"
    # AMQP_EXCHANGE: str = "tasks"
    # AMQP_EVENT_QUEUE: str = "tasks.events"
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    CACHE_TTL: int = 90

    class Config:
        env_file = ".env"


settings = Settings()
