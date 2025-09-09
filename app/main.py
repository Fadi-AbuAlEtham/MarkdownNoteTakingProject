# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from app.core.db import engine
from app.api.router import api


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup: optional connectivity check ---
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    yield
    # --- shutdown: close pools ---
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
app.include_router(api)
