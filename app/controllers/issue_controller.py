from typing import Annotated, List

from fastapi import APIRouter, Depends, status
from fastapi.params import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.core.db import get_db
from app.schemas import issue as issue_schema
from app.services import issue_service

router = APIRouter(prefix="/issues", tags=["issues"])


@router.get(
    "/{issue_id}",
    response_model=issue_schema.ResponseIssue,
    status_code=status.HTTP_200_OK,
)
async def get_issue_by_id(
    issue_id: Annotated[int, Path(title="The ID of the issue to get", gt=0)],
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Get a issue by ID.
    :param issue_id: Target issue ID.
    :param db: Async SQLAlchemy session.
    :param current_user_id: The ID of the current user.
    :return: The target issue.
    """
    return await issue_service.get_issue_by_id_and_user(
        db, issue_id=issue_id, user_id=current_user_id
    )


@router.get(
    "/",
    response_model=List[issue_schema.ResponseIssue],
    status_code=status.HTTP_200_OK,
)
async def get_all_active_issues(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Get all active issues.
    :param skip: Starting offset
    :param limit: ending offset
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :return: List of all active issues for the current user
    """
    return await issue_service.get_all_active_issues(db, current_user_id, skip, limit)


@router.post(
    "/",
    response_model=issue_schema.ResponseIssue,
    status_code=status.HTTP_201_CREATED,
)
async def create_issue(
    issue: issue_schema.CreateIssue,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Create a new issue.
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :param issue: Pydantic model that holds the new issue payload
    :return: The newly created issue
    """
    return await issue_service.create_issue(db, user_id=current_user_id, issue_to_create=issue)


@router.put("/{issue_id}", response_model=issue_schema.ResponseIssue)
async def update_issue(
    issue: issue_schema.UpdateIssue,
    issue_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Update a issue.
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :param issue_id: Target issue id
    :param issue: Pydantic model that holds the new issue payload
    :return: The updated issue
    """
    return await issue_service.update_issue(
        db, user_id=current_user_id, issue_id=issue_id, issue_to_update=issue
    )


@router.delete("/{issue_id}", response_model=issue_schema.ResponseIssue)
async def delete_issue(
    issue_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Delete a issue.
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :param issue_id:  of the issue to delete
    :return: The deleted issue
    """
    return await issue_service.soft_delete_issue(db, user_id=current_user_id, issue_id=issue_id)
