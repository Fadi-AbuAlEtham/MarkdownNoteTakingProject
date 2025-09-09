from typing import Annotated, List

from fastapi import APIRouter, Depends
from fastapi.params import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.schemas import user as user_schema
from app.services import user_service


router = APIRouter(prefix="/users", tags=["user"])


async def get_db():
    async with SessionLocal() as session:
        yield session


@router.get("/{user_id}", response_model=user_schema.UserResponse, status_code=200)
async def get_user_by_id(
    user_id: Annotated[int, Path(title="The ID of the user to get", gt=0)],
    db: AsyncSession = Depends(get_db),
):
    """
    Get a user by ID.
    :param user_id: The ID of the user to get.
    :param db: The database to use.
    :return: The user.
    """
    return await user_service.get_user_by_id(db, user_id)


@router.get("/", response_model=List[user_schema.UserResponse], status_code=200)
async def get_all_users(
    db: AsyncSession = Depends(get_db), skip: int = 0, limit: int = 100
):
    """
    Get all users.
    :param db: The database to use.
    :param skip: The number of users to skip.
    :param limit: The number of users to limit.
    :return: List of all users.
    """
    return await user_service.get_all_users(db, skip=skip, limit=limit)


@router.get("/", response_model=List[user_schema.UserResponse], status_code=200)
async def get_all_active_users(
    db: AsyncSession = Depends(get_db), skip: int = 0, limit: int = 100
):
    """
    Get all active users.
    :param db: The database to use.
    :param skip: The number of users to skip.
    :param limit: The number of users to limit.
    :return: List of all active users.
    """
    return await user_service.get_all_active_users(db, skip=skip, limit=limit)


@router.post("/", response_model=user_schema.UserResponse, status_code=201)
async def create_user(user: user_schema.CreateUser, db: AsyncSession = Depends(get_db)):
    """
    Create a new user.
    :param db: The database to use.
    :param user: The new user to create.
    :return: The created user.
    """
    return await user_service.create_user(db, user)


@router.put("/{user_id}", response_model=user_schema.UserResponse, status_code=200)
async def update_user(
    user: user_schema.UpdateUser,
    user_id: Annotated[int, Path(title="The ID of the user to get", gt=0)],
    db: AsyncSession = Depends(get_db),
):
    """
    Update a user.
    :param db: The database to use.
    :param user_id: The ID of the user to update.
    :param user: The user to update.
    :return: The updated user.
    """
    return await user_service.update_user(db, user_id, user)


@router.delete("/{user_id}", response_model=user_schema.UserResponse, status_code=200)
async def soft_delete_user(
    user_id: Annotated[int, Path(title="The ID of the user to get", gt=0)],
    db: AsyncSession = Depends(get_db),
):
    """
    Soft-delete a user.
    :param db: The database to use.
    :param user_id: The ID of the user to delete.
    :return: The deleted user.
    """
    return await user_service.soft_delete_user(db, user_id)
