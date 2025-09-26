from fastapi import HTTPException, status

from ..core.utils.format_response import to_response_dict
from ..models import tag as model_tag
from ..schemas import tag as schemas_tag
from ..repositories.tag import TagRepository


class TagService:
    def __init__(self, tag_repo: TagRepository, user_id: int):
        self.tag_repo = tag_repo
        self.user_id = user_id

    async def get_tag_by_id_and_user(self, tag_id: int):
        """
        Get tag by id
        :param tag_id: Target tag ID
        :return: Tag object
        """
        tag = await self.tag_repo.get_tag_by_id_and_user(self.user_id, tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")
        return to_response_dict(obj=tag, res_type=schemas_tag.TagResponse)

    async def get_all_active_tags(self, skip: int = 0, limit: int = 100):
        """
        Get all active tags.
        :param skip: Number of rows to skip (offset).
        :param limit: Maximum number of rows to return.
        :return: All active tags.
        """
        tags = await self.tag_repo.get_all_active_tags(
            user_id=self.user_id, skip=skip, limit=limit
        )
        return [to_response_dict(obj=t, res_type=schemas_tag.TagResponse) for t in tags]

    async def get_all_tags(self, skip: int = 0, limit: int = 100):
        """
        Get all tags.
        :param skip: Number of rows to skip (offset).
        :param limit: Maximum number of rows to return.
        :return: All tags.
        """
        tags = await self.tag_repo.get_all_tags(skip=skip, limit=limit)
        return [to_response_dict(obj=t, res_type=schemas_tag.TagResponse) for t in tags]

    # async def get_active_notes_for_tag(self, tag_id: int):
    #     """
    #     Get active notes for a tag.
    #     :param db: Async SQLAlchemy session.
    #     :param user_id: target user_id
    #     :param tag_id: Target tag ID
    #     :return: Active notes for a tag.
    #     """
    #     tag = await self.tag_repo.get_tag_by_id_and_user(
    #         user_id=self.user_id, tag_id=tag_id
    #     )
    #     if not tag:
    #         raise HTTPException(status_code=404, detail="Tag not found")
    #
    #     notes = await note_repo.get_active_notes_by_tag(
    #         user_id=self.user_id, tag_id=tag_id
    #     )
    #
    #     return {
    #         "tag": to_response_dict(tag),
    #         "notes": [note_to_response(n) for n in notes],
    #     }

    async def create_tag(self, tag_to_create: schemas_tag.CreateTag):
        """
        Create new tag.
        :param tag_to_create: Pydantic model that holds the tag payload.
        :return: The created tag.
        """
        if await self.tag_repo.check_tag_existence_by_title(
            user_id=self.user_id, title=tag_to_create.title
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"This title: {tag_to_create.title} exists from before.",
            )

        payload = tag_to_create.model_dump()
        payload["user_id"] = self.user_id

        db_tag = model_tag.Tag(**payload)
        try:
            tag = await self.tag_repo.create_tag(tag=db_tag)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        return to_response_dict(obj=tag, res_type=schemas_tag.TagResponse)

    async def update_tag(self, tag_id: int, tag_to_update: schemas_tag.UpdateTag):
        """
        Update existing tag.
        :param tag_id: Target tag ID.
        :param tag_to_update: Pydantic model that holds the tag payload.
        :return: The updated tag.
        """
        tag = await self.tag_repo.get_tag_by_id_and_user(
            user_id=self.user_id, tag_id=tag_id
        )
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tag with id: {tag_id} is not found!",
            )
        data = tag_to_update.model_dump(exclude_unset=True)

        if await self.tag_repo.active_title_exists(
            tag_id=tag_id, user_id=self.user_id, title=tag_to_update.title
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Title is already in use",
            )

        try:
            tag = await self.tag_repo.update_tag(tag=tag_to_update, data=data)
        except ValueError as e:
            msg = str(e).lower()
            if "exist" in msg or "duplicate" in msg or "already" in msg:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
            )
        return to_response_dict(obj=tag, res_type=schemas_tag.TagResponse)

    async def soft_delete_tag(self, tag_id: int):
        """
        Soft-delete existing tag.
        :param tag_id: Target tag ID.
        :return: The soft-deleted tag.
        """

        try:
            tag = await self.tag_repo.get_tag_by_id_and_user(
                user_id=self.user_id, tag_id=tag_id
            )
            if tag is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tag with id: {tag_id} is not found!",
                )
            else:
                deleted_tag = await self.tag_repo.soft_delete_by_id(tag)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        return to_response_dict(obj=deleted_tag, res_type=schemas_tag.TagResponse)

    async def validate_tags(self, candidate_ids: set[int]):
        valid_ids = await self.tag_repo.validate_tags(
            candidate_ids=candidate_ids, user_id=self.user_id
        )
        ignored_tag_ids = sorted(candidate_ids - valid_ids)
        if not valid_ids:
            raise ValueError(f"No valid tags found for IDs: {sorted(candidate_ids)}")
        return ignored_tag_ids, valid_ids
