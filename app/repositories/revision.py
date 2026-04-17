from datetime import datetime, timezone
from typing import Mapping

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import revision as rev_models
from ..models import tag as tag_models


def with_revision_tags(stmt):
    return stmt.options(selectinload(rev_models.NoteRevision.tags)).execution_options(
        populate_existing=True
    )


class RevisionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_active_revisions(
        self, user_id: int, skip: int = 0, limit: int = 100
    ):
        stmt = (
            select(rev_models.NoteRevision)
            .where(
                rev_models.NoteRevision.deleted_at.is_(None),
                rev_models.NoteRevision.user_id == user_id,
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(with_revision_tags(stmt))
        return result.scalars().all()

    async def get_all_revisions(self, skip: int = 0, limit: int = 100):
        stmt = select(rev_models.NoteRevision).offset(skip).limit(limit)
        result = await self.db.execute(with_revision_tags(stmt))
        return result.scalars().all()

    async def get_revisions_for_note(
        self, user_id: int, note_id: int, skip: int = 0, limit: int = 100
    ):
        stmt = (
            select(rev_models.NoteRevision)
            .where(
                rev_models.NoteRevision.user_id == user_id,
                rev_models.NoteRevision.note_id == note_id,
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(with_revision_tags(stmt))
        return result.scalars().all()

    async def get_revision_by_id(self, revision_id: int):
        stmt = select(rev_models.NoteRevision).where(
            rev_models.NoteRevision.id == revision_id,
            rev_models.NoteRevision.deleted_at.is_(None),
        )
        result = await self.db.execute(with_revision_tags(stmt))
        return result.scalar_one_or_none()

    async def get_revision_by_id_and_user(self, revision_id: int, user_id: int):
        stmt = select(rev_models.NoteRevision).where(
            rev_models.NoteRevision.id == revision_id,
            rev_models.NoteRevision.deleted_at.is_(None),
            rev_models.NoteRevision.user_id == user_id,
        )
        result = await self.db.execute(with_revision_tags(stmt))
        return result.scalar_one_or_none()

    async def get_revision_by_id_and_user_note(
        self, revision_id: int, user_id: int, note_id: int
    ):
        stmt = select(rev_models.NoteRevision).where(
            rev_models.NoteRevision.id == revision_id,
            rev_models.NoteRevision.deleted_at.is_(None),
            rev_models.NoteRevision.user_id == user_id,
            rev_models.NoteRevision.note_id == note_id,
        )
        result = await self.db.execute(with_revision_tags(stmt))
        return result.scalar_one_or_none()

    async def check_revision_existence(self, user_id: int, note_id: int, version: int):
        stmt = select(
            exists().where(
                rev_models.NoteRevision.user_id == user_id,
                rev_models.NoteRevision.note_id == note_id,
                rev_models.NoteRevision.deleted_at.is_(None),
                rev_models.NoteRevision.version == version,
            )
        )
        return bool(await self.db.scalar(stmt))

    async def get_by_note_and_version(self, note_id: int, version: int, user_id: int):
        stmt = select(rev_models.NoteRevision).where(
            rev_models.NoteRevision.note_id == note_id,
            rev_models.NoteRevision.version == version,
            rev_models.NoteRevision.user_id == user_id,
            rev_models.NoteRevision.deleted_at.is_(None),
        )
        result = await self.db.execute(with_revision_tags(stmt))
        return result.scalar_one_or_none()

    async def create_revision(self, revision: rev_models.NoteRevision):
        self.db.add(revision)
        await self.db.flush()
        await self.db.commit()
        return await self.get_revision_by_id(revision.id)

    async def title_exists_for_note_excluding_revision(
        self, note_id: int, user_id: int, title: str, revision_id: int
    ):
        stmt = select(
            exists().where(
                rev_models.NoteRevision.title == title,
                rev_models.NoteRevision.id != revision_id,
                rev_models.NoteRevision.deleted_at.is_(None),
                rev_models.NoteRevision.user_id == user_id,
                rev_models.NoteRevision.note_id == note_id,
            )
        )
        return bool(await self.db.scalar(stmt))

    async def update_revision(
        self,
        revision: rev_models.NoteRevision,
        data: Mapping[str, object],
    ):
        for key, value in data.items():
            setattr(revision, key, value)
        await self.db.commit()
        return await self.get_revision_by_id(revision.id)

    async def soft_delete(self, revision: rev_models.NoteRevision):
        revision.deleted_at = datetime.now(timezone.utc)
        revision.is_active = False
        await self.db.commit()
        return await self.get_revision_by_id(revision.id)

    async def get_tags_for_revision(self, revision_id: int):
        stmt = (
            select(tag_models.Tag)
            .join(
                rev_models.note_revision_tags,
                tag_models.Tag.id == rev_models.note_revision_tags.c.tag_id,
            )
            .where(rev_models.note_revision_tags.c.revision_id == revision_id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
