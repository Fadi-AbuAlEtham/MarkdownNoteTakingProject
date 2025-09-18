from datetime import datetime, timezone
from typing import Mapping, Any

from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists

from ..models import user as models

"""
Async User repository.
"""


class UserRepository:
    model = models.User
    active_filter = models.User.deleted_at.is_(None)

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int):
        """
        Get an active user by its ID.
        :param user_id: target user ID.
        :return: The matching "User" instance, or "None" if not found or soft-deleted.
        """
        stmt = (
            select(self.model).where(self.model.id == user_id).where(self.active_filter)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_by_id_including_deleted(self, user_id: int):
        """
        Get a user byt its ID including soft-deleted.
        :param user_id: target user ID.
        :return: The matching "User" instance, or "None" if not found.
        """
        stmt = select(self.model).where(self.model.id == user_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_by_username(self, username: str):
        """
        Get an active user by its username.
        :param username: target username.
        :return: The matching "User" instance, or "None" if not found or soft-deleted.
        """
        stmt = (
            select(self.model)
            .where(self.model.username == username)
            .where(self.active_filter)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_active_users(self, skip: int = 0, limit: int = 100):
        """
        List all active users.
        :param skip: Starting offset.
        :param limit: Ending offset.
        :return: A list of active users.
        """
        stmt = select(self.model).where(self.active_filter).offset(skip).limit(limit)
        return (await self.db.execute(stmt)).scalars().all()

    async def list_all_users(self, skip: int = 0, limit: int = 100):
        """
        List all users including soft-deleted.
        :param skip: Starting offset.
        :param limit: Ending offset.
        :return: List of all users including the soft-deleted ones.
        """
        stmt = select(self.model).offset(skip).limit(limit)
        return (await self.db.execute(stmt)).scalars().all()

    async def exists_by_email(self, email: EmailStr):
        """
        Check if user exists by its email.
        :param email: target user email.
        :return: True if found, false if not or soft-deleted.
        """
        stmt = select(
            exists().where(self.model.email == email).where(self.active_filter)
        )
        return bool(await self.db.scalar(stmt))

    async def exists_by_username(self, username: str):
        """
        Check if user exists by its name.
        :param username: target username.
        :return: True if found, false if not or soft-deleted.
        """
        stmt = select(
            exists().where(self.model.username == username).where(self.active_filter)
        )
        return bool(await self.db.scalar(stmt))

    async def create_user(self, user: models.User):
        """Create a user. Expects `data` to include `password_hash` (not plain password).
        :param user: user to be inserted.
        :return: user object created.
        """
        self.db.add(user)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update(self, user: models.User, data: Mapping[str, Any]):
        """Partial update a user
        :param user: object to be updated.
        :param data:
        """
        # user = await self.get_by_id(user_id)
        # if user is None:
        #     return None
        for k, v in data.items():
            setattr(user, k, v)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def soft_delete(self, user: models.User):
        """
        Soft delete a user.
        :param user: user to be deleted.
        :return: soft-deleted user.
        """
        user.deleted_at = datetime.now(timezone.utc)
        user.is_active = False
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def active_email_exists(self, email: str, *, exclude_user_id: int):
        """
        Return True if an ACTIVE user (deleted_at IS NULL) exists with this email.
        Optionally exclude a specific user id.
        Expects 'email' to be already normalized by the caller (if desired).
        """
        stmt = select(
            exists().where(self.model.email == email).where(self.active_filter)
        )
        if exclude_user_id is not None:
            stmt = stmt.where(self.model.id != exclude_user_id)
        return bool(await self.db.scalar(stmt))

    async def active_username_exists(self, username: str, *, exclude_user_id: int):
        """
        Return True if an ACTIVE user (deleted_at IS NULL) exists with this username.
        Optionally exclude a specific user id.
        Expects 'username' to be already normalized by the caller (if desired).
        """
        stmt = select(
            exists().where(self.model.username == username).where(self.active_filter)
        )
        if exclude_user_id is not None:
            stmt = stmt.where(self.model.id != exclude_user_id)
        return bool(await self.db.scalar(stmt))
