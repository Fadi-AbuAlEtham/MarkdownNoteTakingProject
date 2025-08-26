from datetime import datetime, timezone

from pydantic import EmailStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists, func
from ..models import user as models
from ..schemas import user as schemas


async def get_user_by_id(db: AsyncSession, user_id: int):
    stmt = (
        select(models.User)
        .where(models.User.id == user_id)
        .where(models.User.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_all_users(db: AsyncSession, skip: int = 0, limit: int = 100):
    stmt = (
        select(models.User)
        .where(models.User.deleted_at.is_(None))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_user_by_id_including_deleted(db: AsyncSession, user_id: int):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    return result.scalar_one_or_none()


async def user_exists_by_email(db: AsyncSession, email: EmailStr) -> bool:
    email_norm = str(email).strip().lower()
    stmt = select(
        exists()
        .where(
            func.lower(models.User.email) == email_norm,
        )
        .where(models.User.deleted_at.is_(None))
    )
    return await db.scalar(stmt)


async def user_exists_by_username(db: AsyncSession, username: str) -> bool:
    uname_norm = username.strip().lower()
    stmt = select(
        exists()
        .where(
            func.lower(models.User.username) == uname_norm,
        )
        .where(models.User.deleted_at.is_(None))
    )
    return await db.scalar(stmt)


async def update_user(db: AsyncSession, user_id: int, update_user: schemas.UpdateUser):
    user = await get_user_by_id(db, user_id)
    if not user:
        return None

    update_data = update_user.model_dump(exclude_unset=True)

    # email
    if "email" in update_data:
        new_email = str(update_data["email"]).strip().lower()
        stmt = select(
            exists()
            .where(func.lower(models.User.email) == new_email)
            .where(models.User.id != user_id)
            .where(models.User.deleted_at.is_(None))
        )
        if await db.scalar(stmt):
            raise ValueError("Email is already in use")
        update_data["email"] = new_email

    # username
    if "username" in update_data:
        new_username = update_data["username"].strip().lower()
        stmt = select(
            exists()
            .where(func.lower(models.User.username) == new_username)
            .where(models.User.id != user_id)
            .where(models.User.deleted_at.is_(None))
        )
        if await db.scalar(stmt):
            raise ValueError("Username is already in use")
        update_data["username"] = new_username

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
    email_norm = str(user.email).strip().lower()
    uname_norm = user.username.strip().lower()

    if await user_exists_by_username(db, uname_norm):
        raise ValueError("Username is already in use")
    if await user_exists_by_email(db, email_norm):
        raise ValueError("Email is already in use")

    payload = user.model_dump()
    payload["email"] = email_norm
    payload["username"] = uname_norm

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
    user = await db.scalar(select(models.User).where(models.User.id == user_id))
    if not user:
        raise ValueError("User doesn't exist!")
    if user.deleted_at:
        return user
    user.deleted_at = datetime.now(timezone.utc)
    user.is_active = False
    await db.commit()
    await db.refresh(user)
    return user


async def restore_user_by_id(db: AsyncSession, user_id: int):
    user = await db.scalar(select(models.User).where(models.User.id == user_id))
    if not user:
        raise ValueError("User doesn't exist!")
    if user.deleted_at is None:
        return user
    user.deleted_at = None
    user.is_active = True
    await db.commit()
    await db.refresh(user)
    return user
