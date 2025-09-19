from fastapi import APIRouter
from app.routes.user import router as user_router
from app.routes.folder import router as folder_router
from .auth import router as auth_router
from app.routes.tag import router as tag_router
from app.routes.note import router as note_router
from app.routes.issue import router as issue_router
from app.routes.revision import router as revision_router
from app.routes.grammar import router as grammar_router
from app.routes.render import router as render_router
from app.routes.summarize import router as summarize_router

api = APIRouter()
api.include_router(auth_router)
api.include_router(user_router)
api.include_router(folder_router)
api.include_router(tag_router)
api.include_router(note_router)
api.include_router(issue_router)
api.include_router(revision_router)
api.include_router(grammar_router)
api.include_router(render_router)
api.include_router(summarize_router)
