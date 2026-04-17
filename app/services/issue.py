from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from ..repositories.issue import IssueRepository
from ..repositories.note import NoteRepository
from ..repositories.revision import RevisionRepository
from ..schemas import issue as schemas_issue


class IssueService:
    def __init__(
        self,
        issue_repo: IssueRepository,
        note_repo: NoteRepository,
        revision_repo: RevisionRepository,
        user_id: int,
    ):
        self.issue_repo = issue_repo
        self.note_repo = note_repo
        self.revision_repo = revision_repo
        self.user_id = user_id

    async def get_issue_by_id_and_user(self, issue_id: int):
        issue = await self.issue_repo.get_issue_by_id_user(issue_id, self.user_id)
        if not issue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found"
            )
        return issue

    async def get_all_active_issues(self, skip: int = 0, limit: int = 100):
        issues = await self.issue_repo.get_all_active_issues_user(
            user_id=self.user_id, skip=skip, limit=limit
        )
        return issues

    async def get_issues_by_note(
        self,
        note_id: int,
        revision_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ):
        note = await self.note_repo.get_note_by_id_user(note_id=note_id, user_id=self.user_id)
        if not note:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

        if revision_id is None:
            issues = await self.issue_repo.list_issues_by_note(
                note_id=note_id, skip=skip, limit=limit
            )
            return issues

        revision = await self.revision_repo.get_revision_by_id_and_user_note(
            revision_id=revision_id,
            user_id=self.user_id,
            note_id=note_id,
        )
        if not revision:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Revision not found for this note",
            )
        issues = await self.issue_repo.list_issues_by_note_and_revision(
            note_id=note_id, revision_id=revision_id, skip=skip, limit=limit
        )
        return issues

    async def create_issue(self, issue_to_create: schemas_issue.CreateIssue):
        note = await self.note_repo.get_note_by_id_user(
            note_id=issue_to_create.note_id, user_id=self.user_id
        )
        if not note:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

        revision = await self.revision_repo.get_revision_by_id_and_user_note(
            revision_id=issue_to_create.revision_id,
            user_id=self.user_id,
            note_id=issue_to_create.note_id,
        )
        if not revision:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Revision not found for this note",
            )

        try:
            issue = await self.issue_repo.create_issue(data=issue_to_create.model_dump())
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Duplicate issue detected."
            )
        return issue

    async def update_issue(self, issue_id: int, issue_to_update: schemas_issue.UpdateIssue):
        issue = await self.issue_repo.get_issue_by_id_user(issue_id, self.user_id)
        if not issue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found"
            )

        data = issue_to_update.model_dump(exclude_unset=True)
        target_note_id = data.get("note_id", issue.note_id)
        target_revision_id = data.get("revision_id", issue.revision_id)

        note = await self.note_repo.get_note_by_id_user(
            note_id=target_note_id, user_id=self.user_id
        )
        if not note:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

        if target_revision_id is not None:
            revision = await self.revision_repo.get_revision_by_id_and_user_note(
                revision_id=target_revision_id,
                user_id=self.user_id,
                note_id=target_note_id,
            )
            if not revision:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Revision not found for this note",
                )

        try:
            issue = await self.issue_repo.update_issue(issue=issue, data=data)
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Failed to update issue due to a constraint violation.",
            )
        return issue

    async def soft_delete_issue(self, issue_id: int):
        issue = await self.issue_repo.get_issue_by_id_user(issue_id, self.user_id)
        if not issue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found"
            )
        issue = await self.issue_repo.soft_delete_issue(issue=issue)
        return issue
