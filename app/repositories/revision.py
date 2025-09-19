from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists, func, update
from sqlalchemy.orm import selectinload

from ..models import revision as rev_models
from ..models import note as note_models
from ..models.revision import NoteRevision
from ..schemas import revision as schemas


async def get_all_active_revisions(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
):
    """
    Get all active revisions
    :param db: Async SQLAlchemy session
    :param user_id: target user id
    :param skip: Number of rows to skip (offset).
    :param limit: Maximum number of rows to return.
    :return: A list of revision objects that are not soft-deleted.
    """

    stmt = (
        select(rev_models.NoteRevision)
        .where(rev_models.NoteRevision.deleted_at.is_(None))
        .where(rev_models.NoteRevision.user_id == user_id)
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

    stmt = select(rev_models.NoteRevision).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_revisions_for_note(
    db: AsyncSession, user_id: int, note_id: int, skip: int = 0, limit: int = 100
):
    """
    Get all revisions for a note
    :param db: Async SQLAlchemy session
    :param user_id: target user id
    :param note_id: target note id
    :param skip: Number of rows to skip (offset).
    :param limit: Maximum number of rows to return.
    :return: A list of revision objects that are not soft-deleted.
    """
    stmt = (
        select(rev_models.NoteRevision)
        .where(rev_models.NoteRevision.user_id == user_id)
        .where(rev_models.NoteRevision.note_id == note_id)
        .offset(skip)
        .limit(limit)
    )
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
        select(rev_models.NoteRevision)
        .where(rev_models.NoteRevision.id == revision_id)
        .where(rev_models.NoteRevision.deleted_at.is_(None))
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
        select(rev_models.NoteRevision)
        .where(rev_models.NoteRevision.id == revision_id)
        .where(rev_models.NoteRevision.deleted_at.is_(None))
        .where(rev_models.NoteRevision.user_id == user_id)
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
        select(rev_models.NoteRevision)
        .where(rev_models.NoteRevision.id == revision_id)
        .where(rev_models.NoteRevision.deleted_at.is_(None))
        .where(rev_models.NoteRevision.user_id == user_id)
        .where(rev_models.NoteRevision.note_id == note_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def check_revision_existence(
    db: AsyncSession, user_id: int, note_id: int, version: int
):
    """
    Check if revision exists for certain note and user
    :param db: Async SQLAlchemy session
    :param user_id: User ID
    :param note_id: Revision note ID
    :param version: target version
    :return: True if revision exists for this note; otherwise False.
    """

    stmt = select(
        exists()
        .where(rev_models.NoteRevision.user_id == user_id)
        .where(rev_models.NoteRevision.note_id == note_id)
        .where(rev_models.NoteRevision.deleted_at.is_(None))
        .where(rev_models.NoteRevision.version == version)
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

    try:
        async with db.begin_nested():
            note = await db.scalar(
                select(note_models.Note)
                .options(selectinload(note_models.Note.tags))
                .where(
                    note_models.Note.id == note_id,
                    note_models.Note.user_id == user_id,
                    note_models.Note.deleted_at.is_(None),
                )
            )
            if not note:
                raise ValueError("Note not found or not accessible")

            # bump version
            res = await db.execute(
                update(note_models.Note)
                .where(note_models.Note.id == note_id)
                .values(version=note_models.Note.version + 1, updated_at=func.now())
                .returning(note_models.Note.version)
            )
            row = res.first()
            if not row:
                raise ValueError("Note not found or not accessible")
            new_version: int = int(row[0])

            payload = revision.model_dump(
                exclude={"version", "created_by", "note_id", "tag_ids"},  # <— add this
                exclude_none=True,
                exclude_defaults=True,
            )

            db_rev = rev_models.NoteRevision(
                **payload, note_id=note_id, user_id=user_id, version=new_version
            )
            db_rev.tags = list(note.tags)
            db.add(db_rev)

        await db.commit()
        await db.refresh(db_rev)
        return db_rev

    except IntegrityError as e:
        await db.rollback()
        raise ValueError("Concurrent revision creation conflict; please retry.") from e


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
            .where(rev_models.NoteRevision.title == updated_revision.title)
            # Exclude the current revision while updating to check other revisions
            .where(rev_models.NoteRevision.id != revision_id)
            .where(rev_models.NoteRevision.deleted_at.is_(None))
            .where(rev_models.NoteRevision.user_id == user_id)
            .where(rev_models.NoteRevision.note_id == note_id)
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

    revision = await get_revision_by_id_and_user(db, revision_id, user_id)
    if revision is None:
        raise ValueError("This revision doesn't exist")

    revision.deleted_at = datetime.now(timezone.utc)
    revision.is_active = False
    await db.commit()
    await db.refresh(revision)
    return revision


async def restore_revision(
    db: AsyncSession, user_id: int, note_id: int, revision_id: int
):
    """
    Restore a revision.
    :param db: Async SQLAlchemy session.
    :param user_id: Target User ID.
    :param note_id: Revision note ID.
    :param revision_id: Revision ID
    :return: The updated revision instance with "deleted_at" and "is_active" attributes.
    """
    rev: NoteRevision = await db.scalar(
        select(rev_models.NoteRevision)
        .options(selectinload(rev_models.NoteRevision.tags))
        .where(
            rev_models.NoteRevision.id == revision_id,
            rev_models.NoteRevision.user_id == user_id,
            rev_models.NoteRevision.note_id == note_id,
            rev_models.NoteRevision.deleted_at.is_(None),
        )
    )
    if not rev:
        raise ValueError("Revision not found")

    note = await db.scalar(
        select(note_models.Note)
        .options(selectinload(note_models.Note.tags))
        .where(
            note_models.Note.id == note_id,
            note_models.Note.user_id == user_id,
            note_models.Note.deleted_at.is_(None),
        )
    )
    if not note:
        raise ValueError("Note not found or not accessible")

    rev_tag_ids = {t.id for t in (rev.tags or [])}
    note_tag_ids = {t.id for t in (note.tags or [])}

    if (
        (rev.title or "").strip() == (note.title or "").strip()
        and (rev.content_md or "") == (note.content_md or "")
        and bool(getattr(rev, "is_public", note.is_public)) == bool(note.is_public)
        and getattr(rev, "folder_id", note.folder_id) == note.folder_id
        and rev_tag_ids == note_tag_ids
    ):
        raise ValueError(
            "Revision is identical to the current note; nothing to restore."
        )

    try:
        # bump note version & update fields
        res = await db.execute(
            update(note_models.Note)
            .where(
                note_models.Note.id == note_id,
                note_models.Note.user_id == user_id,
                note_models.Note.deleted_at.is_(None),
            )
            .values(
                title=rev.title,
                content_md=rev.content_md,
                is_public=getattr(rev, "is_public", note.is_public),
                folder_id=getattr(rev, "folder_id", note.folder_id),
                version=note_models.Note.version + 1,
                updated_at=func.now(),
            )
            .returning(
                note_models.Note.version,
                note_models.Note.title,
                note_models.Note.content_md,
                note_models.Note.is_public,
                note_models.Note.folder_id,
            )
        )
        row = res.first()
        if not row:
            raise ValueError("Note not found or not accessible")

        new_version, new_title, new_content_md, new_is_public, new_folder_id = row

        note.tags = list(rev.tags)

        restored = rev_models.NoteRevision(
            note_id=note_id,
            user_id=user_id,
            version=int(new_version),
            title=new_title,
            content_md=new_content_md,
            is_public=new_is_public,
            folder_id=new_folder_id,
        )
        restored.tags = list(rev.tags)
        db.add(restored)

        await db.commit()
        await db.refresh(restored)
        return restored

    except Exception:
        await db.rollback()
        raise
