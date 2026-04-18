from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists, and_
from sqlalchemy.orm import selectinload

from ..models import note as models


class NoteRepository:
    """Note repository"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_active_notes(self, user_id: int, skip: int = 0, limit: int = 100):
        """
        Get all active (non-deleted) notes.
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
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_all_notes(self, skip: int = 0, limit: int = 100):
        """
        Get all notes (deleted and non-deleted).
        :param skip: Number of rows to skip.
        :param limit: Number of rows to limit.
        :return: List of notes.
        """
        stmt = select(models.Note).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_active_notes_in_folder(self, user_id: int, folder_id: int):
        """
        Get all active (non-deleted) notes for a certain folder.
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
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def get_note_by_id_user(self, note_id: int, user_id: int):
        """
        Get a note by id for a certain user.
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
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_note_with_tags_by_id_user(self, note_id: int, user_id: int):
        stmt = (
            select(models.Note)
            .where(
                models.Note.deleted_at.is_(None),
                models.Note.id == note_id,
                models.Note.user_id == user_id,
            )
            .options(selectinload(models.Note.tags))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def check_root_note_existence(self, title: str, user_id: int):
        stmt = select(
            exists().where(
                and_(
                    models.Note.title == title,
                    models.Note.user_id == user_id,
                    models.Note.deleted_at.is_(None),
                    models.Note.folder_id.is_(None),
                )
            )
        )
        result = await self.db.execute(stmt)
        return bool(result.scalar())

    async def check_note_existence_in_folder(
        self, title: str, user_id: int, folder_id: int
    ):
        stmt = select(
            exists().where(
                and_(
                    models.Note.title == title,
                    models.Note.user_id == user_id,
                    models.Note.deleted_at.is_(None),
                    models.Note.folder_id == folder_id,
                )
            )
        )
        result = await self.db.execute(stmt)
        return bool(result.scalar())

    async def create_note(self, db_note: models.Note):
        """
        Create a new note.
        :param db_note: note ORM model.
        :return: The created note instance.
        """
        self.db.add(db_note)
        await self.db.flush()
        await self.db.refresh(db_note)
        return db_note

    async def update_note(self, note: models.Note, data: Mapping[str, Any]):
        """
        Update a note.
        :param note: note ORM model.
        :param data: Updated note data.
        :return: The updated note instance.
        """
        for k, v in data.items():
            setattr(note, k, v)
        await self.db.flush()
        await self.db.refresh(note)
        return note

    async def soft_delete_by_id(self, note: models.Note):
        """
        Soft-delete note by id
        :param note: note to soft-delete
        :return: The soft-deleted note instance.
        """

        note.deleted_at = datetime.now(timezone.utc)
        note.is_active = False
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def delete_note(self, note: models.Note):
        """
        Delete note by id
        :param note: note to soft-delete
        :return: Deleted note-object.
        """
        await self.db.delete(note)
        await self.db.flush()
        await self.db.commit()
        return note
