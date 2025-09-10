from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.jwt import decode_access_token
from app.repositories import user_repo
from app.models import user as models

unauth_exc = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
)


def _extract_bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise unauth_exc
    scheme, _, param = authorization.partition(" ")
    if scheme.lower() != "bearer" or not param:
        raise unauth_exc
    return param


async def get_current_user(
    authorization: Annotated[Optional[str], Header(None, alias="Authorization")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> models.User:
    """
    - Reads Authorization header (Bearer token)
    - Decodes JWT and gets user id from `sub`
    - Loads user; rejects soft-deleted or inactive
    """
    token = _extract_bearer_token(authorization)
    try:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        user_id = int(sub)
    except (JWTError, ValueError, TypeError):
        raise unauth_exc

    user = await user_repo.get_user_by_id(
        db, user_id
    )  # your repo excludes soft-deleted
    if not user:
        raise unauth_exc
    if getattr(user, "is_active", True) is False:
        raise HTTPException(status_code=403, detail="Inactive user")
    return user


async def get_current_user_id(
    user: Annotated[models.User, Depends(get_current_user)],
) -> int:
    return user.id


# Optional authorization helper
async def allow_self_or_admin(
    target_user_id: int,
    user: Annotated[models.User, Depends(get_current_user)],
) -> None:
    is_admin = (
        bool(getattr(user, "is_admin", False)) or getattr(user, "role", None) == "admin"
    )
    if user.id != target_user_id and not is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")
