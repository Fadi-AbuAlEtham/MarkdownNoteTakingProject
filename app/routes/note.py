from typing import Annotated, List

from fastapi import APIRouter, Depends, status, Response
from fastapi.params import Path

from app.api.deps import get_note_service
from app.schemas import note as note_schema
from app.services.note import NoteService

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get(
    "/{note_id}",
    response_model=note_schema.NoteResponse,
    status_code=status.HTTP_200_OK,
)
async def get_note_by_id(
    note_id: Annotated[int, Path(title="The ID of the note to get", gt=0)],
    note_service: NoteService = Depends(get_note_service),
):
    """
    Get a note by ID.
    :param note_id: Target note ID.
    :param note_service: Note service to use
    :return: The target note.
    """
    return await note_service.get_note_by_id_and_user(note_id=note_id)


@router.get(
    "/",
    response_model=List[note_schema.NoteResponse],
    status_code=status.HTTP_200_OK,
)
async def get_all_active_note(
    skip: int = 0,
    limit: int = 100,
    note_service: NoteService = Depends(get_note_service),
):
    """
    Get all active notes.
    :param skip: Starting offset
    :param limit: ending offset
    :param note_service: Note service to use
    :return: List of all active notes for the current user
    """
    return await note_service.get_all_active_notes(skip=skip, limit=limit)


@router.post(
    "/",
    response_model=note_schema.NoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_note(
    note_to_create: note_schema.CreateNote,
    response: Response,
    note_service: NoteService = Depends(get_note_service),
):
    """
    Create a new note.
    :param note_to_create: Pydantic model that holds the new note payload
    :param response: Response model
    :param note_service: Note service to use
    :return: The newly created note
    """
    note, ignored = await note_service.create_note(note_to_create)
    if ignored:
        response.headers["X-Ignored-Tags"] = ",".join(map(str, ignored))
    return note


@router.put("/{note_id}", response_model=note_schema.NoteResponse)
async def update_note(
    note_to_update: note_schema.UpdateNote,
    note_id: int,
    response: Response,
    note_service: NoteService = Depends(get_note_service),
):
    """
    Update a note.
    :param note_id: Target note id
    :param response: Response model
    :param note_to_update: Pydantic model that holds the new note payload
    :param note_service: Note service to use
    :return: The updated note
    """
    note, ignored = await note_service.update_note(
        note_id=note_id, patch=note_to_update
    )
    if ignored:
        response.headers["X-Ignored-Tags"] = ",".join(map(str, ignored))
    return note


@router.delete("/{note_id}", response_model=note_schema.NoteResponse)
async def delete_note(
    note_id: int,
    note_service: NoteService = Depends(get_note_service),
):
    """
    Delete a note.
    :param note_id:  of the note to delete
    :param note_service: Note service to use
    :return: The deleted note
    """
    return await note_service.soft_delete_note(note_id=note_id)
