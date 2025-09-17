from typing import Annotated, List

from fastapi import APIRouter
from fastapi.params import Path, Depends

from app.api.deps import get_user_service
from app.schemas import user as user_schema
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["user"])


@router.get("/{user_id}", response_model=user_schema.UserResponse, status_code=200)
async def get_user_by_id(
    user_id: Annotated[int, Path(title="The ID of the user to get", gt=0)],
    user_service: UserService = Depends(get_user_service),
):
    """
    Get a user by ID.
    :param user_id: The ID of the user to get.
    :param user_service: user service module
    :return: The user.
    """
    return await user_service.get_user_by_id(user_id)


@router.get("/", response_model=List[user_schema.UserResponse], status_code=200)
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    user_service: UserService = Depends(get_user_service),
):
    """
    Get all users.
    :param skip: The number of users to skip.
    :param limit: The number of users to limit.
    :param user_service: user service module
    :return: List of all users.
    """
    return await user_service.get_all_users(skip=skip, limit=limit)


@router.get("/", response_model=List[user_schema.UserResponse], status_code=200)
async def get_all_active_users(
    skip: int = 0,
    limit: int = 100,
    user_service: UserService = Depends(get_user_service),
):
    """
    Get all active users.
    :param skip: The number of users to skip.
    :param limit: The number of users to limit.
    :param user_service: user service module
    :return: List of all active users.
    """
    return await user_service.get_all_active_users(skip=skip, limit=limit)


@router.post("/", response_model=user_schema.UserResponse, status_code=201)
async def create_user(
    user: user_schema.CreateUser, user_service: UserService = Depends(get_user_service)
):
    """
    Create a new user.
    :param user: The new user to create.
    :param user_service: user service module
    :return: The created user.
    """
    return await user_service.create_user(user)


@router.put("/{user_id}", response_model=user_schema.UserResponse, status_code=200)
async def update_user(
    user: user_schema.UpdateUser,
    user_id: Annotated[int, Path(title="The ID of the user to get", gt=0)],
    user_service: UserService = Depends(get_user_service),
):
    """
    Update a user.
    :param user_id: The ID of the user to update.
    :param user: The user to update.
    :param user_service: user service module
    :return: The updated user.
    """
    return await user_service.update_user(user_id, user)


@router.delete("/{user_id}", response_model=user_schema.UserResponse, status_code=200)
async def soft_delete_user(
    user_id: Annotated[int, Path(title="The ID of the user to get", gt=0)],
    user_service: UserService = Depends(get_user_service),
):
    """
    Soft-delete a user.
    :param user_id: The ID of the user to delete.
    :param user_service: user service module
    :return: The deleted user.
    """
    return await user_service.soft_delete_user(user_id)
