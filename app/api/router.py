from fastapi import APIRouter
from app.controllers.user_controller import router as user_router
from app.controllers.folder_controller import router as folder_router
from .auth import router as auth_router
from app.controllers.tag_controller import router as tag_router

api = APIRouter()
api.include_router(auth_router)
api.include_router(user_router)
api.include_router(folder_router)
api.include_router(tag_router)
