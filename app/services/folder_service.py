from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas import folder as schemas_issue
from ..repositories import folder_repo


def to_response_dict(obj) -> dict:
    """
    Convert response to dict.
    :param obj: Response to convert.
    :return: Response dict.
    """
    return schemas_issue.FolderResponse.model_validate(
        obj, from_attributes=True
    ).model_dump()


async def get_folder_by_and_user(db: AsyncSession, user_id: int, folder_id: int):
    """
    Get folder by and user
    :param db: Async SQLAlchemy session
    :param user_id: Target user id
    :param folder_id: Target folder id
    :return: Folder object
    """
    folder = await folder_repo.get_folder_by_id_and_user(db, user_id, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    return to_response_dict(folder)


async def get_all_active_folders(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
):
    """
    Get all active folders
    :param db: Async SQLAlchemy session
    :param user_id: Target user_id
    :param skip: Number of items to skip
    :param limit: Number of items to return
    :return: List of all active folders
    """
    folders = await folder_repo.get_all_active_folders(
        db, user_id=user_id, skip=skip, limit=limit
    )
    return [to_response_dict(f) for f in folders]


async def create_folder(
    db: AsyncSession, user_id: int, folder_to_create: schemas_issue.FolderCreate
):
    """
    Create new folder
    :param db: Async SQLAlchemy session
    :param user_id: Target user id
    :param folder_to_create: Pydantic model that holds the new folder payload
    :return: Created folder
    """
    try:
        folder = await folder_repo.create_folder(db, user_id, folder_to_create)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return to_response_dict(folder)


async def update_folder(
    db: AsyncSession,
    user_id: int,
    folder_id: int,
    folder_to_update: schemas_issue.FolderUpdate,
):
    """
    Update folder
    :param db: Async SQLAlchemy session
    :param user_id: Target user id
    :param folder_id: Target folder id
    :param folder_to_update: Pydantic model that holds the new folder payload
    :return: Updated folder
    """
    try:
        folder = await folder_repo.update_folder(
            db, user_id, folder_id, folder_to_update
        )
    except ValueError as e:
        msg = str(e).lower()
        if "exist" in msg or "duplicate" in msg or "already" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
        )
    return to_response_dict(folder)


async def soft_delete_folder(db: AsyncSession, user_id: int, folder_id: int):
    """
    Soft-delete folder
    :param db: Async SQLAlchemy session
    :param user_id: Target user id
    :param folder_id: Target folder id
    :return: Soft-deleted folder
    """
    try:
        folder = await folder_repo.soft_delete_folder_by_id(
            db, user_id=user_id, folder_id=folder_id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return to_response_dict(folder)
