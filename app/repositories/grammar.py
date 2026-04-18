from __future__ import annotations

from typing import List, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.grammar import GrammarAudit, GrammarIssue


class GrammarRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_audit_with_issues(
        self,
        revision_id: int,
        provider: str,
        language: str,
        raw_issues: Sequence[dict],
    ) -> GrammarAudit:
        audit = GrammarAudit(
            revision_id=revision_id,
            provider=provider,
            language=language,
            issue_count=len(raw_issues),
        )
        self.db.add(audit)
        await self.db.flush()

        issues = [
            GrammarIssue(
                audit_id=audit.id,
                revision_id=revision_id,
                start=i["start"],
                length=i["length"],
                message=i["message"],
                rule_id=i.get("rule_id"),
                category=i.get("category"),
                severity=i.get("severity", "info"),
                original=i["original"],
                replacements=i.get("replacements", []),
            )
            for i in raw_issues
        ]
        self.db.add_all(issues)
        await self.db.commit()
        await self.db.refresh(audit)
        return audit

    async def get_latest_audit(self, revision_id: int) -> GrammarAudit | None:
        stmt = (
            select(GrammarAudit)
            .where(GrammarAudit.revision_id == revision_id)
            .order_by(GrammarAudit.id.desc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_issues_by_ids(self, issue_ids: List[int]) -> List[GrammarIssue]:
        stmt = select(GrammarIssue).where(GrammarIssue.id.in_(issue_ids))
        return list((await self.db.execute(stmt)).scalars().all())
