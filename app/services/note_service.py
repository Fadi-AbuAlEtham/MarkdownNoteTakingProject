from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas import note as schemas_note
from ..repositories import note_repo, revision_repo


def to_response_dict(obj) -> dict:
    """
    Convert response to dict.
    :param obj: Response to convert.
    :return: Response dict.
    """
    return schemas_note.NoteResponse.model_validate(
        obj, from_attributes=True
    ).model_dump()


async def get_note_by_id_and_user(db: AsyncSession, user_id: int, note_id: int):
    """
    Get note by id and user
    :param db: Async SQLAlchemy session.
    :param user_id: Target user id
    :param note_id: Target note id
    :return: Target note object.
    """
    note = await note_repo.get_note_by_id_user(db, user_id=user_id, note_id=note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return to_response_dict(note)


async def get_all_active_notes(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
):
    """
    Get all active notes
    :param db: Async SQLAlchemy session.
    :param user_id: Target user id.
    :param skip: Skip-cursor.
    :param limit: Limit cursor.
    :return: All active notes.
    """
    notes = await note_repo.get_all_active_notes(db, user_id, skip=skip, limit=limit)
    return [to_response_dict(n) for n in notes]


async def create_note(
    db: AsyncSession, user_id: int, note_to_create: schemas_note.CreateNote
):
    """
    Create new note
    :param db: Async SQLAlchemy session.
    :param user_id: Target user id
    :param note_to_create: Pydantic model that holds the new note payload.
    :return: New note object.
    """
    try:
        note, ignored = await note_repo.create_note(db, user_id, note_to_create)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return to_response_dict(note), ignored


async def update_note(
    db: AsyncSession, user_id: int, note_id: int, note: schemas_note.UpdateNote
):
    """
    Update existing note
    :param db: Async SQLAlchemy session.
    :param user_id: Target user id
    :param note_id: Target note id
    :param note: Pydantic model that holds the new note payload.
    :return: Updated note object.
    """
    try:
        note, ignored = await note_repo.update_note(
            db, user_id=user_id, note_id=note_id, updated_note=note
        )
    except ValueError as e:
        msg = str(e).lower()
        if "exist" in msg or "duplicate" in msg or "already" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
        )
    return to_response_dict(note), ignored


async def soft_delete_note(db: AsyncSession, user_id: int, note_id: int):
    """
    Soft-delete existing note
    :param db: Async SQLAlchemy session.
    :param user_id: Target user id
    :param note_id: Target note id
    :return: Deleted note-object.
    """
    try:
        note = await note_repo.soft_delete_by_id(db, user_id, note_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return to_response_dict(note)
