from datetime import datetime, timezone

from pydantic import EmailStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists

from ..core.security import hash_password
from ..models import user as models
from ..schemas import user as schemas

"""
Async User repository.

This module provides CRUD and helper methods for the User entity using
SQLAlchemy's async APIs. It implements:

- Read helpers that, by default, return only active users;
  (deleted_at IS NULL), in addition to others that include soft-deleted rows.
- Existence checks for "email" and "username" that ignore soft-deleted users.
- Update logic that:
    - Applies partial updates from a Pydantic schema.
    - Enforces case-insensitive uniqueness (excluding the current user).
    - Normalizes "email"/"username" to lowercase for accepted storage.
    - Relies on database UNIQUE indexes as the final arbiter (catches
      "IntegrityError" on commit).
- Create logic with pre-checks and "IntegrityError" handling.
- Soft delete (sets "deleted_at" and "is_active=False") and restore helpers.

Notes:
    - The database schema uses partial UNIQUE indexes on "email"/"username"
      that apply only when "deleted_at IS NULL", allowing reuse of identifiers
      after a soft delete.
    - Although PostgreSQL "CITEXT" provides case-insensitive comparisons,
      inputs are still normalized to lowercase here for accepted storage and
      consistency across non-DB consumers (logs, caches, etc.).
"""


