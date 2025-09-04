from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists, func, update

from ..models import revision as models
from ..models import note as models
from ..schemas import revision as schemas


async def get_all_active_revisions(db: AsyncSession, skip: int = 0, limit: int = 100):
    """
    Get all active revisions
    :param db: Async SQLAlchemy session
    :param skip: Number of rows to skip (offset).
    :param limit: Maximum number of rows to return.
    :return: A list of revision objects that are not soft-deleted.
    """

    stmt = (
        select(models.NoteRevision)
        .where(models.NoteRevision.deleted_at.is_(None))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_all_revisions(db: AsyncSession, skip: int = 0, limit: int = 100):
    """
    Get all revisions
    :param db: Async SQLAlchemy session
    :param skip: Number of rows to skip (offset).
    :param limit: Maximum number of rows to return.
    :return: A list of all revision objects.
    """

    stmt = select(models.NoteRevision).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_revision_by_id(db: AsyncSession, revision_id: int):
    """
    Get revision by id
    :param db: Async SQLAlchemy session
    :param revision_id: Revision ID
    :return: Revision object or None if not found
    """

    stmt = (
        select(models.NoteRevision)
        .where(models.NoteRevision.id == revision_id)
        .where(models.NoteRevision.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_revision_by_id_and_user(db: AsyncSession, revision_id: int, user_id: int):
    """
    Get revision by id and user
    :param db: Async SQLAlchemy session
    :param revision_id: Revision ID
    :param user_id: User ID
    :return: Revision object or None if not found
    """

    stmt = (
        select(models.NoteRevision)
        .where(models.NoteRevision.id == revision_id)
        .where(models.NoteRevision.deleted_at.is_(None))
        .where(models.NoteRevision.user_id == user_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_revision_by_id_and_user_note(
    db: AsyncSession, revision_id: int, user_id: int, note_id: int
):
    """
    Get revision by id and user
    :param db: Async SQLAlchemy session
    :param revision_id: Revision ID
    :param user_id: User ID
    :param note_id: Note ID
    :return: Revision object or None if not found
    """

    stmt = (
        select(models.NoteRevision)
        .where(models.NoteRevision.id == revision_id)
        .where(models.NoteRevision.deleted_at.is_(None))
        .where(models.NoteRevision.user_id == user_id)
        .where(models.NoteRevision.note_id == note_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def check_revision_existence(
    db: AsyncSession, user_id: int, title: str, note_id: int
):
    """
    Check if revision exists for certain note and user
    :param db: Async SQLAlchemy session
    :param user_id: User ID
    :param title: Revision title
    :param note_id: Revision note ID
    :return: True if revision exists for this note; otherwise False.
    """

    stmt = select(
        exists()
        .where(models.NoteRevision.user_id == user_id)
        .where(models.NoteRevision.title == title.strip())
        .where(models.NoteRevision.note_id == note_id)
        .where(models.NoteRevision.deleted_at.is_(None))
    )
    return await db.scalar(stmt)


async def create_revision(
    db: AsyncSession, revision: schemas.CreateRevision, note_id: int, user_id: int
):
    """
    Create new revision
    :param db: Async SQLAlchemy session
    :param revision: Revision object
    :param note_id: Revision note ID
    :param user_id: User ID
    :return: Revision object or None if not created
    """

    note = await db.scalar(
        select(models.Note).where(
            models.Note.id == note_id,
            models.Note.user_id == user_id,
            models.Note.deleted_at.is_(None),
        )
    )
    if note is None:
        raise ValueError("Note not found or not accessible")

    if await check_revision_existence(
        db, user_id=user_id, note_id=note_id, title=revision.title
    ):
        raise ValueError(
            f"A revision titled '{revision.title}' already exists for this note."
        )

    # ToDo: fix the version logic, note that the note has version attribute which can
    #  be used to get the current version of the note then compute the next version from it
    next_version = await db.scalar(
        update(models.Note)
        .where(models.Note.id == note_id)
        .values(current_version=models.Note.current_version + 1)
        .returning(models.Note.current_version)
    )

    payload = revision.model_dump(exclude={"version", "created_by"})
    payload.update({"note_id": note_id, "user_id": user_id, "version": next_version})

    db_rev = models.NoteRevision(**payload)
    db.add(db_rev)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # Very rare with atomic counter; unique (note_id, version) is final safety net.
        raise ValueError("Concurrent revision creation conflict; please retry.")

    await db.refresh(db_rev)
    return db_rev


async def update_revision(
    db: AsyncSession,
    revision_id: int,
    updated_revision: schemas.UpdateRevision,
    note_id: int,
    user_id: int,
):
    """
    Update revision
    :param db: Async SQLAlchemy session
    :param revision_id: Revision ID
    :param updated_revision: Revision object
    :param note_id: Revision note ID
    :param user_id: User ID
    :return: Revision object or None if not updated
    """

    revision = await get_revision_by_id_and_user_note(
        db=db, revision_id=revision_id, user_id=user_id, note_id=note_id
    )
    if not revision:
        raise ValueError(f"No revision #{revision_id} found for note #{note_id}")

    data = updated_revision.model_dump(exclude_unset=True)

    if "title" in data:
        stmt = select(
            exists()
            .where(models.NoteRevision.title == updated_revision.title)
            # Exclude the current revision while updating to check other revisions
            .where(models.NoteRevision.id != revision_id)
            .where(models.NoteRevision.deleted_at.is_(None))
            .where(models.NoteRevision.user_id == user_id)
            .where(models.NoteRevision.note_id == note_id)
        )
        if await db.scalar(stmt):
            raise ValueError(f"This title: {updated_revision.title} is already in use")

    for key, value in data.items():
        setattr(revision, key, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        title_for_msg = data.get("title", revision.title)
        # DB-level partial UNIQUE index is the final arbiter; translate race to a friendly message
        raise ValueError(f"A revision named '{title_for_msg}' already exists")

    await db.refresh(revision)
    return revision


async def soft_delete_by_id(db: AsyncSession, user_id: int, revision_id: int):
    """
        Soft delete a revision.
    :param db: Async SQLAlchemy session.
    :param user_id: Target User ID.
    :param revision_id: Target revision ID
    :return: The updated revision instance with "deleted_at" and "is_active" attributes.
    """

    revision = await get_revision_by_id_and_user(db, user_id, revision_id)
    if revision is None:
        raise ValueError("This revision doesn't exist")

    revision.deleted_at = datetime.now(timezone.utc)
    revision.is_active = False
    await db.commit()
    await db.refresh(revision)
    return revision
