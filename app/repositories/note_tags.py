from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import note as models
from app.models.note_tag import note_tags


class NoteTagRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_notes_by_tag(self, user_id: int, tag_id: int):
        """
        Return the user's active notes that are associated with a given tag.
        :param user_id: target User ID
        :param tag_id: target Tag ID
        :return: List of active notes associated with the given tag
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
        res = await self.db.execute(stmt)
        return res.scalars().all()
