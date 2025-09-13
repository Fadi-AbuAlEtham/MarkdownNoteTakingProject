from typing import List
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import revision_repo
from app.repositories import grammar_repo
from app.models.grammar import GrammarIssue
from app.schemas import grammar as gs
from app.services.grammar_provider import GrammarProvider

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

def _apply_slices(text: str, items: List[tuple[int,int,str]]) -> str:
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
            # overlapping with previous change → skip
            continue
        out = out[:start] + repl + out[start+length:]
        last_start = start
    return out

async def apply_fixes(
    db: AsyncSession,
    user_id: int,
    note_id: int,
    revision_id: int,
    body: gs.ApplyFixesRequest,
) -> dict:
    # confirm revision ownership
    rev = await revision_repo.get_revision_by_id_and_user_note(
        db, revision_id=revision_id, user_id=user_id, note_id=note_id
    )
    if not rev:
        raise HTTPException(status_code=404, detail="Revision not found")

    # which issues?
    if body.issue_ids:
        issues = await grammar_repo.get_issues_by_ids(db, body.issue_ids)
        # filter to this revision only
        issues = [i for i in issues if i.revision_id == rev.id]
    else:
        latest = await grammar_repo.get_latest_audit(db, rev.id)
        if not latest:
            raise HTTPException(status_code=404, detail="No audit found for this revision")
        issues = [i for i in latest.issues if _severity_ge(i.severity, body.min_severity)]

    if not issues:
        raise HTTPException(status_code=400, detail="No matching issues to apply")

    # build replacements (first suggestion only)
    repls = []
    for i in issues:
        if not i.replacements:
            continue
        repls.append((i.start, i.length, i.replacements[0]))

    new_content = _apply_slices(rev.content_md, repls)

    if new_content == rev.content_md:
        raise HTTPException(status_code=409, detail="No changes after applying fixes")

    # create a new revision by reusing your existing path: bump note.version and insert revision
    # (same title/is_public/folder_id; only content_md changes)
    from app.schemas.revision import CreateRevision  # reuse your schema
    new_rev_payload = CreateRevision(
        version=rev.version, # ignored on create, your repo recomputes
        title=rev.title,
        content_md=new_content,
        is_public=getattr(rev, "is_public", False),
        folder_id=getattr(rev, "folder_id", None) or 0,  # adjust if your schema requires gt=0
        tag_ids=[],  # optional, if you later persist tags per revision
        note_id=note_id,
    )
    created = await revision_repo.create_revision(
        db, revision=new_rev_payload, note_id=note_id, user_id=user_id
    )

    return {
        "revision_id": created.id,
        "version": created.version,
        "applied_issue_ids": [i.id for i in issues if i.replacements],
    }

def _severity_ge(a: str, b: str) -> bool:
    rank = {"info": 0, "warning": 1, "error": 2}
    return rank.get(a, 0) >= rank.get(b, 0)
