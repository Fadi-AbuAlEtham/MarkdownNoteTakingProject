from fastapi import APIRouter
from app.controllers.user_controller import router as user_router

api = APIRouter()
api.include_router(user_router)
