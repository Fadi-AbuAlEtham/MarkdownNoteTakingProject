from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas import user as schemas_user
from ..repositories import user_repo


def to_response_dict(obj) -> dict:
    """
    Convert response to dict.
    :param obj: Response to convert.
    :return: Response dict.
    """
    return schemas_user.UserResponse.model_validate(
        obj, from_attributes=True
    ).model_dump()


async def get_user_by_id(db: AsyncSession, user_id: int):
    """
    Get user by id
    :param db: Async SQLAlchemy session.
    :param user_id: Target User id.
    :return: User object.
    """
    user = await user_repo.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return to_response_dict(user)


async def get_all_active_users(db: AsyncSession, skip: int = 0, limit: int = 100):
    """
    Get all active users
    :param db: Async SQLAlchemy session.
    :param skip: Number of rows to skip (offset).
    :param limit: Maximum number of rows to return.
    :return: User list.
    """
    users = await user_repo.get_all_active_users(db, skip=skip, limit=limit)
    return [to_response_dict(user) for user in users]


async def get_all_users(db: AsyncSession, skip: int = 0, limit: int = 100):
    """
    Get all users
    :param db: Async SQLAlchemy session.
    :param skip: Number of rows to skip (offset).
    :param limit: Maximum number of rows to return.
    :return: User list.
    """
    users = await user_repo.get_all_users(db, skip=skip, limit=limit)
    return [to_response_dict(user) for user in users]


async def create_user(db: AsyncSession, payload: schemas_user.CreateUser):
    """
    Create new user
    :param db: Async SQLAlchemy session.
    :param payload: Pydantic model that holds the new user payload.
    :return: User created object.
    """
    try:
        user = await user_repo.create_user(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return to_response_dict(user)


async def update_user(db: AsyncSession, user_id: int, payload: schemas_user.UpdateUser):
    """
    Update user
    :param db: Async SQLAlchemy session.
    :param user_id: Target User id.
    :param payload: Pydantic model that holds the new user payload.
    :return: User updated object.
    """
    try:
        user = await user_repo.update_user(db, user_id, payload)
    except ValueError as e:
        msg = str(e).lower()
        if "exist" in msg or "already" in msg or "in use" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return to_response_dict(user)


async def soft_delete_user(db: AsyncSession, user_id: int):
    """
    Soft-delete user
    :param db: Async SQLAlchemy session.
    :param user_id: Target User id.
    :return: User deleted object.
    """
    try:
        user = await user_repo.soft_delete_user_by_id(db, user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return to_response_dict(user)
