from fastapi import HTTPException, status

from ..core.utils.format_response import to_response_dict
from ..models.user import User as model_User
from ..core.security import hash_password
from ..schemas import user as schemas_user
from ..repositories.user_repo import UserRepository


class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def get_user_by_id(self, user_id: int):
        """
        Get user by id
        :param user_id: Target User id.
        :return: User object.
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return to_response_dict(schemas_user.UserResponse, user)

    async def get_all_active_users(self, skip: int = 0, limit: int = 100):
        """
        Get all active users
        :param skip: Number of rows to skip (offset).
        :param limit: Maximum number of rows to return.
        :return: Active user list.
        """
        users = await self.user_repo.list_active_users(skip=skip, limit=limit)
        return [to_response_dict(schemas_user.UserResponse, user) for user in users]

    async def get_all_users(self, skip: int = 0, limit: int = 100):
        """
        Get all users
        :param skip: Number of rows to skip (offset).
        :param limit: Maximum number of rows to return.
        :return: User list.
        """
        users = await self.user_repo.list_all_users(skip=skip, limit=limit)
        return [to_response_dict(schemas_user.UserResponse, user) for user in users]

    async def create_user(self, user: schemas_user.CreateUser):
        """
        Create new user
        :param user: Pydantic model that holds the new user payload.
        :return: User created object.
        """
        uname_norm = user.username.strip()
        email_norm = str(user.email).strip().lower()

        if await self.user_repo.exists_by_username(uname_norm):
            raise ValueError("Username is already in use")
        if await self.user_repo.exists_by_email(user.email):
            raise ValueError("Email is already in use")

        payload = user.model_dump(exclude={"password"})
        payload.update(
            {
                "username": uname_norm,
                "email": email_norm,
                "password_hash": hash_password(user.password),
            }
        )

        db_user = model_User(**payload)
        try:
            user = await self.user_repo.create_user(db_user)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        return to_response_dict(schemas_user.UserResponse, user)

    async def update_user(self, user_id: int, payload: schemas_user.UpdateUser):
        """
        Update user
        :param user_id: Target User id.
        :param payload: Pydantic model that holds the new user payload.
        :return: User updated object.
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"User with id: {user_id} doesn't exist!")

        update_data = payload.model_dump(exclude_unset=True)

        if "email" in update_data:
            new_email = str(update_data.pop("email")).strip().lower()
            if await self.user_repo.active_email_exists(
                email=new_email, exclude_user_id=user_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email is already in use",
                )
            update_data["email"] = new_email

        if "username" in update_data:
            new_username = update_data.pop("username").strip()
            if await self.user_repo.active_username_exists(
                username=new_username, exclude_user_id=user_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Username is already in use",
                )
            update_data["username"] = new_username

        if "password" in update_data:
            user.password_hash = hash_password(update_data.pop("password"))

        try:
            user = await self.user_repo.update(user, update_data)
        except ValueError as e:
            msg = str(e).lower()
            if "exist" in msg or "already" in msg or "in use" in msg:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return to_response_dict(schemas_user.UserResponse, user)

    async def soft_delete_user(self, user_id: int):
        """
        Soft-delete user
        :param user_id: Target User id.
        :return: User deleted object.
        """
        try:
            user = await self.user_repo.get_by_id(user_id)
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with id: {user_id} is not found!",
                )
            else:
                deleted_user = await self.user_repo.soft_delete(user)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        return to_response_dict(schemas_user.UserResponse, deleted_user)
