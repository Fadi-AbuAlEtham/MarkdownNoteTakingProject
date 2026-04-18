import os
from typing import Annotated

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.core.db import get_db
from app.models import user as models
from app.repositories.folder import FolderRepository
from app.repositories.grammar import GrammarRepository
from app.repositories.issue import IssueRepository
from app.repositories.note import NoteRepository
from app.repositories.revision import RevisionRepository
from app.repositories.tag import TagRepository
from app.repositories.user import UserRepository
from app.services.auth import AuthService
from app.services.folder import FolderService
from app.services.grammar import GrammarService
from app.services.issue import IssueService
from app.services.note import NoteService
from app.services.render import RenderService
from app.services.revision import RevisionService
from app.services.summarize import SummarizeService
from app.services.tag import TagService
from app.services.user import UserService
from app.services.grammar_provider import GrammarProvider
from app.services.providers.languagetool import LanguageToolProvider
from app.services.providers.gemini_summarizer import GeminiSummarizer
from app.services.summarize_provider import SummarizeProvider
from app.core.config import GrammarSettings

security = HTTPBearer(auto_error=False)
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
_grammar_settings = GrammarSettings()
_grammar_provider = LanguageToolProvider(
    base_url=_grammar_settings.BASE_URL,
    api_key=_grammar_settings.API_KEY,
    auth_header=_grammar_settings.AUTH_HEADER,
    level=_grammar_settings.LEVEL,
)
_summarize_provider: SummarizeProvider = GeminiSummarizer()

unauth_exc = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
)


def get_user_repo(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_user_service(repo: UserRepository = Depends(get_user_repo)) -> UserService:
    return UserService(repo)


def get_auth_service(repo: UserRepository = Depends(get_user_repo)) -> AuthService:
    return AuthService(repo)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    user_repo: UserRepository = Depends(get_user_repo),
) -> models.User:
    """
    Extract Bearer token, decode JWT, fetch the active user.
    Raises 401 on any problem (missing token, bad token, user not found).
    """
    if credentials is None or not credentials.credentials:
        raise unauth_exc

    if not SECRET_KEY:
        raise HTTPException(status_code=500, detail="Server auth misconfigured")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        user_id = int(sub)
    except (JWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


async def get_current_user_id(
    user: Annotated[models.User, Depends(get_current_user)],
) -> int:
    return user.id


async def allow_self_or_admin(
    target_user_id: int,
    user: Annotated[models.User, Depends(get_current_user)],
) -> None:
    """
    Dependency to guard routes that allow either the resource owner (self)
    or an admin to proceed. Raises 403 otherwise.
    """
    is_admin = (
        bool(getattr(user, "is_admin", False)) or getattr(user, "role", None) == "admin"
    )
    if user.id != target_user_id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def get_tag_repo(db: AsyncSession = Depends(get_db)) -> TagRepository:
    return TagRepository(db)


def get_folder_repo(db: AsyncSession = Depends(get_db)) -> FolderRepository:
    return FolderRepository(db)


def get_revision_repo(db: AsyncSession = Depends(get_db)) -> RevisionRepository:
    return RevisionRepository(db)


def get_note_repo(db: AsyncSession = Depends(get_db)) -> NoteRepository:
    return NoteRepository(db)


def get_issue_repo(db: AsyncSession = Depends(get_db)) -> IssueRepository:
    return IssueRepository(db)


def get_grammar_repo(db: AsyncSession = Depends(get_db)) -> GrammarRepository:
    return GrammarRepository(db)


def get_grammar_provider() -> GrammarProvider:
    return _grammar_provider


def get_summarize_provider() -> SummarizeProvider:
    return _summarize_provider


def get_revision_service(
    repo: RevisionRepository = Depends(get_revision_repo),
    note_repo: NoteRepository = Depends(get_note_repo),
    tag_repo: TagRepository = Depends(get_tag_repo),
    user_id: int = Depends(get_current_user_id),
) -> RevisionService:
    return RevisionService(repo, note_repo, tag_repo, user_id)


def get_tag_service(
    repo: TagRepository = Depends(get_tag_repo),
    user_id: int = Depends(get_current_user_id),
) -> TagService:
    return TagService(repo, user_id)


def get_folder_service(
    repo: FolderRepository = Depends(get_folder_repo),
    note_repo: NoteRepository = Depends(get_note_repo),
    user_id: int = Depends(get_current_user_id),
) -> FolderService:
    return FolderService(folder_repo=repo, note_repo=note_repo, user_id=user_id)


def get_note_service(
    note_repo: NoteRepository = Depends(get_note_repo),
    tag_repo: TagRepository = Depends(get_tag_repo),
    folder_repo: FolderRepository = Depends(get_folder_repo),
    tag_service: TagService = Depends(get_tag_service),
    revision_repo: RevisionRepository = Depends(get_revision_repo),
    user_id: int = Depends(get_current_user_id),
) -> NoteService:
    return NoteService(
        note_repo=note_repo,
        user_id=user_id,
        tag_repo=tag_repo,
        folder_repo=folder_repo,
        tag_service=tag_service,
        revision_repo=revision_repo,
    )


def get_issue_service(
    repo: IssueRepository = Depends(get_issue_repo),
    note_repo: NoteRepository = Depends(get_note_repo),
    revision_repo: RevisionRepository = Depends(get_revision_repo),
    user_id: int = Depends(get_current_user_id),
) -> IssueService:
    return IssueService(repo, note_repo, revision_repo, user_id)


def get_render_service(
    repo: RevisionRepository = Depends(get_revision_repo),
    user_id: int = Depends(get_current_user_id),
) -> RenderService:
    return RenderService(repo, user_id)


def get_grammar_service(
    revision_repo: RevisionRepository = Depends(get_revision_repo),
    note_repo: NoteRepository = Depends(get_note_repo),
    grammar_repo: GrammarRepository = Depends(get_grammar_repo),
    provider: GrammarProvider = Depends(get_grammar_provider),
    user_id: int = Depends(get_current_user_id),
) -> GrammarService:
    return GrammarService(
        revision_repo=revision_repo,
        note_repo=note_repo,
        grammar_repo=grammar_repo,
        provider=provider,
        user_id=user_id,
    )


def get_summarize_service(
    note_repo: NoteRepository = Depends(get_note_repo),
    folder_repo: FolderRepository = Depends(get_folder_repo),
    provider: SummarizeProvider = Depends(get_summarize_provider),
    user_id: int = Depends(get_current_user_id),
) -> SummarizeService:
    return SummarizeService(
        note_repo=note_repo,
        folder_repo=folder_repo,
        provider=provider,
        user_id=user_id,
    )
