from typing import Annotated, List

from fastapi import APIRouter, Depends, status
from fastapi.params import Path

from app.api.deps import get_folder_service
from app.schemas import folder as folder_schema
from app.services.folder import FolderService

router = APIRouter(prefix="/folders", tags=["folders"])


@router.get(
    "/{folder_id}",
    response_model=folder_schema.FolderResponse,
    status_code=status.HTTP_200_OK,
)
async def get_folder_by_id(
    folder_id: Annotated[int, Path(title="The ID of the folder to get", gt=0)],
    folder_service: FolderService = Depends(get_folder_service),
):
    """
    Get a folder by ID.
    :param folder_id: Target folder ID.
    :param folder_service: Folder service to use.
    :return: The target folder.
    """
    return await folder_service.get_folder_by_and_user(folder_id=folder_id)


@router.get(
    "/",
    response_model=List[folder_schema.FolderResponse],
    status_code=status.HTTP_200_OK,
)
async def get_all_active_folders(
    skip: int = 0,
    limit: int = 100,
    folder_service: FolderService = Depends(get_folder_service),
):
    """
    Get all active folders.
    :param skip: Starting offset
    :param limit: End offset
    :param folder_service: Folder service to use.
    :return: List of all active folders for the current user
    """
    return await folder_service.get_all_active_folders(skip=skip, limit=limit)


@router.get(
    "{folder_id}/notes/",
    response_model=folder_schema.FolderWithNotesResponse,
    status_code=status.HTTP_200_OK,
)
async def get_active_notes_in_folder(
    folder_id: Annotated[
        int, Path(title="The ID of the folder to get the notes from", gt=0)
    ],
    folder_service: FolderService = Depends(get_folder_service),
):
    """
    Get all active notes in folder.
    :param folder_id: Target folder ID.
    :param folder_service: Folder service to use.
    :return: List of all active notes in a folder for the current user
    """
    return await folder_service.get_active_notes_in_folder(folder_id=folder_id)


@router.post(
    "/",
    response_model=folder_schema.FolderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_folder(
    folder: folder_schema.FolderCreate,
    folder_service: FolderService = Depends(get_folder_service),
):
    """
    Create a new folder.
    :param folder: Pydantic model that holds the new folder payload
    :param folder_service: Folder service to use.
    :return: The newly created folder
    """
    return await folder_service.create_folder(folder_to_create=folder)


@router.put("/{folder_id}", response_model=folder_schema.FolderResponse)
async def update_folder(
    folder: folder_schema.FolderUpdate,
    folder_id: int,
    folder_service: FolderService = Depends(get_folder_service),
):
    """
    Update a folder.
    :param folder_id: Target folder id
    :param folder: Pydantic model that holds the new folder payload
    :param folder_service: Folder service to use.
    :return: The updated folder
    """
    return await folder_service.update_folder(
        folder_id=folder_id, folder_to_update=folder
    )


@router.delete("/{folder_id}", response_model=folder_schema.FolderResponse)
async def delete_folder(
    folder_id: int,
    folder_service: FolderService = Depends(get_folder_service),
):
    """
    Delete a folder.
    :param folder_id: ID of the folder to delete
    :param folder_service: Folder service to use.
    :return: The deleted folder
    """
    return await folder_service.soft_delete_folder(folder_id=folder_id)
