from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists, func, update
from sqlalchemy.orm import aliased

from ..models import tag as models
from ..schemas import tag as schemas


async def get_all_active_tags(db: AsyncSession, user_id: int, skip: int, limit: int):
    """
        Fetch all active tags (not soft-deleted) with pagination
    :param user_id: Target user_id
    :param db: Async SQLAlchemy session
    :param skip: Number of rows to skip (offset).
    :param limit: Maximum number of rows to return.
    :return: A list of tag objects that are not soft-deleted.
    """

    stmt = (
        select(models.Tag)
        .where(models.Tag.deleted_at.is_(None))
        .where(models.Tag.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_all_tags(db: AsyncSession, skip: int, limit: int):
    """
        Fetch all tags with pagination
    :param db: Async SQLAlchemy session
    :param skip: Number of rows to skip (offset).
    :param limit: Maximum number of rows to return.
    :return: A list of tag objects.
    """

    stmt = select(models.Tag).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_tag_by_id(db: AsyncSession, tag_id: int):
    """
        Fetch a certain tag by its id (not soft-deleted)
    :param db: Async SQLAlchemy session
    :param tag_id: Target tag ID
    :return: The matching tag instance, or None if not found or soft-deleted.
    """
    stmt = (
        select(models.Tag)
        .where(models.Tag.id == tag_id)
        .where(models.Tag.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_tag_by_id_and_user(db: AsyncSession, user_id: int, tag_id: int):
    """
        Fetch a certain tag by its id (not soft-deleted)
    :param db: Async SQLAlchemy session
    :param user_id: Target user ID
    :param tag_id: Target tag ID
    :return: The matching tag instance, or None if not found or soft-deleted.
    """
    stmt = (
        select(models.Tag)
        .where(models.Tag.id == tag_id)
        .where(models.Tag.deleted_at.is_(None))
        .where(models.Tag.user_id == user_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def check_tag_existence_by_title(db: AsyncSession, user_id: int, title: str):
    """
        Check if an active tag exists with the given title (case-insensitive --> CITEXT).
    :param db: Async SQLAlchemy session.
    :param user_id: Target user ID.
    :param title: Target tag title
    :return: True if another active tag exists with this title; otherwise False.
    """
    stmt = select(
        exists()
        .where(models.Tag.title == title.strip())
        .where(models.Tag.deleted_at.is_(None))
        .where(models.Tag.user_id == user_id)
    )
    return await db.scalar(stmt)


async def create_tag(db: AsyncSession, user_id: int, tag: schemas.CreateTag):
    """
         Create new tag with distinct title for a certain user.
    :param db: Async SQLAlchemy session
    :param user_id: Target User ID.
    :param tag: Pydantic payload containing tag fields.
    :return: The updated tag instance.
    """

    if await check_tag_existence_by_title(db, user_id, tag.title):
        raise ValueError(f"This title: {tag.title} exists from before.")

    payload = tag.model_dump()
    payload["user_id"] = user_id

    db_tag = models.Tag(**payload)
    db.add(db_tag)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # Catches races that slipped past the pre-check
        raise ValueError(f"A tag named '{tag.title}' already exists.")
    await db.refresh(db_tag)
    return db_tag


async def update_tag(
    db: AsyncSession, user_id: int, tag_id: int, updated_tag: schemas.UpdateTag
):
    """
        Update Certain tag data based on its tag_id.
    :param db: Async SQLAlchemy session.
    :param user_id: Target user ID.
    :param tag_id: Target tag ID.
    :param updated_tag: Pydantic payload containing tag's fields.
    :return: The updated tag instance or None if the tag doesn't exist or soft-deleted
    :raises:
        ValueError: If the new title conflicts with another active title
            or if the commit hits a uniqueness violation, or if the tag doesn't exist.
    """
    tag = await get_tag_by_id_and_user(db, user_id, tag_id)
    if not tag:
        raise ValueError(f"This tag which holds ID# {tag_id} doesn't exist!")

    data = updated_tag.model_dump(exclude_unset=True)

    if "title" in data:
        stmt = select(
            exists()
            .where(models.Tag.title == updated_tag.title)
            # Exclude the current tag while updating to check other tags
            .where(models.Tag.id != tag_id)
            .where(models.Tag.deleted_at.is_(None))
            .where(models.Tag.user_id == user_id)
        )
        if await db.scalar(stmt):
            raise ValueError(f"This title: {updated_tag.title} is already in use")

    for key, value in data.items():
        setattr(tag, key, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        title_for_msg = data.get("title", tag.title)
        # DB-level partial UNIQUE index is the final arbiter; translate race to a friendly message
        raise ValueError(f"A tag named '{title_for_msg}' already exists")

    await db.refresh(tag)
    return tag


async def soft_delete_by_id(db: AsyncSession, user_id: int, tag_id: int):
    """
        Soft delete a tag.
    :param db: Async SQLAlchemy session.
    :param user_id: Target User ID.
    :param tag_id: Target tag ID
    :return: The updated tag instance with "deleted_at" and "is_active" attributes.
    """

    tag = await get_tag_by_id_and_user(db, user_id, tag_id)
    if tag is None:
        raise ValueError("This tag doesn't exist")

    tag.deleted_at = datetime.now(timezone.utc)
    tag.is_active = False
    await db.commit()
    await db.refresh(tag)
    return tag
