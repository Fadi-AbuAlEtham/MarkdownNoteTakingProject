from datetime import timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_auth_service
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(
    body: LoginRequest, auth_service: AuthService = Depends(get_auth_service)
):
    """
    Login a user by username and password.
    :param body: The body of the login.
    :param db: The database to use.
    :raises HTTPException: If the login fails.
    :return: The login token.
    """
    return await auth_service.login(body.username, body.password)