async def get_user_by_id(db: AsyncSession, user_id: int):
    """Fetch an active user by numeric ID.

    Only returns a user whose deleted_at IS NULL (not soft deleted).

    Args:
        db: Async SQLAlchemy session.
        user_id: Database primary key.

    Returns:
        The matching "User" instance, or "None" if not found or soft-deleted.
    """
    stmt = (
        select(models.User)
        .where(models.User.id == user_id)
        .where(models.User.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str):
    """
    Get an active user by username.
    Only returns a user whose deleted_at IS NULL (not soft-deleted).
    Args:
        db: Async SQLAlchemy session.
        username: Database primary key.

    Returns:
        The matching "User" instance, or "None" if not found or soft-deleted.
    """
    stmt = (
        select(models.User)
        .where(models.User.username == username.strip())
        .where(models.User.deleted_at.is_(None))
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_all_active_users(db: AsyncSession, skip: int = 0, limit: int = 100):
    """List active users with pagination.

    Args:
        db: Async SQLAlchemy session.
        skip: Number of rows to skip (offset).
        limit: Maximum number of rows to return.

    Returns:
        A list of "User" objects that are not soft-deleted.
    """
    stmt = (
        select(models.User)
        .where(models.User.deleted_at.is_(None))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_all_users(db: AsyncSession, skip: int = 0, limit: int = 100):
    """List all users with pagination.

    Args:
        db: Async SQLAlchemy session.
        skip: Number of rows to skip (offset).
        limit: Maximum number of rows to return.

    Returns:
        A list of "User" objects.
    """
    stmt = select(models.User).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_user_by_id_including_deleted(db: AsyncSession, user_id: int):
    """Fetch a user by ID, including soft-deleted rows.

    Args:
        db: Async SQLAlchemy session.
        user_id: Database primary key.

    Returns:
        The matching "User" instance or "None" if not found.
    """
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    return result.scalar_one_or_none()


async def user_exists_by_email(db: AsyncSession, email: EmailStr) -> bool:
    """Check if an active user exists with the given email (case-insensitive --> CITEXT).

    Soft-deleted users are ignored.

    Args:
        db: Async SQLAlchemy session.
        email: Email to check.

    Returns:
        True if another active user exists with this email; otherwise False.
    """
    stmt = select(
        exists()
        .where(models.User.email == str(email))
        .where(models.User.deleted_at.is_(None))
    )
    return await db.scalar(stmt)


async def user_exists_by_username(db: AsyncSession, username: str) -> bool:
    """Check if an active user exists with the given username (case-insensitive).

    Soft-deleted users are ignored.

    Args:
        db: Async SQLAlchemy session.
        username: Username to check.

    Returns:
        True if another active user exists with this username; otherwise False.
    """
    uname_norm = username.strip()
    stmt = select(
        exists()
        .where(models.User.username == uname_norm)
        .where(models.User.deleted_at.is_(None))
    )
    return await db.scalar(stmt)


async def update_user(db: AsyncSession, user_id: int, updated_user: schemas.UpdateUser):
    """Partially update an active user and return the updated row.

    Applies only provided fields from the Pydantic schema. For "email" and
    "username", values are normalized to lowercase and checked for conflicts
    against other active users (excluding the current user). The database
    remains the final arbiter of uniqueness; a race will be surfaced as an
    "IntegrityError", which is caught and rethrown as a "ValueError".

    Args:
        db: Async SQLAlchemy session.
        user_id: Target user's ID (must be active).
        updated_user: Partial update payload.

    Returns:
        The updated `User` instance, or `None` if the user doesn't exist or is
        soft-deleted.

    Raises:
        ValueError: If the new email/username conflicts with another active user
            or if the commit hits a uniqueness violation, or if the user doesn't exist.
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"User with id: {user_id} doesn't exist!")

    update_data = updated_user.model_dump(exclude_unset=True)

    if "email" in update_data:
        new_email = str(update_data.pop("email")).strip().lower()
        stmt = select(
            exists()
            .where(models.User.email == new_email)
            .where(models.User.id != user_id)
            .where(models.User.deleted_at.is_(None))
        )
        if await db.scalar(stmt):
            raise ValueError("Email is already in use")
        update_data["email"] = new_email

    # username
    if "username" in update_data:
        new_username = update_data.pop("username").strip()
        stmt = select(
            exists()
            .where(models.User.username == new_username)
            .where(models.User.id != user_id)
            .where(models.User.deleted_at.is_(None))
        )
        if await db.scalar(stmt):
            raise ValueError("Username is already in use")
        update_data["username"] = new_username

    if "password" in update_data:
        user.password_hash = hash_password(update_data.pop("password"))

    for k, v in update_data.items():
        setattr(user, k, v)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError("Email or username already exists")
    await db.refresh(user)
    return user


async def create_user(db: AsyncSession, user: schemas.CreateUser):
    """Create a new user after validating uniqueness.

    Normalizes "email" and "username" to lowercase, then pre-checks for active
    duplicates. On commit, any race is handled by catching `IntegrityError` and
    surfacing a friendly "ValueError".

    Args:
        db: Async SQLAlchemy session.
        user: Pydantic payload containing user's fields.

    Returns:
        The newly created "User" instance.

    Raises:
        ValueError: If "username" or "email" already exists among active users,
            or if a race triggers a uniqueness violation on commit.
    """
    uname_norm = user.username.strip()
    email_norm = str(user.email).strip().lower()

    if await user_exists_by_username(db, uname_norm):
        raise ValueError("Username is already in use")
    if await user_exists_by_email(db, user.email):
        raise ValueError("Email is already in use")

    payload = user.model_dump(exclude={"password"})
    payload.update(
        {
            "username": uname_norm,
            "email": email_norm,
            "password_hash": hash_password(user.password),
        }
    )

    db_user = models.User(**payload)
    db.add(db_user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # Handles race condition, or restore conflict if unique indexes hit
        raise ValueError("Email or username already exists")
    await db.refresh(db_user)
    return db_user


async def soft_delete_user_by_id(db: AsyncSession, user_id: int):
    """Soft-delete a user by setting "deleted_at" and "is_active=False".

    If the user is already soft-deleted, this is a no-op and the user is
    returned unchanged.

    Args:
        db: Async SQLAlchemy session.
        user_id: Target user's ID.

    Returns:
        The updated "User" instance with "deleted_at" set.

    Raises:
        ValueError: If the user does not exist.
    """
    user = await db.scalar(select(models.User).where(models.User.id == user_id))
    if not user:
        raise ValueError(f"User with id: {user_id} doesn't exist!")
    if user.deleted_at:
        return user
    user.deleted_at = datetime.now(timezone.utc)
    user.is_active = False
    await db.commit()
    await db.refresh(user)
    return user


async def restore_user_by_id(db: AsyncSession, user_id: int):
    """Restore a previously soft-deleted user.

    Clears "deleted_at" and sets "is_active=True". If the user is not
    soft-deleted, this is a no-op and the user is returned unchanged.

    Args:
        db: Async SQLAlchemy session.
        user_id: Target user's ID.

    Returns:
        The restored "User" instance.

    Raises:
        ValueError: If the user does not exist.
    """
    user = await db.scalar(select(models.User).where(models.User.id == user_id))
    if not user:
        raise ValueError(f"User with id: {user_id} doesn't exist!")
    if user.deleted_at is None:
        return user
    user.deleted_at = None
    user.is_active = True
    await db.commit()
    await db.refresh(user)
    return user
