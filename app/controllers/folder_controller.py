from typing import Annotated, List

from fastapi import APIRouter, Depends, status
from fastapi.params import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.core.db import get_db
from app.schemas import folder as folder_schema
from app.services import folder_service

router = APIRouter(prefix="/folders", tags=["folders"])


@router.get(
    "/{folder_id}",
    response_model=folder_schema.FolderResponse,
    status_code=status.HTTP_200_OK,
)
async def get_folder_by_id(
    folder_id: Annotated[int, Path(title="The ID of the folder to get", gt=0)],
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Get a folder by ID.
    :param folder_id: Target folder ID.
    :param db: Async SQLAlchemy session.
    :param current_user_id: The ID of the current user.
    :return: The target folder.
    """
    return await folder_service.get_folder_by_and_user(
        db, folder_id=folder_id, user_id=current_user_id
    )


@router.get(
    "/",
    response_model=List[folder_schema.FolderResponse],
    status_code=status.HTTP_200_OK,
)
async def get_all_active_folders(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Get all active folders.
    :param skip: Starting offset
    :param limit: End offset
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :return: List of all active folders for the current user
    """
    return await folder_service.get_all_active_folders(db, current_user_id, skip, limit)


@router.get(
    "{folder_id}/notes/",
    response_model=folder_schema.FolderWithNotesResponse,
    status_code=status.HTTP_200_OK,
)
async def get_active_notes_in_folder(
    folder_id: Annotated[
        int, Path(title="The ID of the folder to get the notes from", gt=0)
    ],
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Get all active notes in folder.
    :param folder_id: Target folder ID.
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :return: List of all active notes in a folder for the current user
    """
    return await folder_service.get_active_notes_in_folder(
        db, user_id=current_user_id, folder_id=folder_id
    )


@router.post(
    "/",
    response_model=folder_schema.FolderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_folder(
    folder: folder_schema.FolderCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Create a new folder.
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :param folder: Pydantic model that holds the new folder payload
    :return: The newly created folder
    """
    return await folder_service.create_folder(
        db, user_id=current_user_id, folder_to_create=folder
    )


@router.put("/{folder_id}", response_model=folder_schema.FolderResponse)
async def update_folder(
    folder: folder_schema.FolderUpdate,
    folder_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Update a folder.
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :param folder_id: Target folder id
    :param folder: Pydantic model that holds the new folder payload
    :return: The updated folder
    """
    return await folder_service.update_folder(
        db, user_id=current_user_id, folder_id=folder_id, folder_to_update=folder
    )


@router.delete("/{folder_id}", response_model=folder_schema.FolderResponse)
async def delete_folder(
    folder_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Delete a folder.
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :param folder_id: ID of the folder to delete
    :return: The deleted folder
    """
    return await folder_service.soft_delete_folder(
        db, user_id=current_user_id, folder_id=folder_id
    )
