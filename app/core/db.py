import os

from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

Base = declarative_base()
import app.models.user  # noqa: F401
import app.models.note_tag  # noqa: F401
import app.models.folder  # noqa: F401
import app.models.note  # noqa: F401
import app.models.revision  # noqa: F401
import app.models.issue  # noqa: F401
import app.models.grammar  # noqa: F401

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_async_engine(DATABASE_URL, echo=True, future=True, pool_pre_ping=True)


def get_async_engine(database_url: str, echo: bool = True):
    return create_async_engine(database_url, echo=echo, future=True)


def get_async_session_factory(engine):
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


SessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db():
    async with SessionLocal() as session:
        yield session
