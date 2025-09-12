from typing import Annotated, List

from fastapi import APIRouter, Depends, status
from fastapi.params import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.core.db import get_db
from app.schemas import revision as revision_schema, note as note_schema
from app.services import revision_service


router = APIRouter(prefix="/revisions", tags=["revisions"])


@router.get(
    "/{revision_id}",
    response_model=revision_schema.RevisionResponse,
    status_code=status.HTTP_200_OK,
)
async def get_revision_by_id(
    revision_id: Annotated[int, Path(title="The ID of the revision to get", gt=0)],
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Get a tag by ID.
    :param revision_id: Target revision ID.
    :param db: Async SQLAlchemy session.
    :param current_user_id: The ID of the current user.
    :return: The target revision.
    """
    return await revision_service.get_revision_by_id_and_user(
        db, revision_id=revision_id, user_id=current_user_id
    )


@router.get(
    "/",
    response_model=List[revision_schema.RevisionResponse],
    status_code=status.HTTP_200_OK,
)
async def get_all_active_revision(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Get all active revisions.
    :param skip: Starting offset
    :param limit: ending offset
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :return: List of all active tags for the current user
    """
    return await revision_service.get_all_active_revisions(
        db, current_user_id, skip, limit
    )


@router.get(
    "/notes/{note_id}/revisions",
    response_model=List[revision_schema.RevisionResponse],
    status_code=status.HTTP_200_OK,
)
async def get_revisions_for_note(
    note_id: Annotated[int, Path(title="The ID of the note to get", gt=0)],
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Get all active revisions.
    :param note_id: Target note ID.
    :param skip: Starting offset
    :param limit: ending offset
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :return: List of all active tags for the current user
    """
    return await revision_service.get_revisions_for_note(
        db=db, user_id=current_user_id, skip=skip, limit=limit, note_id=note_id
    )


@router.post(
    "/",
    response_model=revision_schema.RevisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_revision(
    revision: revision_schema.CreateRevision,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Create a new revision.
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :param revision: Pydantic model that holds the new revision payload
    :return: The newly created revision
    """
    return await revision_service.create_revision(
        db, user_id=current_user_id, revision_to_create=revision
    )


@router.put("/{revision_id}", response_model=revision_schema.RevisionResponse)
async def update_revision(
    revision: revision_schema.UpdateRevision,
    revision_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Update a revision.
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :param revision_id: Target revision id
    :param revision: Pydantic model that holds the new revision payload
    :return: The updated revision
    """
    return await revision_service.update_revision(
        db, user_id=current_user_id, revision_id=revision_id, updated_revision=revision
    )


@router.delete("/{revision_id}", response_model=revision_schema.RevisionResponse)
async def delete_revision(
    revision_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Delete a revision.
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :param revision_id:  of the revision to delete
    :return: The deleted revision
    """
    return await revision_service.soft_delete_revision(
        db, user_id=current_user_id, revision_id=revision_id
    )


@router.post(
    "/notes/{note_id}/revisions/{revision_id}/restore",
    response_model=revision_schema.RevisionResponse,
    status_code=status.HTTP_200_OK,
)
async def restore_revision(
    note_id: int,
    revision_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    return await revision_service.restore_revision(
        db, current_user_id, note_id, revision_id
    )
