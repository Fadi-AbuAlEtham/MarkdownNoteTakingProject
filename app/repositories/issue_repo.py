from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, exists, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import issue as models_issue
from ..models import note as models_note
from ..models import revision as models_revision
from ..schemas import issue as schemas


async def _ensure_note_owned_by_user(db: AsyncSession, note_id: int, user_id: int):
    """
    Ensure the given note exists, is not soft-deleted, and belongs to the user.
    Raises PermissionError if not accessible.
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


async def _ensure_revision_belongs_to_note(
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


async def _load_issue_owned_by_user(db: AsyncSession, issue_id: int, user_id: int):
    """
    Load an issue only if the parent note is owned by the user and not soft-deleted.
    Raises PermissionError if missing or not accessible.
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
        issue = await _load_issue_owned_by_user(db, issue_id=issue_id, user_id=user_id)
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
    """
    await _ensure_note_owned_by_user(db, note_id=note_id, user_id=user_id)

    stmt = (
        select(models_issue.Issue)
        .where(models_issue.Issue.note_id == note_id)
        .offset(skip)
        .limit(limit)
    )
    if revision_id is not None:
        await _ensure_revision_belongs_to_note(
            db, revision_id=revision_id, note_id=note_id
        )
        stmt = stmt.where(models_issue.Issue.revision_id == revision_id)

    res = await db.execute(stmt)
    return res.scalars().all()


async def list_issues_user(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
):
    """
    List all issues for notes owned by the given user.
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


async def create_issue(db: AsyncSession, user_id: int, payload: schemas.CreateIssue):
    """
    Create a new issue, ensuring the user owns the parent note and (if provided)
    the revision belongs to that note.
    """
    await _ensure_note_owned_by_user(db, note_id=payload.note_id, user_id=user_id)

    if payload.revision_id is not None:
        await _ensure_revision_belongs_to_note(
            db, revision_id=payload.revision_id, note_id=payload.note_id
        )

    issue = models_issue.Issue(**payload.model_dump())
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
    db: AsyncSession, user_id: int, issue_id: int, changes: schemas.UpdateIssue
):
    """
    Update an existing issue. If moving it to a different note or revision,
    re-validate ownership and revision consistency.
    """
    issue = await _load_issue_owned_by_user(db, issue_id=issue_id, user_id=user_id)

    data = changes.model_dump(exclude_unset=True)

    # Determine target identifiers if they change
    target_note_id = data.get("note_id", issue.note_id)
    target_revision_id: Optional[int] = data.get("revision_id", issue.revision_id)

    # If moving to a different note, re-authorize
    if target_note_id != issue.note_id:
        await _ensure_note_owned_by_user(db, note_id=target_note_id, user_id=user_id)

    # If revision provided, ensure it belongs to the (possibly new) note
    if target_revision_id is not None:
        await _ensure_revision_belongs_to_note(
            db, revision_id=target_revision_id, note_id=target_note_id
        )

    # Apply changes
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
    """
    issue = await _load_issue_owned_by_user(db, issue_id=issue_id, user_id=user_id)
    issue.deleted_at = datetime.now(timezone.utc)
    issue.is_active = False
    await db.commit()
    await db.refresh(issue)
    return issue
