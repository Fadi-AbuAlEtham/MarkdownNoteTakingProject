from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.jwt import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.repositories import user_repo
from app.core.security import verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Login a user by username and password.
    :param body: The body of the login.
    :param db: The database to use.
    :raises HTTPException: If the login fails.
    :return: The login token.
    """
    user = await user_repo.get_user_by_username(db, body.username)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    if getattr(user, "is_active", True) is False:
        raise HTTPException(status_code=403, detail="Inactive user")

    token = create_access_token(user.id, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": token, "token_type": "bearer"}


@router.get("/logout")
async def logout():
    """
    Logout the current user.
    :param db: The database to use.
    """
    return {"message": "Successfully logged out"}
