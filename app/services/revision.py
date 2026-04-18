from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from ..models import revision as revision_models
from ..repositories.note import NoteRepository
from ..repositories.revision import RevisionRepository
from ..repositories.tag import TagRepository
from ..schemas import revision as schemas_revision


class RevisionService:
    def __init__(
        self,
        revision_repo: RevisionRepository,
        note_repo: NoteRepository,
        tag_repo: TagRepository,
        user_id: int,
    ):
        self.revision_repo = revision_repo
        self.note_repo = note_repo
        self.tag_repo = tag_repo
        self.user_id = user_id

    async def get_revision_by_id_and_user(self, revision_id: int):
        revision = await self.revision_repo.get_revision_by_id_and_user(
            revision_id=revision_id, user_id=self.user_id
        )
        if not revision:
            raise HTTPException(status_code=404, detail="Revision not found")
        return revision

    async def get_all_revisions(self, skip: int = 0, limit: int = 100):
        return await self.revision_repo.get_all_revisions(skip=skip, limit=limit)

    async def get_all_active_revisions(self, skip: int = 0, limit: int = 100):
        return await self.revision_repo.get_all_active_revisions(
            self.user_id, skip=skip, limit=limit
        )

    async def get_revisions_for_note(
        self, note_id: int, skip: int = 0, limit: int = 100
    ):
        return await self.revision_repo.get_revisions_for_note(
            user_id=self.user_id, note_id=note_id, skip=skip, limit=limit
        )

    async def create_revision(self, revision_to_create: schemas_revision.CreateRevision):
        note = await self.note_repo.get_note_with_tags_by_id_user(
            note_id=revision_to_create.note_id, user_id=self.user_id
        )
        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Note not found or not accessible",
            )

        tag_rows = list(note.tags or [])
        if revision_to_create.tag_ids:
            valid_tag_ids = await self.tag_repo.validate_tags(
                candidate_ids=set(revision_to_create.tag_ids),
                user_id=self.user_id,
            )
            tag_rows = list(await self.tag_repo.get_tags_by_ids(valid_tag_ids))

        updated_note = await self.note_repo.update_note(
            note=note, data={"version": (note.version or 0) + 1}
        )
        db_revision = revision_models.NoteRevision(
            note_id=updated_note.id,
            user_id=self.user_id,
            version=int(updated_note.version),
            title=revision_to_create.title,
            content_md=revision_to_create.content_md,
            is_public=revision_to_create.is_public,
            folder_id=revision_to_create.folder_id,
        )
        db_revision.tags = tag_rows
        try:
            revision = await self.revision_repo.create_revision(db_revision)
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Concurrent revision creation conflict; please retry.",
            )
        return revision

    async def update_revision(
        self, revision_id: int, updated_revision: schemas_revision.UpdateRevision
    ):
        revision = await self.revision_repo.get_revision_by_id_and_user(
            revision_id=revision_id, user_id=self.user_id
        )
        if not revision:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision not found")

        data = updated_revision.model_dump(exclude_unset=True)
        if "title" in data:
            title_exists = await self.revision_repo.title_exists_for_note_excluding_revision(
                note_id=revision.note_id,
                user_id=self.user_id,
                title=data["title"],
                revision_id=revision_id,
            )
            if title_exists:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"This title: {data['title']} is already in use",
                )

        if "tag_ids" in data:
            tag_ids = data.pop("tag_ids") or []
            revision.tags = list(
                await self.tag_repo.get_tags_by_ids(
                    await self.tag_repo.validate_tags(
                        candidate_ids=set(tag_ids),
                        user_id=self.user_id,
                    )
                )
            )

        try:
            revision = await self.revision_repo.update_revision(
                revision=revision,
                data=data,
            )
        except IntegrityError:
            title_for_msg = data.get("title", revision.title)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A revision named '{title_for_msg}' already exists",
            )
        return revision

    async def soft_delete_revision(self, revision_id: int):
        revision = await self.revision_repo.get_revision_by_id_and_user(
            revision_id=revision_id, user_id=self.user_id
        )
        if not revision:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision not found")
        revision = await self.revision_repo.soft_delete(revision)
        return revision

    async def restore_revision(self, note_id: int, revision_id: int):
        revision = await self.revision_repo.get_revision_by_id_and_user_note(
            revision_id=revision_id, user_id=self.user_id, note_id=note_id
        )
        if not revision:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision not found")

        note = await self.note_repo.get_note_with_tags_by_id_user(
            note_id=note_id, user_id=self.user_id
        )
        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Note not found or not accessible",
            )

        revision_tags = await self.revision_repo.get_tags_for_revision(revision.id)
        revision_tag_ids = {tag.id for tag in revision_tags}
        note_tag_ids = {tag.id for tag in note.tags or []}
        identical_to_current = (
            revision.title == note.title
            and revision.content_md == note.content_md
            and bool(revision.is_public) == bool(note.is_public)
            and revision.folder_id == note.folder_id
            and revision_tag_ids == note_tag_ids
        )
        if identical_to_current:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Revision is identical to the current note; nothing to restore.",
            )

        note.tags = list(revision_tags)
        update_data = {
            "title": revision.title,
            "content_md": revision.content_md,
            "is_public": revision.is_public,
            "folder_id": revision.folder_id,
            "version": (note.version or 0) + 1,
        }
        try:
            updated_note = await self.note_repo.update_note(
                note=note,
                data=update_data,
            )
            restored = revision_models.NoteRevision(
                note_id=note_id,
                user_id=self.user_id,
                version=int(updated_note.version),
                title=updated_note.title,
                content_md=updated_note.content_md,
                is_public=updated_note.is_public,
                folder_id=updated_note.folder_id,
            )
            restored.tags = list(revision_tags)
            restored = await self.revision_repo.create_revision(restored)
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Failed to restore revision due to a conflict.",
            )
        return restored
