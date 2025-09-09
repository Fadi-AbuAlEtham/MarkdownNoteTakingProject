from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, exists, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import issue as models_issue
from ..models import note as models_note
from ..models import revision as models_revision
from ..schemas import issue as schemas


async def ensure_note_owned_by_user(db: AsyncSession, note_id: int, user_id: int):
    """
    Ensure the given note exists, is not soft-deleted, and belongs to the user.
    Raises PermissionError if not accessible.
    :param db: Async SQLAlchemy session.
    :param note_id: Target Note ID.
    :param user_id: Target User ID.
    :return: True if the user owns the note, otherwise False.
    :raises: PermissionError if not accessible.
    """
    stmt = select(
        exists().where(
            and_(
                models_note.Note.id == note_id,
                models_note.Note.user_id == user_id,
                models_note.Note.deleted_at.is_(None),
            )
        )
    )
    if not (await db.execute(stmt)).scalar():
        raise PermissionError("You do not have access to this note.")


async def ensure_revision_belongs_to_note(
    db: AsyncSession, revision_id: int, note_id: int
):
    """
    Ensure the given revision belongs to the given note.
    Raises ValueError if not.
    """
    stmt = select(
        exists().where(
            and_(
                models_revision.NoteRevision.id == revision_id,
                models_revision.NoteRevision.note_id == note_id,
            )
        )
    )
    if not (await db.execute(stmt)).scalar():
        raise ValueError("Revision does not belong to the specified note.")


async def load_issue_owned_by_user(db: AsyncSession, issue_id: int, user_id: int):
    """
    Load an issue only if the parent note is owned by the user and not soft-deleted.
    Raises PermissionError if missing or not accessible.
    :param db: Async SQLAlchemy session.
    :param issue_id: Target Issue ID.
    :param user_id: Target User ID.
    :return: Issue instance or None if it does not exist.
    """
    stmt = (
        select(models_issue.Issue)
        .join(models_note.Note, models_issue.Issue.note_id == models_note.Note.id)
        .where(models_issue.Issue.id == issue_id)
        .where(models_note.Note.user_id == user_id)
        .where(models_note.Note.deleted_at.is_(None))
    )
    res = await db.execute(stmt)
    issue = res.scalar_one_or_none()
    if issue is None:
        raise PermissionError(
            "You do not have access to this issue or it does not exist."
        )
    return issue


async def get_issue_by_id_user(db: AsyncSession, issue_id: int, user_id: int):
    """
    Return an issue if the user owns its parent note; otherwise None.
    """
    try:
        issue = await load_issue_owned_by_user(db, issue_id=issue_id, user_id=user_id)
    except PermissionError:
        return None
    return issue


async def list_issues_by_note(
    db: AsyncSession,
    user_id: int,
    note_id: int,
    revision_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
):
    """
    List issues for a user's note, optionally constrained to a specific revision.
    :param db: Async SQLAlchemy session.
    :param user_id: Target User ID.
    :param note_id: Target Note ID.
    :param revision_id: Target Revision ID.
    :param skip: Number of issues to skip.
    :param limit: Number of issues to return.
    :return: List of issues.
    """
    await ensure_note_owned_by_user(db, note_id=note_id, user_id=user_id)

    stmt = (
        select(models_issue.Issue)
        .where(models_issue.Issue.note_id == note_id)
        .offset(skip)
        .limit(limit)
    )
    if revision_id is not None:
        await ensure_revision_belongs_to_note(
            db, revision_id=revision_id, note_id=note_id
        )
        stmt = stmt.where(models_issue.Issue.revision_id == revision_id)

    res = await db.execute(stmt)
    return res.scalars().all()


async def get_all_active_issues_user(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
):
    """
    List all issues for notes owned by the given user.
    :param db: Async SQLAlchemy session.
    :param user_id: Target User ID.
    :param skip: Number of issues to skip.
    :param limit: Number of issues to return.
    :return: List of issues.
    """
    stmt = (
        select(models_issue.Issue)
        .join(models_note.Note, models_issue.Issue.note_id == models_note.Note.id)
        .where(models_note.Note.user_id == user_id)
        .where(models_note.Note.deleted_at.is_(None))
        .offset(skip)
        .limit(limit)
    )
    res = await db.execute(stmt)
    return res.scalars().all()


async def create_issue(
    db: AsyncSession, user_id: int, issue_to_create: schemas.CreateIssue
):
    """
    Create a new issue, ensuring the user owns the parent note, and (if provided)
    the revision belongs to that note.
    :param db: Async SQLAlchemy session.
    :param user_id: Target User ID.
    :param issue_to_create: Pydantic model that holds the issue data.
    :return: The created issue.
    """
    await ensure_note_owned_by_user(
        db, note_id=issue_to_create.note_id, user_id=user_id
    )

    if issue_to_create.revision_id is not None:
        await ensure_revision_belongs_to_note(
            db, revision_id=issue_to_create.revision_id, note_id=issue_to_create.note_id
        )

    issue = models_issue.Issue(**issue_to_create.model_dump())
    db.add(issue)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # If you add a UNIQUE constraint to prevent exact duplicates,
        # translate here to a friendly error:
        raise ValueError("Duplicate issue detected.")
    await db.refresh(issue)
    return issue


async def update_issue(
    db: AsyncSession, user_id: int, issue_id: int, issue_to_update: schemas.UpdateIssue
):
    """
    Update an existing issue. If moving it to a different note or revision,
    re-validate ownership and revision consistency.
    :param db: Async SQLAlchemy session.
    :param user_id: Target User ID.
    :param issue_id: Target Issue ID.
    :param issue_to_update: Pydantic model that holds the issue data.
    :return: The updated issue.
    """
    issue = await load_issue_owned_by_user(db, issue_id=issue_id, user_id=user_id)

    data = issue_to_update.model_dump(exclude_unset=True)

    target_note_id = data.get("note_id", issue.note_id)
    target_revision_id: Optional[int] = data.get("revision_id", issue.revision_id)

    if target_note_id != issue.note_id:
        await ensure_note_owned_by_user(db, note_id=target_note_id, user_id=user_id)

    if target_revision_id is not None:
        await ensure_revision_belongs_to_note(
            db, revision_id=target_revision_id, note_id=target_note_id
        )

    for k, v in data.items():
        setattr(issue, k, v)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError("Failed to update issue due to a constraint violation.")
    await db.refresh(issue)
    return issue


async def soft_delete_issue(db: AsyncSession, user_id: int, issue_id: int):
    """
    Soft-delete an existing issue.
    :param db: Async SQLAlchemy session.
    :param user_id: Target User ID.
    :param issue_id: Target Issue ID.
    :return: The issue soft-deleted.
    """
    issue = await load_issue_owned_by_user(db, issue_id=issue_id, user_id=user_id)
    issue.deleted_at = datetime.now(timezone.utc)
    issue.is_active = False
    await db.commit()
    await db.refresh(issue)
    return issue
