from typing import List
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import select

from app.repositories import (
    revision as revision_repo,
    grammar as grammar_repo,
    note as note_repo,
)
from app.models.grammar import GrammarIssue
from app.schemas import grammar as gs, note as note_schemas
from app.services.grammar_provider import GrammarProvider
from ..models import revision as rev_models


def _to_issue_out(i: GrammarIssue) -> gs.IssueOut:
    return gs.IssueOut.model_validate(i, from_attributes=True)


async def run_audit(
    db: AsyncSession,
    user_id: int,
    note_id: int,
    revision_id: int,
    req: gs.AuditRequest,
    provider: GrammarProvider,
) -> gs.AuditOut:
    rev = await revision_repo.get_revision_by_id_and_user_note(
        db, revision_id=revision_id, user_id=user_id, note_id=note_id
    )
    if not rev:
        raise HTTPException(status_code=404, detail="Revision not found")

    # analyze
    issues_in = await provider.analyze(rev.content_md, language=req.language)

    # persist
    audit = await grammar_repo.create_audit_with_issues(
        db,
        revision_id=rev.id,
        provider=req.provider,
        language=req.language,
        raw_issues=issues_in,
    )

    return gs.AuditOut(
        audit_id=audit.id,
        revision_id=rev.id,
        provider=audit.provider,
        language=audit.language,
        issue_count=audit.issue_count,
        issues=[_to_issue_out(i) for i in audit.issues],
    )


def _apply_slices(text: str, items: List[tuple[int, int, str]]) -> str:
    """
    Apply non-overlapping replacements to `text`.
    items: list of (start, length, replacement).
    Must be sorted by start desc to avoid offset drift.
    Overlaps are skipped (conservatively).
    """
    if not items:
        return text
    out = text
    last_start = len(text) + 1
    for start, length, repl in sorted(items, key=lambda t: t[0], reverse=True):
        if start + length > last_start:
            continue
        out = out[:start] + repl + out[start + length :]
        last_start = start
    return out


async def apply_fixes(
    db: AsyncSession,
    user_id: int,
    note_id: int,
    revision_id: int,
    body: gs.ApplyFixesRequest,
) -> dict:
    rev = await revision_repo.get_revision_by_id_and_user_note(
        db, revision_id=revision_id, user_id=user_id, note_id=note_id
    )
    if not rev:
        raise HTTPException(status_code=404, detail="Revision not found")

    if body.issue_ids:
        issues = await grammar_repo.get_issues_by_ids(db, body.issue_ids)
        issues = [i for i in issues if i.revision_id == rev.id]
    else:
        latest = await grammar_repo.get_latest_audit(db, rev.id)
        if not latest:
            raise HTTPException(
                status_code=404, detail="No audit found for this revision"
            )
        issues = [
            i for i in latest.issues if _severity_ge(i.severity, body.min_severity)
        ]

    if not issues:
        raise HTTPException(status_code=400, detail="No matching issues to apply")

    repls: list[tuple[int, int, str]] = []
    for i in issues:
        if i.replacements:
            repls.append((i.start, i.length, i.replacements[0]))

    new_content = _apply_slices(rev.content_md, repls)
    if new_content == rev.content_md:
        raise HTTPException(status_code=409, detail="No changes after applying fixes")

    upd = note_schemas.UpdateNote(content_md=new_content)
    updated_note, _ignored = await note_repo.update_note(
        db=db, user_id=user_id, note_id=note_id, updated_note=upd
    )

    stmt = (
        select(rev_models.NoteRevision.id)
        .where(
            rev_models.NoteRevision.note_id == note_id,
            rev_models.NoteRevision.version == updated_note.version,
        )
        .limit(1)
    )
    row = await db.execute(stmt)
    created_rev_id = row.scalar_one_or_none()
    if created_rev_id is None:
        raise HTTPException(
            status_code=500, detail="New revision not found after update"
        )

    return {
        "revision_id": created_rev_id,
        "version": updated_note.version,
        "applied_issue_ids": [i.id for i in issues if i.replacements],
        "patched_content_md": new_content,
    }


def _severity_ge(a: str, b: str) -> bool:
    rank = {"info": 0, "warning": 1, "error": 2}
    return rank.get(a, 0) >= rank.get(b, 0)
