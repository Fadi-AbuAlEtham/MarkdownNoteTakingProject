from datetime import datetime, timezone
from typing import Optional, Any, Coroutine

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists, and_, update, func, RowMapping, Row
from sqlalchemy.orm import selectinload

from ..models import note as models, revision as rev_models
from ..models.tag import Tag
from app.models.tag import note_tags
from ..schemas import note as schemas
from ..repositories import folder_repo


async def get_all_active_notes(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
):
    """
    Get all active (non-deleted) notes.
    :param db: Async SQLAlchemy session.
    :param user_id: target user id.
    :param skip: Number of rows to skip.
    :param limit: Number of rows to limit.
    :return: List of active notes.
    """
    stmt = (
        select(models.Note)
        .where(models.Note.deleted_at.is_(None))
        .where(models.Note.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_all_notes(db: AsyncSession, skip: int = 0, limit: int = 100):
    """
    Get all notes (deleted and non-deleted).
    :param db: Async SQLAlchemy session.
    :param skip: Number of rows to skip.
    :param limit: Number of rows to limit.
    :return: List of notes.
    """
    stmt = select(models.Note).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_all_active_notes_user(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
):
    """
    Get all active (non-deleted) notes for a certain user.
    :param db: Async SQLAlchemy session.
    :param user_id: Target user id.
    :param skip: Number of rows to skip.
    :param limit: Number of rows to limit.
    :return: List of active notes.
    """
    stmt = (
        select(models.Note)
        .where(models.Note.deleted_at.is_(None))
        .where(models.Note.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_active_notes_in_folder(db, user_id: int, folder_id: int):
    """
    Get all active (non-deleted) notes for a certain folder.
    :param db: Async SQLAlchemy session.
    :param user_id: Target user id.
    :param folder_id: Target folder id.
    :return: List of active notes.
    """
    stmt = (
        select(models.Note)
        .where(
            models.Note.user_id == user_id,
            models.Note.folder_id == folder_id,
            models.Note.deleted_at.is_(None),
        )
        .order_by(models.Note.updated_at.desc())
        .options(
            selectinload(models.Note.tags),
            selectinload(models.Note.folder),
        )
    )
    res = await db.execute(stmt)
    return res.scalars().all()


async def get_active_notes_by_tag(db, user_id: int, tag_id: int):
    """
    Return the user's active notes that are associated with a given tag.
    """
    stmt = (
        select(models.Note)
        .join(note_tags, note_tags.c.note_id == models.Note.id)
        .where(
            models.Note.user_id == user_id,
            note_tags.c.tag_id == tag_id,
            models.Note.deleted_at.is_(None),
        )
        .order_by(models.Note.updated_at.desc())
        .options(
            selectinload(models.Note.tags),
            selectinload(models.Note.folder),
        )
    )
    res = await db.execute(stmt)
    return res.scalars().all()


async def get_note_by_id_user(db: AsyncSession, note_id: int, user_id: int):
    """
    Get a note by id for a certain user.
    :param db: Async SQLAlchemy session.
    :param note_id: Target note id.
    :param user_id: Target user id.
    :return: Note or None if not found.
    """
    stmt = (
        select(models.Note)
        .where(models.Note.deleted_at.is_(None))
        .where(models.Note.id == note_id)
        .where(models.Note.user_id == user_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def check_note_existence(
    db: AsyncSession, title: str, user_id: int, folder_id: Optional[int] = None
) -> bool:
    """
    Check if a note exists for a certain user.
    If folder_id is provided, constrain to that folder.
    If folder_id is None, check across all user's notes (regardless of folder).

    :return: True if the note exists and False otherwise.
    """
    conditions = [
        models.Note.title == title.strip(),
        models.Note.user_id == user_id,
        models.Note.deleted_at.is_(None),
    ]
    if folder_id is not None:
        conditions.append(models.Note.folder_id == folder_id)

    stmt = select(exists().where(and_(*conditions)))
    result = await db.execute(stmt)
    return bool(result.scalar())


async def create_note(db: AsyncSession, user_id: int, note: schemas.CreateNote):
    """
    Create a new note.
    :param db: Async SQLAlchemy session.
    :param user_id: Target user id.
    :param note: Pydantic payload containing note's fields.
    :return: The created note instance.
    """
    if note.folder_id is not None:
        folder_exists = await folder_repo.get_folder_by_id_and_user(
            db=db, user_id=user_id, folder_id=note.folder_id
        )
        if not folder_exists:
            raise ValueError(f"Folder with id {note.folder_id} was not found.")

    ignored_tag_ids: list[int] = []
    valid_tag_ids: set[int] = set()

    if note.tag_ids:
        candidate_ids = {int(t) for t in note.tag_ids if t is not None}

        if candidate_ids:
            ignored_tag_ids, valid_tag_ids = await validate_tags(
                candidate_ids=candidate_ids, db=db, user_id=user_id
            )

    if await check_note_existence(
        db=db, title=note.title, user_id=user_id, folder_id=note.folder_id
    ):
        raise ValueError(f"This title: {note.title} exists from before.")

    payload = note.model_dump(exclude={"tag_ids"})
    payload["user_id"] = user_id
    db_note = models.Note(**payload)
    db.add(db_note)

    tag_objs = []
    if valid_tag_ids:
        tag_rows = await db.execute(select(Tag).where(Tag.id.in_(valid_tag_ids)))
        tag_objs = list(tag_rows.scalars().all())
        db_note.tags = tag_objs
    else:
        db_note.tags = []

    try:
        await db.flush()
        db_note.version = 1

        init_rev = rev_models.NoteRevision(
            note_id=db_note.id,
            user_id=user_id,
            version=1,
            title=db_note.title,
            content_md=db_note.content_md,
            folder_id=db_note.folder_id,
        )
        init_rev.tags = tag_objs
        db.add(init_rev)

        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError(f"A note named '{note.title}' already exists.")

    await db.refresh(db_note)
    return db_note, ignored_tag_ids


async def update_note(
    db: AsyncSession, user_id: int, note_id: int, updated_note: schemas.UpdateNote
):
    """
    Update a note.
    :param db: Async SQLAlchemy session.
    :param user_id: Target user id.
    :param note_id: Target note id.
    :param updated_note: Pydantic payload containing note's fields.
    :return: The updated note instance.
    """
    note = await get_note_by_id_user(db=db, note_id=note_id, user_id=user_id)
    if not note:
        raise ValueError(f"No note with id {note_id} found.")

    data = updated_note.model_dump(exclude_unset=True)

    target_title: str = data.get("title", note.title)
    if target_title is not None:
        target_title = target_title.strip()
    target_folder_id: Optional[int] = data.get("folder_id", note.folder_id)

    if "folder_id" in data and target_folder_id is not None:
        folder_exists = await folder_repo.get_folder_by_id_and_user(
            db=db, user_id=user_id, folder_id=target_folder_id
        )
        if not folder_exists:
            raise ValueError(f"Folder with id {target_folder_id} was not found.")

    if ("title" in data) or ("folder_id" in data):
        conflict_filters = [
            models.Note.user_id == user_id,
            models.Note.deleted_at.is_(None),
            models.Note.id != note_id,  # exclude current note
            models.Note.title == target_title,
        ]
        if target_folder_id is not None:
            conflict_filters.append(models.Note.folder_id == target_folder_id)

        conflict_stmt = select(exists().where(and_(*conflict_filters)))
        conflict = (await db.execute(conflict_stmt)).scalar()

        if conflict:
            scope = (
                f"folder #{target_folder_id}"
                if target_folder_id is not None
                else "your notes"
            )
            raise ValueError(
                f"A note named '{target_title}' already exists in {scope}."
            )

    ignored_tag_ids: list[int] = []
    if "tag_ids" in data:
        incoming = data["tag_ids"] or []
        candidate_ids = {int(t) for t in incoming if t is not None}

        if candidate_ids:
            ignored_tag_ids, valid_ids = await validate_tags(
                candidate_ids=candidate_ids, db=db, user_id=user_id
            )

            tag_rows = await db.execute(select(Tag).where(Tag.id.in_(valid_ids)))
            note.tags = list(tag_rows.scalars().all())
        else:
            note.tags = []

        data.pop("tag_ids", None)

    for key, value in data.items():
        setattr(note, key, value)

    try:
        await db.flush()

        upd = (
            update(models.Note)
            .where(
                models.Note.id == note_id,
                models.Note.user_id == user_id,
                models.Note.deleted_at.is_(None),
            )
            .values(version=models.Note.version + 1, updated_at=func.now())
            .returning(models.Note.version)
        )
        res = await db.execute(upd)
        new_version = res.scalar_one()

        # insert the revision for the *current* note state
        rev = rev_models.NoteRevision(
            note_id=note.id,
            user_id=user_id,
            version=int(new_version),
            title=note.title,
            content_md=note.content_md,
            folder_id=note.folder_id,
        )
        rev.tags = list(note.tags)
        db.add(rev)

        await db.commit()
    except IntegrityError:
        await db.rollback()
        title_for_msg = data.get("title", note.title)
        raise ValueError(f"A note named '{title_for_msg}' already exists.")

    await db.refresh(note)
    return note, ignored_tag_ids


async def validate_tags(
    candidate_ids: set[int], db: AsyncSession, user_id: int
) -> tuple[list[int], set[Row[Any] | RowMapping | Any]]:
    res = await db.execute(
        select(Tag.id).where(
            Tag.user_id == user_id,
            Tag.deleted_at.is_(None),
            Tag.id.in_(candidate_ids),
        )
    )
    valid_ids = set(res.scalars().all())
    ignored_tag_ids = sorted(candidate_ids - valid_ids)
    if not valid_ids:
        raise ValueError(f"No valid tags found for IDs: {sorted(candidate_ids)}")
    return ignored_tag_ids, valid_ids


async def soft_delete_by_id(db: AsyncSession, user_id: int, note_id: int):
    """
    Soft delete a note.
    :param db: Async SQLAlchemy session.
    :param user_id: Target User ID.
    :param note_id: Target note ID
    :return: The updated note instance with 'deleted_at' set.
    """
    note = await get_note_by_id_user(db=db, user_id=user_id, note_id=note_id)
    if note is None:
        raise ValueError("This note doesn't exist")

    note.deleted_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(note)
    return note
