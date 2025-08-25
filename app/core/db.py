from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

Base = declarative_base()

def get_async_engine(database_url: str, echo: bool = True):
    return create_async_engine(database_url, echo=echo, future=True)

def get_async_session_factory(engine):
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
