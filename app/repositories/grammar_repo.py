from __future__ import annotations

from typing import List, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.grammar import GrammarAudit, GrammarIssue

async def create_audit_with_issues(
    db: AsyncSession,
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
    db.add(audit)
    await db.flush()  # get audit.id

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
    db.add_all(issues)
    await db.commit()
    await db.refresh(audit)
    return audit

async def get_latest_audit(db: AsyncSession, revision_id: int) -> GrammarAudit | None:
    stmt = (
        select(GrammarAudit)
        .where(GrammarAudit.revision_id == revision_id)
        .order_by(GrammarAudit.id.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()

async def get_issues_by_ids(db: AsyncSession, issue_ids: List[int]) -> List[GrammarIssue]:
    if not issue_ids:
        return []
    stmt = select(GrammarIssue).where(GrammarIssue.id.in_(issue_ids))
    return list((await db.execute(stmt)).scalars().all())