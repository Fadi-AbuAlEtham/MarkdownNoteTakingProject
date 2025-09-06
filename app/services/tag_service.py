from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas import tag as schemas_tag
from ..repositories import tag_repo


def to_response_dict(obj) -> dict:
    """
    Convert response to dict.
    :param obj: Response to convert.
    :return: Response dict.
    """
    return schemas_tag.TagResponse.model_validate(
        obj, from_attributes=True
    ).model_dump()


async def get_tag_by_id_and_user(db: AsyncSession, user_id: int, tag_id: int):
    """
    Get tag by id
    :param db: Async SQLAlchemy session.
    :param user_id: User id.
    :param tag_id: Target tag ID
    :return: Tag object
    """
    tag = await tag_repo.get_tag_by_id_and_user(db, user_id, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return to_response_dict(tag)


async def get_all_active_tags(db: AsyncSession, skip: int = 0, limit: int = 100):
    """
    Get all active tags.
    :param db: Async SQLAlchemy session.
    :param skip: Number of rows to skip (offset).
    :param limit: Maximum number of rows to return.
    :return: All active tags.
    """
    tags = await tag_repo.get_all_active_tags(db, skip=skip, limit=limit)
    return [to_response_dict(t) for t in tags]


async def get_all_tags(db: AsyncSession, skip: int = 0, limit: int = 100):
    """
    Get all tags.
    :param db: Async SQLAlchemy session.
    :param skip: Number of rows to skip (offset).
    :param limit: Maximum number of rows to return.
    :return: All tags.
    """
    tags = await tag_repo.get_all_tags(db, skip=skip, limit=limit)
    return [to_response_dict(t) for t in tags]


async def create_tag(
    db: AsyncSession, user_id: int, tag_to_create: schemas_tag.CreateTag
):
    """
    Create new tag.
    :param db: Async SQLAlchemy session.
    :param user_id: Target user id.
    :param tag_to_create: Pydantic model that holds the tag payload.
    :return: The created tag.
    """
    try:
        tag = await tag_repo.create_tag(db, user_id=user_id, tag=tag_to_create)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return to_response_dict(tag)


async def update_tag(
    db: AsyncSession, user_id: int, tag_id: int, tag_to_update: schemas_tag.UpdateTag
):
    """
    Update existing tag.
    :param db: Async SQLAlchemy session.
    :param user_id: Target user id.
    :param tag_id: Target tag ID.
    :param tag_to_update: Pydantic model that holds the tag payload.
    :return: The updated tag.
    """
    try:
        tag = await tag_repo.update_tag(
            db, user_id=user_id, tag_id=tag_id, updated_tag=tag_to_update
        )
    except ValueError as e:
        msg = str(e).lower()
        if "exist" in msg or "duplicate" in msg or "already" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
        )
    return to_response_dict(tag)


async def soft_delete_tag(db: AsyncSession, user_id: int, tag_id: int):
    """
    Soft-delete existing tag.
    :param db: Async SQLAlchemy session.
    :param user_id: Target user id.
    :param tag_id: Target tag ID.
    :return: The soft-deleted tag.
    """
    try:
        tag = await tag_repo.soft_delete_by_id(db, user_id=user_id, tag_id=tag_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return to_response_dict(tag)
