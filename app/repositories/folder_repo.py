from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists, func, update
from sqlalchemy.orm import aliased

from ..models import folder as models
from ..schemas import folder as schemas

"""
Async folder repository.

- Active-only reads by default (`deleted_at IS NULL`).
- Title uniqueness per user + parent (sibling level); DB should enforce via partial UNIQUE index.
- Create/Update validate parent ownership/access; Update checks conflicts in target level.
- Soft delete cascades to active descendants using a recursive CTE (sets `deleted_at`, 
  `is_active=False`).
- Pre-checks for conflicts; DB remains final arbiter (catch `IntegrityError` on commit).
- Prefer CITEXT for case-insensitive title equality without LOWER().
"""


async def get_folder_by_id(db: AsyncSession, folder_id: int):
    """
        Fetch certain folder from its id (only active folders; not soft-deleted)
    :param
        db: Async SQLAlchemy session.
        folder_id: Database primary key.
    :return:
        The matching "Folder" instance, or "None" if not found or soft-deleted.
    """
    stmt = (
        select(models.Folder)
        .where(models.Folder.id == folder_id)
        .where(models.Folder.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_all_active_folders(db: AsyncSession, skip: int, limit: int):
    """
        Fetch all active folders.
    :param
        db: Async SQLAlchemy session.
        skip: Number of rows to skip (offset).
        limit: Maximum number of rows to return.
    :return:
        All active Folders, or None if not found or soft-deleted.
    """

    stmt = (
        select(models.Folder)
        .where(models.Folder.deleted_at.is_(None))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def folder_exists_by_title(db: AsyncSession, user_id: int, title: str):
    """
        Check folder existence by title for a certain user by its id

    :param
        db: Async SQLAlchemy session.
        user_id: Target user's ID.
        title: Target folder's title

    :return:
        True if another title exists for the same user; otherwise False.

    """
    title_edited = title.strip()
    stmt = select(
        exists().where(
            models.Folder.user_id == user_id,
            models.Folder.deleted_at.is_(None),
            func.lower(models.Folder.title.concat()) == title_edited.lower(),
        )
    )
    return await db.scalar(stmt)


async def folder_exists_by_title_at_level(
    db: AsyncSession, user_id: int, parent_id: int | None, title: str
) -> bool:
    """
        Check folder title existence within the same level for a certain user.
    :param
        db: Async SQLAlchemy session.
        user_id: Target user ID.
        parent_id: Target parent level ID.
        title: Target folder title.
    :return:
        Returns true if a title exist within the same level for the same user or false if None.
    """

    title_edited = title.strip()
    conditions = [
        models.Folder.user_id == user_id,
        models.Folder.deleted_at.is_(None),
        models.Folder.title == title_edited,
    ]
    if parent_id is None:
        conditions.append(models.Folder.parent_id.is_(None))
    else:
        conditions.append(models.Folder.parent_id == parent_id)

    stmt = select(exists().where(*conditions))
    return await db.scalar(stmt)


async def get_folder_by_id_including_deleted(db: AsyncSession, folder_id: int):
    """Fetch a folder by ID, including soft-deleted rows.

    Args:
        db: Async SQLAlchemy session.
        folder_id: Database primary key.

    Returns:
        The matching "Folder" instance or "None" if not found.
    """
    result = await db.execute(select(models.Folder).where(models.Folder.id == folder_id))
    return result.scalar_one_or_none()


async def create_folder(db: AsyncSession, user_id: int, folder: schemas.FolderCreate):
    """
        Create new folder with distinct title for a certain user.
    :param
        db: Async SQLAlchemy session.
        user_id: Target user ID.
        folder:  Pydantic payload containing folder's fields.

    :return:
        The newly created folder instance.

    Raises:
        ValueError: If title already exists for the same user.
    """
    title = folder.title.strip()
    parent_id = folder.parent_id

    # validate that parent_id belongs to the same user (and is active), if provided
    if parent_id is not None:
        parent = await db.scalar(
            select(models.Folder).where(
                models.Folder.id == parent_id,
                models.Folder.user_id == user_id,
                models.Folder.deleted_at.is_(None),
            )
        )
        if not parent:
            raise ValueError("Parent folder not found or not accessible")

    if await folder_exists_by_title_at_level(db, user_id, parent_id, title):
        raise ValueError(f"A folder named '{title}' already exists at this level.")

    payload = folder.model_dump()
    payload["user_id"] = user_id
    payload["title"] = title

    db_folder = models.Folder(**payload)
    db.add(db_folder)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # Catches races that slipped past the pre-check
        raise ValueError(f"A folder named '{title}' already exists at this level.")
    await db.refresh(db_folder)
    return db_folder


async def update_folder(
    db: AsyncSession, user_id: int, folder_id: int, updated_folder: schemas.FolderUpdate
):
    """
        Update Folder attributes.

    :param db: Async SQLAlchemy session.
    :param user_id: Target User ID.
    :param folder_id: Target Folder ID
    :param updated_folder: Pydantic payload containing folder's fields.
    :return: The updated folder instance or None if the folder doesn't exist or soft-deleted
    :raises:
        ValueError: If the new title conflicts with another active title
            or if the commit hits a uniqueness violation, or if the folder doesn't exist.
    """

    folder = get_folder_by_id(db, folder_id)
    if not folder:
        raise ValueError(f"Folder with id: {folder_id} doesn't exist!")

    data = updated_folder.model_dump(exclude_unset=True)

    target_parent_id = data.get("parent_id", folder.parent_id)

    # Parent
    if target_parent_id is not None:
        if target_parent_id == folder_id:
            raise ValueError("A folder cannot be its own parent")
        parent = await db.scalar(
            select(models.Folder).where(
                models.Folder.id == target_parent_id,
                models.Folder.user_id == user_id,
                models.Folder.deleted_at.is_(None),
            )
        )
        if not parent:
            raise ValueError("Parent folder not found or not accessible")

    # Determine the title to check (new or current), trim edges
    target_title = data.get("title", folder.title)
    if isinstance(target_title, str):
        target_title = target_title.strip()

    # Uniqueness pre-check: same user, same parent level, different id, active only
    conditions = [
        models.Folder.user_id == user_id,
        models.Folder.deleted_at.is_(None),
        models.Folder.id != folder_id,
        models.Folder.title == target_title,
    ]

    if target_parent_id is None:
        conditions.append(models.Folder.parent_id.is_(None))
    else:
        conditions.append(models.Folder.parent_id == target_parent_id)

    if await db.scalar(select(exists().where(*conditions))):
        raise ValueError(
            f"A folder named '{target_title}' already exists at this level"
        )

    # Apply the mutation
    if "title" in data:
        folder.title = target_title
        del data["title"]
    if "parent_id" in data:
        folder.parent_id = target_parent_id
        del data["parent_id"]

    for key, value in data.items():
        setattr(folder, key, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # DB-level partial UNIQUE index is the final arbiter; translate race to a friendly message
        raise ValueError(
            f"A folder named '{target_title}' already exists at this level"
        )

    await db.refresh(folder)
    return folder


async def soft_delete_folder_by_id(db: AsyncSession, user_id: int, folder_id: int):
    """
        Soft delete a folder and its children.
    :param db: Async SQLAlchemy session.
    :param user_id: Target User ID.
    :param folder_id: Target Folder ID
    :return: The updated folder instance with "deleted_at" and "is_active" attributes.
    """

    fd = models.Folder
    now = datetime.now(timezone.utc)

    stmt = (
        select(fd)
        .where(fd.id == folder_id)
        .where(fd.user_id == user_id)
        .where(fd.deleted_at.is_(None))
    )

    root = await db.scalar(stmt)

    if not root:
        raise ValueError(
            f"Folder with id: {folder_id} doesn't exist or is already deleted"
        )

    # Build recursive CTE of root + all descendants (active only)
    tree = (
        select(fd.id, fd.parent_id)
        .where(fd.id == folder_id, fd.user_id == user_id, fd.deleted_at.is_(None))
        .cte("tree", recursive=True)
    )

    ct = aliased(fd)
    tree = tree.union_all(
        select(ct.id, ct.parent_id).where(
            ct.parent_id == tree.c.id,
            ct.user_id == user_id,
            ct.deleted_at.is_(None),
        )
    )

    # Bulk soft-delete all in the tree
    await db.execute(
        update(fd)
        .where(fd.id.in_(select(tree.c.id)))
        .values(deleted_at=now, is_active=False)
    )
    await db.commit()

    # Refresh and return the root
    return await db.scalar(select(fd).where(fd.id == folder_id))
