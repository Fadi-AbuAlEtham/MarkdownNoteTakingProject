from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from .tag import TagService
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

    @staticmethod
    def _split_tag_ids(raw_tag_ids: list[int | None] | None) -> tuple[list[int], set[int]]:
        ignored_ids: set[int] = set()
        valid_candidates: set[int] = set()

        for raw_id in raw_tag_ids or []:
            if raw_id is None:
                continue
            tag_id = int(raw_id)
            if tag_id <= 0:
                ignored_ids.add(tag_id)
                continue
            valid_candidates.add(tag_id)

        return sorted(ignored_ids), valid_candidates

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
        return note

    async def get_all_active_notes(self, skip: int = 0, limit: int = 100):
        """
        Get all active notes
        :param skip: Skip-cursor.
        :param limit: Limit cursor.
        :return: All active notes.
        """
        notes = await self.note_repo.get_all_active_notes(
            user_id=self.user_id, skip=skip, limit=limit
        )
        return notes

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
            ignored_tag_ids, candidate_ids = self._split_tag_ids(note.tag_ids)
            if candidate_ids:
                repo_ignored_ids, valid_tag_ids = await self.tag_service.validate_tags(
                    candidate_ids=candidate_ids
                )
                ignored_tag_ids.extend(repo_ignored_ids)

        title_conflict = (
            await self.note_repo.check_root_note_existence(
                title=note.title, user_id=self.user_id
            )
            if note.folder_id is None
            else await self.note_repo.check_note_existence_in_folder(
                title=note.title, user_id=self.user_id, folder_id=note.folder_id
            )
        )
        if title_conflict:
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
            created_note,
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
            ignored_tag_ids, candidate_ids = self._split_tag_ids(incoming)

            if candidate_ids:
                repo_ignored_ids, valid_ids = await self.tag_service.validate_tags(
                    candidate_ids=candidate_ids
                )
                ignored_tag_ids.extend(repo_ignored_ids)
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
            updated_note,
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
        return deleted_tag
