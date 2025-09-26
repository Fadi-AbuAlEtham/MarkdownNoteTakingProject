from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from .tag import TagService
from ..core.utils.format_response import to_response_dict
from ..repositories.note import NoteRepository
from ..repositories.folder import FolderRepository
from ..repositories.revision import RevisionRepository
from ..repositories.tag import TagRepository
from ..schemas import note as schemas_note
from ..models import note as models, revision as rev_models


class NoteService:
    def __init__(
        self,
        note_repo: NoteRepository,
        folder_repo: FolderRepository,
        tag_service: TagService,
        tag_repo: TagRepository,
        revision_repo: RevisionRepository,
        user_id: int,
    ):
        self.note_repo = note_repo
        self.folder_repo = folder_repo
        self.tag_service = tag_service
        self.tag_repo = tag_repo
        self.revision_repo = revision_repo
        self.user_id = user_id

    async def get_note_by_id_and_user(self, note_id: int):
        """
        Get note by id and user
        :param note_id: Target note id
        :return: Target note object.
        """
        note = await self.note_repo.get_note_by_id_user(
            user_id=self.user_id, note_id=note_id
        )
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")
        return to_response_dict(obj=note, res_type=schemas_note.NoteResponse)

    async def get_all_active_notes(self, user_id: int, skip: int = 0, limit: int = 100):
        """
        Get all active notes
        :param user_id: Target user id.
        :param skip: Skip-cursor.
        :param limit: Limit cursor.
        :return: All active notes.
        """
        notes = await self.note_repo.get_all_active_notes(
            user_id=user_id, skip=skip, limit=limit
        )
        return [
            to_response_dict(obj=n, res_type=schemas_note.NoteResponse) for n in notes
        ]

    async def create_note(self, note: schemas_note.CreateNote):
        """
        Create new note
        :param note: Pydantic model that holds the new note payload.
        :return: (NoteResponse, ignored_tag_ids)
        """
        if note.folder_id is not None:
            folder_exists = await self.folder_repo.get_folder_by_id_and_user(
                user_id=self.user_id, folder_id=note.folder_id
            )
            if not folder_exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Folder with id {note.folder_id} was not found.",
                )

        ignored_tag_ids: list[int] = []
        valid_tag_ids: set[int] = set()

        if note.tag_ids:
            candidate_ids = {int(t) for t in note.tag_ids if t is not None}
            if candidate_ids:
                ignored_tag_ids, valid_tag_ids = await self.tag_service.validate_tags(
                    candidate_ids=candidate_ids
                )

        if await self.note_repo.check_note_existence(
            title=note.title, user_id=self.user_id, folder_id=note.folder_id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"This title: {note.title} exists from before.",
            )

        tag_objs = []
        if valid_tag_ids:
            tag_objs = list(await self.tag_repo.get_tags_by_ids(tag_ids=valid_tag_ids))

        payload = note.model_dump(exclude={"tag_ids"})
        payload["user_id"] = self.user_id
        payload["version"] = 1

        db_note = models.Note(**payload)
        db_note.tags = tag_objs

        try:
            created_note = await self.note_repo.create_note(db_note=db_note)
            if created_note is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Note wasn't created."
                )

            init_rev = rev_models.NoteRevision(
                note_id=created_note.id,
                user_id=self.user_id,
                version=1,
                title=created_note.title,
                content_md=created_note.content_md,
                folder_id=created_note.folder_id,
            )
            init_rev.tags = tag_objs

            db_rev = await self.revision_repo.create_revision(revision=init_rev)
            if db_rev is None:
                await self.note_repo.delete_note(created_note)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Revision for note with id: {created_note.id} wasn't created.",
                )

        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Note title already exists.",
            )

        return (
            to_response_dict(obj=created_note, res_type=schemas_note.NoteResponse),
            ignored_tag_ids,
        )

    async def update_note(self, note_id: int, patch: schemas_note.UpdateNote):
        """
        Update existing note
        :param note_id: Target note id
        :param patch: Updated note payload.
        :return: Updated note object.
        """
        note = await self.note_repo.get_note_by_id_user(
            note_id=note_id, user_id=self.user_id
        )
        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No note with id {note_id} found.",
            )

        data = patch.model_dump(exclude_unset=True)

        target_folder_id: Optional[int] = data.get("folder_id", note.folder_id)
        if "folder_id" in data and target_folder_id is not None:
            folder_exists = await self.folder_repo.get_folder_by_id_and_user(
                user_id=self.user_id, folder_id=target_folder_id
            )
            if not folder_exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Folder with id {target_folder_id} was not found.",
                )

        if "title" in data and data["title"] is not None:
            data["title"] = data["title"].strip()
            if data["title"] == "":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Title cannot be empty.",
                )

        ignored_tag_ids: list[int] = []
        if "tag_ids" in data:
            incoming = data["tag_ids"] or []
            candidate_ids = {int(t) for t in incoming if t is not None}

            if candidate_ids:
                ignored_tag_ids, valid_ids = await self.tag_service.validate_tags(
                    candidate_ids=candidate_ids
                )
                if valid_ids:
                    tag_rows = await self.tag_repo.get_tags_by_ids(tag_ids=valid_ids)
                    note.tags = list(tag_rows)
                else:
                    note.tags = []
            else:
                note.tags = []

            data.pop("tag_ids", None)

        note.version = (note.version or 0) + 1

        try:
            updated_note = await self.note_repo.update_note(note=note, data=data)
        except IntegrityError:
            title_for_msg = data.get("title", note.title)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A note named '{title_for_msg}' already exists.",
            )

        rev = rev_models.NoteRevision(
            note_id=updated_note.id,
            user_id=self.user_id,
            version=int(updated_note.version),
            title=updated_note.title,
            content_md=updated_note.content_md,
            folder_id=updated_note.folder_id,
        )
        rev.tags = list(updated_note.tags)

        try:
            db_rev = await self.revision_repo.create_revision(revision=rev)
            if db_rev is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Revision for note id {updated_note.id} wasn't created.",
                )
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Failed to create revision due to a conflict.",
            )

        return (
            to_response_dict(obj=updated_note, res_type=schemas_note.NoteResponse),
            ignored_tag_ids,
        )

    async def soft_delete_note(self, note_id: int):
        """
        Soft-delete existing note
        :param note_id: Target note id
        :return: Deleted note-object.
        """
        try:
            note = await self.note_repo.get_note_by_id_user(
                user_id=self.user_id, note_id=note_id
            )
            if note is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Note with id: {note_id} is not found!",
                )
            else:
                deleted_tag = await self.note_repo.soft_delete_by_id(note)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        return to_response_dict(obj=deleted_tag, res_type=schemas_note.NoteResponse)
