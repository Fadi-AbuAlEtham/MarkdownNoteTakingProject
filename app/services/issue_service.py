from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas import issue as schemas_issue
from ..repositories import issue_repo


def to_response_dict(obj) -> dict:
    """
    Convert response to dict.
    :param obj: Response to convert.
    :return: Response dict.
    """
    return schemas_issue.ResponseIssue.model_validate(
        obj, from_attributes=True
    ).model_dump()


async def get_issue_by_id_and_user(db: AsyncSession, issue_id: int, user_id: int):
    """
    Get issue by id and user
    :param db: Async SQLAlchemy session
    :param issue_id: Target issue id
    :param user_id: Target user id
    :return: Issue object
    """
    issue = await issue_repo.get_issue_by_id_user(db, issue_id, user_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found"
        )
    return to_response_dict(issue)


async def get_all_active_issues(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
):
    """
    Get all active issues
    :param db: Async SQLAlchemy session
    :param user_id: Target user id
    :param skip: Number of issues to skip
    :param limit: Number of issues to return
    :return: List of Issue objects
    """
    issues = await issue_repo.get_all_active_issues_user(
        db, user_id=user_id, skip=skip, limit=limit
    )
    return [to_response_dict(i) for i in issues]


async def get_issues_by_note(
    db: AsyncSession,
    user_id: int,
    note_id: int,
    revision_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
):
    """
    Get issues by note
    :param db: Async SQLAlchemy session
    :param user_id: Target user id
    :param note_id: Target note id
    :param revision_id: Target revision id
    :param skip: Number of issues to skip
    :param limit: Number of issues to return
    :return: List of Issue objects
    """
    issues = await issue_repo.list_issues_by_note(
        db,
        user_id=user_id,
        note_id=note_id,
        revision_id=revision_id,
        skip=skip,
        limit=limit,
    )
    return [to_response_dict(i) for i in issues]


async def create_issue(
    db: AsyncSession, user_id: int, issue_to_create: schemas_issue.CreateIssue
):
    """
    Create new issue
    :param db: Async SQLAlchemy session
    :param user_id: Target user id
    :param issue_to_create: Issue to create
    :return: Issue_object
    """
    try:
        issue = await issue_repo.create_issue(
            db, user_id=user_id, issue_to_create=issue_to_create
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return to_response_dict(issue)


async def update_issue(
    db: AsyncSession,
    user_id: int,
    issue_id: int,
    issue_to_update: schemas_issue.UpdateIssue,
):
    """
    Update existing issue
    :param db: Async SQLAlchemy session
    :param user_id: Target user id
    :param issue_id: Target issue id
    :param issue_to_update: Pydantic model that holds issue payload
    :return: Updated Issue object
    """
    try:
        issue = await issue_repo.update_issue(
            db, user_id=user_id, issue_id=issue_id, issue_to_update=issue_to_update
        )
    except ValueError as e:
        msg = str(e).lower()
        if "exist" in msg or "duplicate" in msg or "already" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found"
        )
    return to_response_dict(issue)


async def soft_delete_issue(db: AsyncSession, user_id: int, issue_id: int):
    """
    Delete existing issue
    :param db: Async SQLAlchemy session
    :param user_id: Target user id
    :param issue_id: Target issue id
    :return: Deleted Issue object
    """
    try:
        issue = await issue_repo.soft_delete_issue(
            db, user_id=user_id, issue_id=issue_id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return to_response_dict(issue)
