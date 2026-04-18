from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from ..repositories.folder import FolderRepository
from ..repositories.note import NoteRepository
from ..schemas import folder as schemas_folder, note as schemas_note
from ..models import folder as models


class FolderService:
    def __init__(
        self, folder_repo: FolderRepository, note_repo: NoteRepository, user_id: int
    ):
        self.folder_repo = folder_repo
        self.note_repo = note_repo
        self.user_id = user_id

    async def get_folder_by_and_user(self, folder_id: int):
        """
        Get folder by and user
        :param folder_id: Target folder id
        :return: Folder object
        """
        folder = await self.folder_repo.get_folder_by_id_and_user(
            self.user_id, folder_id
        )
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")
        return folder

    async def get_all_active_folders(self, skip: int = 0, limit: int = 100):
        """
        Get all active folders
        :param skip: Number of items to skip
        :param limit: Number of items to return
        :return: List of all active folders
        """
        folders = await self.folder_repo.get_all_active_folders(
            user_id=self.user_id, skip=skip, limit=limit
        )
        return folders

    async def get_active_notes_in_folder(self, folder_id: int):
        """
        Get active notes in folder.
        :param folder_id: Target folder id
        :return: List of active notes in folder
        """
        folder = await self.folder_repo.get_folder_by_id_and_user(
            user_id=self.user_id, folder_id=folder_id
        )
        if not folder or folder.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Folder not found")

        notes = await self.note_repo.get_active_notes_in_folder(
            user_id=self.user_id, folder_id=folder_id
        )

        return {
            "folder": folder,
            "notes": notes,
        }

    async def create_folder(self, folder_to_create: schemas_folder.FolderCreate):
        """
        Create new folder
        :param folder_to_create: Pydantic model that holds the new folder payload
        :return: Created folder
        """
        try:
            title = folder_to_create.title.strip()
            parent_id = folder_to_create.parent_id

            if parent_id is not None:
                parent = await self.folder_repo.get_folder_by_id_and_user(
                    user_id=self.user_id, folder_id=parent_id
                )
                if not parent:
                    raise ValueError("Parent folder not found or not accessible")

            root_conflict = parent_id is None and await self.folder_repo.folder_exists_by_title_at_root(
                self.user_id, title
            )
            child_conflict = parent_id is not None and await self.folder_repo.folder_exists_by_title_in_parent(
                self.user_id, parent_id, title
            )
            if root_conflict or child_conflict:
                raise ValueError(
                    f"A folder named '{title}' already exists at this level."
                )

            payload = folder_to_create.model_dump()
            payload["user_id"] = self.user_id
            payload["title"] = title

            db_folder = models.Folder(**payload)
            folder = await self.folder_repo.create_folder(db_folder)
            if folder is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Note wasn't created."
                )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A folder named '{folder_to_create.title}' already exists at this level.",
            )
        return folder

    async def update_folder(
        self,
        folder_id: int,
        folder_to_update: schemas_folder.FolderUpdate,
    ):
        """
        Update folder
        :param folder_id: Target folder id
        :param folder_to_update: Pydantic model that holds the new folder payload
        :return: Updated folder
        """
        try:
            folder = await self.folder_repo.get_folder_by_id_and_user(
                folder_id=folder_id, user_id=self.user_id
            )
            if not folder:
                raise ValueError(f"Folder with id: {folder_id} doesn't exist!")

            data = folder_to_update.model_dump(exclude_unset=True)
            target_parent_id = data.get("parent_id", folder.parent_id)

            if target_parent_id is not None:
                if target_parent_id == folder_id:
                    raise ValueError("A folder cannot be its own parent")
                parent = await self.folder_repo.get_folder_by_id_and_user(
                    folder_id=target_parent_id, user_id=self.user_id
                )
                if not parent:
                    raise ValueError("Parent folder not found or not accessible")

            target_title = data.get("title", folder.title)
            if isinstance(target_title, str):
                target_title = target_title.strip()

            if "title" in data:
                folder.title = target_title
                del data["title"]
            if "parent_id" in data:
                folder.parent_id = target_parent_id
                del data["parent_id"]
            folder = await self.folder_repo.update_folder(folder=folder, data=data)
        except ValueError as e:
            msg = str(e).lower()
            if "exist" in msg or "duplicate" in msg or "already" in msg:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
            )
        return folder

    async def soft_delete_folder(self, folder_id: int):
        """
        Soft delete a folder and its descendants for the current user.
        Returns the deleted folder (including parent/children) so the client can reflect UI changes.
        """
        folder = await self.folder_repo.get_folder_by_id_and_user(
            folder_id=folder_id, user_id=self.user_id
        )
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Folder with id: {folder_id} doesn't exist or is already deleted.",
            )

        updated_rows = await self.folder_repo.soft_delete_subtree(
            user_id=self.user_id, root_folder_id=folder_id
        )
        if updated_rows == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Folder was already deleted.",
            )

        deleted_folder = await self.folder_repo.get_folder_by_id_any_status(
            folder_id=folder_id
        )
        if not deleted_folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder not found after deletion.",
            )

        return deleted_folder
