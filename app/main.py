from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.db import engine
from app.core.db import Base
from app.api.router import api


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(api)
