from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists, update
from sqlalchemy.orm import aliased, selectinload

from ..models import folder as models

"""
Async folder repository.

- Active-only reads by default (`deleted_at IS NULL`).
- Title uniqueness per user + parent (sibling level); DB should enforce via partial UNIQUE index.
- Create/Update validate parent ownership/access; Update checks conflicts in target level.
- Soft delete cascades to active descendants using a recursive CTE (sets `deleted_at`, 
  `is_active=False`).
- Pre-checks for conflicts; DB remains final arbiter (catch `IntegrityError` on commit).
- Prefer CITEXT for case-insensitive title equality without LOWER().
"""


def folder_graph_options():
    return (
        selectinload(models.Folder.parent).load_only(
            models.Folder.id, models.Folder.title
        ),
        selectinload(models.Folder.children).load_only(
            models.Folder.id, models.Folder.title
        ),
    )


def with_folder_graph(stmt):
    return stmt.options(*folder_graph_options())


class FolderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def load_folder_graph(self, folder_id: int):
        stmt = select(models.Folder).where(models.Folder.id == folder_id)
        result = await self.db.execute(with_folder_graph(stmt))
        return result.scalar_one_or_none()

    async def get_folder_by_id(self, folder_id: int):
        """
            Fetch certain folder from its id (only active folders; not soft-deleted)
        :param
            folder_id: Database primary key.
        :return:
            The matching "Folder" instance, or "None" if not found or soft-deleted.
        """
        stmt = (
            select(models.Folder)
            .where(models.Folder.id == folder_id)
            .where(models.Folder.deleted_at.is_(None))
        )
        result = await self.db.execute(with_folder_graph(stmt))
        return result.scalar_one_or_none()

    async def get_folder_by_id_and_user(self, user_id: int, folder_id: int):
        """
            Fetch certain folder from its id for a certain user (only active folders; not soft-deleted)
        :param
            folder_id: Database primary key.
        :return:
            The matching "Folder" instance, or "None" if not found or soft-deleted.
        """
        stmt = (
            select(models.Folder)
            .where(models.Folder.id == folder_id)
            .where(models.Folder.deleted_at.is_(None))
            .where(models.Folder.user_id == user_id)
        )
        result = await self.db.execute(with_folder_graph(stmt))
        return result.scalar_one_or_none()

    async def get_all_active_folders(self, user_id: int, skip: int, limit: int):
        """
            Fetch all active folders.
        :param
            skip: Number of rows to skip (offset).
            limit: Maximum number of rows to return.
        :return:
            All active Folders, or None if not found or soft-deleted.
        """

        stmt = (
            select(models.Folder)
            .where(models.Folder.deleted_at.is_(None))
            .where(models.Folder.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(with_folder_graph(stmt))
        return result.scalars().all()

    async def folder_exists_by_title(self, user_id: int, title: str):
        """
            Check folder existence by title for a certain user by its id

        :param
            user_id: Target user's ID.
            title: Target folder's title

        :return:
            True if another title exists for the same user; otherwise False.

        """
        stmt = select(
            exists().where(
                models.Folder.user_id == user_id,
                models.Folder.deleted_at.is_(None),
                models.Folder.title == title,
            )
        )
        return await self.db.scalar(stmt)

    async def folder_exists_by_title_at_root(self, user_id: int, title: str) -> bool:
        stmt = select(
            exists().where(
                models.Folder.user_id == user_id,
                models.Folder.deleted_at.is_(None),
                models.Folder.title == title,
                models.Folder.parent_id.is_(None),
            )
        )
        return await self.db.scalar(stmt)

    async def folder_exists_by_title_in_parent(
        self, user_id: int, parent_id: int, title: str
    ) -> bool:
        stmt = select(
            exists().where(
                models.Folder.user_id == user_id,
                models.Folder.deleted_at.is_(None),
                models.Folder.title == title,
                models.Folder.parent_id == parent_id,
            )
        )
        return await self.db.scalar(stmt)

    async def get_folder_by_id_including_deleted(self, folder_id: int):
        """Fetch a folder by ID, including soft-deleted rows.

        Args:
            folder_id: Database primary key.

        Returns:
            The matching "Folder" instance or "None" if not found.
        """
        result = await self.db.execute(
            select(models.Folder).where(models.Folder.id == folder_id)
        )
        return result.scalar_one_or_none()

    async def get_folder_by_id_any_status(self, *, folder_id: int):
        return await self.load_folder_graph(folder_id)

    async def create_folder(self, db_folder: models.Folder):
        """
            Create new folder with distinct title for a certain user.
        :param
            user_id: Target user ID.
            folder:  Pydantic payload containing folder's fields.

        :return:
            The newly created folder instance.
        """
        self.db.add(db_folder)
        await self.db.flush()
        await self.db.commit()
        folder = await self.load_folder_graph(db_folder.id)
        return folder

    async def update_folder(self, folder: models.Folder, data: Mapping[str, Any]):
        """
            Update Folder attributes.

        :param data: folder updated data
        :param folder: folder instance.
        :return: The updated folder instance or None if the folder doesn't exist or soft-deleted
        """
        for key, value in data.items():
            setattr(folder, key, value)
        await self.db.flush()
        await self.db.commit()
        result = await self.load_folder_graph(folder.id)
        return result

    async def soft_delete_subtree(self, *, user_id: int, root_folder_id: int) -> int:
        """
        Soft delete the folder subtree rooted at root_folder_id for user_id.
        :param user_id: Target user ID.
        :param root_folder_id: Target root folder ID.
        :return: number of rows updated.
        """
        fd = models.Folder
        now = datetime.now(timezone.utc)

        tree = (
            select(fd.id, fd.parent_id)
            .where(
                fd.id == root_folder_id, fd.user_id == user_id, fd.deleted_at.is_(None)
            )
            .cte("tree", recursive=True)
        )
        ct = aliased(fd)
        tree = tree.union_all(
            select(ct.id, ct.parent_id).where(
                ct.parent_id == tree.c.id,
                ct.user_id == user_id,
                ct.deleted_at.is_(None),
            )
        )

        res = await self.db.execute(
            update(fd)
            .where(fd.id.in_(select(tree.c.id)))
            .values(deleted_at=now, is_active=False)
        )
        await self.db.commit()
        return int(res.rowcount or 0)
