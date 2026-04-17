from typing import List

from fastapi import HTTPException, status

from app.models.grammar import GrammarIssue
from app.models.revision import NoteRevision
from app.repositories.grammar import GrammarRepository
from app.repositories.note import NoteRepository
from app.repositories.revision import RevisionRepository
from app.schemas import grammar as gs
from app.models import revision as rev_models
from app.services.grammar_provider import GrammarProvider


def _to_issue_out(issue: GrammarIssue) -> gs.IssueOut:
    return gs.IssueOut.model_validate(issue, from_attributes=True)


def _apply_slices(text: str, items: List[tuple[int, int, str]]) -> str:
    if not items:
        return text
    out = text
    last_start = len(text) + 1
    for start, length, replacement in sorted(items, key=lambda t: t[0], reverse=True):
        if start + length > last_start:
            continue
        out = out[:start] + replacement + out[start + length :]
        last_start = start
    return out


def _severity_ge(actual: str, minimum: str) -> bool:
    rank = {"info": 0, "warning": 1, "error": 2}
    return rank.get(actual, 0) >= rank.get(minimum, 0)


class GrammarService:
    def __init__(
        self,
        revision_repo: RevisionRepository,
        note_repo: NoteRepository,
        grammar_repo: GrammarRepository,
        provider: GrammarProvider,
        user_id: int,
    ):
        self.revision_repo = revision_repo
        self.note_repo = note_repo
        self.grammar_repo = grammar_repo
        self.provider = provider
        self.user_id = user_id

    async def run_audit(
        self, note_id: int, revision_id: int, req: gs.AuditRequest
    ) -> gs.AuditOut:
        rev = await self.revision_repo.get_revision_by_id_and_user_note(
            revision_id=revision_id, user_id=self.user_id, note_id=note_id
        )
        if not rev:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision not found")

        try:
            issues_in = await self.provider.analyze(rev.content_md, language=req.language)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Grammar provider error: {exc}",
            )

        audit = await self.grammar_repo.create_audit_with_issues(
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

    async def apply_fixes(
        self, note_id: int, revision_id: int, body: gs.ApplyFixesRequest
    ) -> dict:
        rev = await self.revision_repo.get_revision_by_id_and_user_note(
            revision_id=revision_id, user_id=self.user_id, note_id=note_id
        )
        if not rev:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision not found")

        if body.issue_ids:
            issues = await self.grammar_repo.get_issues_by_ids(body.issue_ids)
            issues = [issue for issue in issues if issue.revision_id == rev.id]
        else:
            latest = await self.grammar_repo.get_latest_audit(rev.id)
            if not latest:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No audit found for this revision",
                )
            issues = [
                issue
                for issue in latest.issues
                if _severity_ge(issue.severity, body.min_severity)
            ]

        if not issues:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No matching issues to apply",
            )

        replacements: list[tuple[int, int, str]] = []
        for issue in issues:
            if issue.replacements:
                replacements.append((issue.start, issue.length, issue.replacements[0]))

        new_content = _apply_slices(rev.content_md, replacements)
        if new_content == rev.content_md:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No changes after applying fixes",
            )

        note = await self.note_repo.get_note_with_tags_by_id_user(note_id, self.user_id)
        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Note not found or not accessible",
            )

        note.version = (note.version or 0) + 1
        updated_note = await self.note_repo.update_note(note, {"content_md": new_content})

        restored = rev_models.NoteRevision(
            note_id=note_id,
            user_id=self.user_id,
            version=int(updated_note.version),
            title=updated_note.title,
            content_md=updated_note.content_md,
            is_public=updated_note.is_public,
            folder_id=updated_note.folder_id,
        )
        restored.tags = list(note.tags or [])
        created_revision: NoteRevision = await self.revision_repo.create_revision(restored)

        return {
            "revision_id": revision_id,
            "new_revision_id": created_revision.id,
            "patched_content_md": new_content,
            "applied_issue_ids": [issue.id for issue in issues if issue.replacements],
            "skipped_issue_ids": [issue.id for issue in issues if not issue.replacements],
            "issues": [_to_issue_out(issue) for issue in issues],
        }
