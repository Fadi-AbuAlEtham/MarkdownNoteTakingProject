from typing import Annotated, List

from fastapi import APIRouter, Depends, status
from fastapi.params import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.core.db import get_db
from app.schemas import note as note_schema
from app.services import note_service

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get(
    "/{note_id}",
    response_model=note_schema.NoteResponse,
    status_code=status.HTTP_200_OK,
)
async def get_note_by_id(
    note_id: Annotated[int, Path(title="The ID of the note to get", gt=0)],
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Get a note by ID.
    :param note_id: Target note ID.
    :param db: Async SQLAlchemy session.
    :param current_user_id: The ID of the current user.
    :return: The target note.
    """
    return await note_service.get_note_by_id_and_user(
        db, note_id=note_id, user_id=current_user_id
    )


@router.get(
    "/",
    response_model=List[note_schema.NoteResponse],
    status_code=status.HTTP_200_OK,
)
async def get_all_active_note(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Get all active notes.
    :param skip: Starting offset
    :param limit: ending offset
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :return: List of all active notes for the current user
    """
    return await note_service.get_all_active_notes(db, current_user_id, skip, limit)


@router.post(
    "/",
    response_model=note_schema.NoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_note(
    note: note_schema.CreateNote,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Create a new note.
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :param note: Pydantic model that holds the new note payload
    :return: The newly created note
    """
    return await note_service.create_note(db, user_id=current_user_id, note=note)


@router.put("/{note_id}", response_model=note_schema.NoteResponse)
async def update_note(
    note: note_schema.UpdateNote,
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Update a note.
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :param note_id: Target note id
    :param note: Pydantic model that holds the new note payload
    :return: The updated note
    """
    return await note_service.update_note(
        db, user_id=current_user_id, note_id=note_id, note=note
    )


@router.delete("/{note_id}", response_model=note_schema.NoteResponse)
async def delete_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Delete a note.
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :param note_id:  of the note to delete
    :return: The deleted note
    """
    return await note_service.soft_delete_note(
        db, user_id=current_user_id, note_id=note_id
    )
