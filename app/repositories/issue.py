from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import issue as models_issue
from ..models import note as models_note


class IssueRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_issue_by_id_user(self, issue_id: int, user_id: int):
        stmt = (
            select(models_issue.Issue)
            .join(models_note.Note, models_issue.Issue.note_id == models_note.Note.id)
            .where(
                models_issue.Issue.id == issue_id,
                models_note.Note.user_id == user_id,
                models_note.Note.deleted_at.is_(None),
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_issues_by_note(self, note_id: int, skip: int = 0, limit: int = 100):
        stmt = (
            select(models_issue.Issue)
            .where(models_issue.Issue.note_id == note_id)
            .offset(skip)
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def list_issues_by_note_and_revision(
        self, note_id: int, revision_id: int, skip: int = 0, limit: int = 100
    ):
        stmt = (
            select(models_issue.Issue)
            .where(
                models_issue.Issue.note_id == note_id,
                models_issue.Issue.revision_id == revision_id,
            )
            .offset(skip)
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def get_all_active_issues_user(
        self, user_id: int, skip: int = 0, limit: int = 100
    ):
        stmt = (
            select(models_issue.Issue)
            .join(models_note.Note, models_issue.Issue.note_id == models_note.Note.id)
            .where(
                models_note.Note.user_id == user_id,
                models_note.Note.deleted_at.is_(None),
            )
            .offset(skip)
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def create_issue(self, data: Mapping[str, Any]):
        issue = models_issue.Issue(**dict(data))
        self.db.add(issue)
        await self.db.commit()
        await self.db.refresh(issue)
        return issue

    async def update_issue(self, issue: models_issue.Issue, data: Mapping[str, Any]):
        for key, value in data.items():
            setattr(issue, key, value)
        await self.db.commit()
        await self.db.refresh(issue)
        return issue

    async def soft_delete_issue(self, issue: models_issue.Issue):
        issue.deleted_at = datetime.now(timezone.utc)
        issue.is_active = False
        await self.db.commit()
        await self.db.refresh(issue)
        return issue
