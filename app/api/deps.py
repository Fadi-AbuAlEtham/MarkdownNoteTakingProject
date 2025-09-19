import os
from typing import Annotated

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.core.db import get_db
from app.models import user as models
from app.repositories.tag import TagRepository
from app.repositories.user import UserRepository
from app.services.tag import TagService
from app.services.user import UserService

security = HTTPBearer(auto_error=False)
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

unauth_exc = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
)


def get_user_repo(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_user_service(repo: UserRepository = Depends(get_user_repo)) -> UserService:
    return UserService(repo)


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


def get_tag_service(
    repo: TagRepository = Depends(get_tag_repo),
    user_id: int = Depends(get_current_user_id),
) -> TagService:
    return TagService(repo, user_id)
