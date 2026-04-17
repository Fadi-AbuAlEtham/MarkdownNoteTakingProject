from typing import Annotated, List

from fastapi import APIRouter, Depends, status
from fastapi.params import Path

from app.api.deps import get_revision_service
from app.schemas import revision as revision_schema
from app.services.revision import RevisionService


router = APIRouter(prefix="/revisions", tags=["revisions"])


@router.get(
    "/{revision_id}",
    response_model=revision_schema.RevisionResponse,
    status_code=status.HTTP_200_OK,
)
async def get_revision_by_id(
    revision_id: Annotated[int, Path(title="The ID of the revision to get", gt=0)],
    revision_service: RevisionService = Depends(get_revision_service),
):
    """
    Get a tag by ID.
    :param revision_id: Target revision ID.
    :param db: Async SQLAlchemy session.
    :param current_user_id: The ID of the current user.
    :return: The target revision.
    """
    return await revision_service.get_revision_by_id_and_user(revision_id=revision_id)


@router.get(
    "/",
    response_model=List[revision_schema.RevisionResponse],
    status_code=status.HTTP_200_OK,
)
async def get_all_active_revision(
    skip: int = 0,
    limit: int = 100,
    revision_service: RevisionService = Depends(get_revision_service),
):
    """
    Get all active revisions.
    :param skip: Starting offset
    :param limit: ending offset
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :return: List of all active tags for the current user
    """
    return await revision_service.get_all_active_revisions(skip=skip, limit=limit)


@router.get(
    "/notes/{note_id}/revisions",
    response_model=List[revision_schema.RevisionResponse],
    status_code=status.HTTP_200_OK,
)
async def get_revisions_for_note(
    note_id: Annotated[int, Path(title="The ID of the note to get", gt=0)],
    skip: int = 0,
    limit: int = 100,
    revision_service: RevisionService = Depends(get_revision_service),
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
        note_id=note_id, skip=skip, limit=limit
    )


@router.post(
    "/",
    response_model=revision_schema.RevisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_revision(
    revision: revision_schema.CreateRevision,
    revision_service: RevisionService = Depends(get_revision_service),
):
    """
    Create a new revision.
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :param revision: Pydantic model that holds the new revision payload
    :return: The newly created revision
    """
    return await revision_service.create_revision(revision_to_create=revision)


@router.put("/{revision_id}", response_model=revision_schema.RevisionResponse)
async def update_revision(
    revision: revision_schema.UpdateRevision,
    revision_id: int,
    revision_service: RevisionService = Depends(get_revision_service),
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
        revision_id=revision_id, updated_revision=revision
    )


@router.delete("/{revision_id}", response_model=revision_schema.RevisionResponse)
async def delete_revision(
    revision_id: int,
    revision_service: RevisionService = Depends(get_revision_service),
):
    """
    Delete a revision.
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :param revision_id:  of the revision to delete
    :return: The deleted revision
    """
    return await revision_service.soft_delete_revision(revision_id=revision_id)


@router.post(
    "/notes/{note_id}/revisions/{revision_id}/restore",
    response_model=revision_schema.RevisionResponse,
    status_code=status.HTTP_200_OK,
)
async def restore_revision(
    note_id: int,
    revision_id: int,
    revision_service: RevisionService = Depends(get_revision_service),
):
    return await revision_service.restore_revision(note_id=note_id, revision_id=revision_id)
