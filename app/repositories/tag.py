from datetime import datetime, timezone
from typing import Mapping, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists

from ..models import tag as models


class TagRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_active_tags(self, user_id: int, skip: int, limit: int):
        """
            Fetch all active tags (not soft-deleted) with pagination
        :param user_id: Target user_id
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
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_all_tags(self, skip: int, limit: int):
        """
            Fetch all tags with pagination
        :param skip: Number of rows to skip (offset).
        :param limit: Maximum number of rows to return.
        :return: A list of tag objects.
        """

        stmt = select(models.Tag).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_tag_by_id(self, tag_id: int):
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
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_tag_by_id_and_user(self, user_id: int, tag_id: int):
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
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def check_tag_existence_by_title(self, user_id: int, title: str):
        """
            Check if an active tag exists with the given title (case-insensitive --> CITEXT).
        :param db: Async SQLAlchemy session.
        :param user_id: Target user ID.
        :param title: Target tag title
        :return: True if another active tag exists with this title; otherwise False.
        """
        stmt = select(
            exists()
            .where(models.Tag.title == title)
            .where(models.Tag.deleted_at.is_(None))
            .where(models.Tag.user_id == user_id)
        )
        return await self.db.scalar(stmt)

    async def create_tag(self, tag: models.Tag):
        """
        Create new tag with distinct title for a certain user.
        :param tag: Pydantic payload containing tag fields.
        :return: The updated tag instance.
        """

        self.db.add(tag)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(tag)
        return tag

    async def update_tag(self, tag: models.Tag, data: Mapping[str, Any]):
        """
        Update Certain tag data based on its tag_id.
        :param tag: Pydantic payload containing tag's fields.
        :param data: Updated tag data.
        :return: The updated tag instance or None if the tag doesn't exist or soft-deleted
        """

        for k, v in data.items():
            setattr(tag, k, v)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(tag)
        return tag

    async def soft_delete_by_id(self, tag: models.Tag):
        """
            Soft delete a tag.
        :param tag: tag model to be soft-deleted
        :return: The updated tag instance with "deleted_at" and "is_active" attributes.
        """

        tag.deleted_at = datetime.now(timezone.utc)
        tag.is_active = False
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(tag)
        return tag

    async def active_title_exists_excluding_tag(
        self, title: str, *, tag_id: int, user_id: int
    ):
        """
        Return True if an ACTIVE title (deleted_at IS NULL) exists with this user_id.
        Optionally exclude a specific user id.
        """
        stmt = select(
            exists()
            .where(models.Tag.title == title)
            .where(models.Tag.deleted_at.is_(None))
            .where(models.Tag.user_id == user_id)
        )
        stmt = stmt.where(models.Tag.id != tag_id)
        return bool(await self.db.scalar(stmt))

    async def validate_tags(self, candidate_ids: set[int], user_id: int):
        res = await self.db.execute(
            select(models.Tag.id).where(
                models.Tag.user_id == user_id,
                models.Tag.deleted_at.is_(None),
                models.Tag.id.in_(candidate_ids),
            )
        )
        valid_ids = set(res.scalars().all())
        return valid_ids

    async def get_tags_by_ids(self, tag_ids: set[int]):
        """
        Fetch tags by a list of IDs.
        Optionally scope to a user and/or only active (not soft-deleted) tags.
        :param tag_ids: Target tag IDs
        :return: A list of tag instances.
        """
        stmt = select(models.Tag).where(models.Tag.id.in_(list(tag_ids)))
        res = await self.db.execute(stmt)
        rows = res.scalars().all()
        return rows
