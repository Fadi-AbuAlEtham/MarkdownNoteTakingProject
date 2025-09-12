from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas import revision as schemas_revision
from ..repositories import revision_repo


def to_response_dict(obj) -> dict:
    """
    Convert response to dict.
    :param obj: Response to convert.
    :return: Response dict.
    """
    return schemas_revision.RevisionResponse.model_validate(
        obj, from_attributes=True
    ).model_dump()


async def get_revision_by_id_and_user(db: AsyncSession, user_id: int, revision_id: int):
    """
    Get revision by id and user id.
    :param db: Async SQLAlchemy session.
    :param user_id: Target user ID.
    :param revision_id: Target revision ID.
    :return: Revision object.
    """
    revision = await revision_repo.get_revision_by_id_and_user(
        db, user_id=user_id, revision_id=revision_id
    )
    if not revision:
        raise HTTPException(status_code=404, detail="Revision not found")
    return to_response_dict(revision)


async def get_all_revisions(db: AsyncSession, skip: int = 0, limit: int = 100):
    """
    Get all revisions.
    :param db: Async SQLAlchemy session.
    :param skip: Number of revisions to skip.
    :param limit: Number of revisions to return.
    :return: List of revisions.
    """
    revisions = await revision_repo.get_all_revisions(db, skip=skip, limit=limit)
    return [to_response_dict(r) for r in revisions]


async def get_all_active_revisions(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
):
    """
    Get all active revisions.
    :param db: Async SQLAlchemy session.
    :param user_id: target user ID
    :param skip: Number of revisions to skip.
    :param limit: Number of revisions to return.
    :return: List of revisions.
    """
    revisions = await revision_repo.get_all_active_revisions(
        db, user_id, skip=skip, limit=limit
    )
    return [to_response_dict(r) for r in revisions]


async def get_revisions_for_note(
    db: AsyncSession, user_id: int, note_id: int, skip: int = 0, limit: int = 100
):
    """
    Get all revisions for a note.
    :param db: Async SQLAlchemy session.
    :param user_id: Target user ID.
    :param note_id: Target note ID.
    :param skip: Number of revisions to skip.
    :param limit: Number of revisions to return.
    :return: List of revisions.
    """
    revisions = await revision_repo.get_revisions_for_note(
        db, user_id=user_id, note_id=note_id, skip=skip, limit=limit
    )
    return [to_response_dict(r) for r in revisions]


async def create_revision(
    db: AsyncSession,
    user_id: int,
    revision_to_create: schemas_revision.CreateRevision,
):
    """
    Create new revision.
    :param db: Async SQLAlchemy session.
    :param user_id: Target user ID.
    :param revision_to_create: Pydantic model that holds the new revision payload.
    :return: Created revision_object.
    """
    try:
        revision = await revision_repo.create_revision(
            db,
            user_id=user_id,
            note_id=revision_to_create.note_id,
            revision=revision_to_create,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return to_response_dict(revision)


async def update_revision(
    db: AsyncSession,
    revision_id: int,
    user_id: int,
    updated_revision: schemas_revision.UpdateRevision,
):
    """
    Update existing revision.
    :param db: Async SQLAlchemy session.
    :param revision_id: Target revision ID.
    :param user_id: Target user ID.
    :param note_id: Target note ID.
    :param updated_revision: Pydantic model that holds the new revision payload.
    :return: Updated revision_object.
    """
    try:
        revision = await revision_repo.update_revision(
            db,
            user_id=user_id,
            note_id=updated_revision.note_id,
            revision_id=revision_id,
            updated_revision=updated_revision,
        )
    except ValueError as e:
        msg = str(e).lower()
        if "exist" in msg or "duplicate" in msg or "already" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    if not revision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
        )
    return to_response_dict(revision)


async def soft_delete_revision(db: AsyncSession, revision_id: int, user_id: int):
    """
    Soft delete revision.
    :param db: Async SQLAlchemy session.
    :param revision_id: Target revision ID.
    :param user_id: Target user ID.
    :return: Deleted revision_object.
    """
    try:
        revision = await revision_repo.soft_delete_by_id(db, user_id, revision_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return to_response_dict(revision)


async def restore_revision(
    db: AsyncSession, user_id: int, note_id: int, revision_id: int
):
    """
    Restore revision.
    :param db: Async SQLAlchemy session.
    :param revision_id: Target revision ID.
    :param user_id: Target user ID.
    :param note_id: Target note ID.
    :return: Restored revision_object.
    """
    try:
        revision = await revision_repo.restore_revision(
            db, user_id, note_id, revision_id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AttributeError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return to_response_dict(revision)
