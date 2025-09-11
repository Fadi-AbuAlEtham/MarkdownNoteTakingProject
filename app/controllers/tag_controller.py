from typing import Annotated, List

from fastapi import APIRouter, Depends, status
from fastapi.params import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.core.db import get_db
from app.schemas import tag as tag_schema
from app.services import tag_service

router = APIRouter(prefix="/users", tags=["user"])


@router.get(
    "/{tag_id}",
    response_model=tag_schema.TagResponse,
    status_code=status.HTTP_200_OK,
)
async def get_tag_by_id(
    tag_id: Annotated[int, Path(title="The ID of the tag to get", gt=0)],
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Get a tag by ID.
    :param tag_id: Target tag ID.
    :param db: Async SQLAlchemy session.
    :param current_user_id: The ID of the current user.
    :return: The target tag.
    """
    return await tag_service.get_tag_by_id_and_user(
        db, tag_id=tag_id, user_id=current_user_id
    )


@router.get(
    "/",
    response_model=List[tag_schema.TagResponse],
    status_code=status.HTTP_200_OK,
)
async def get_all_active_tags(
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Get all active tags.
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :return: List of all active tags for the current user
    """
    return await tag_service.get_all_active_tags(db, current_user_id)


@router.post(
    "/",
    response_model=tag_schema.TagResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tag(
    tag: tag_schema.CreateTag,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Create a new tag.
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :param tag: Pydantic model that holds the new tag payload
    :return: The newly created tag
    """
    return await tag_service.create_tag(db, user_id=current_user_id, tag_to_create=tag)


@router.put("/{tag_id}", response_model=tag_schema.TagResponse)
async def update_tag(
    tag: tag_schema.UpdateTag,
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Update a tag.
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :param tag_id: Target tag id
    :param tag: Pydantic model that holds the new tag payload
    :return: The updated tag
    """
    return await tag_service.update_tag(
        db, user_id=current_user_id, tag_id=tag_id, tag_to_update=tag
    )


@router.delete("/{tag_id}", response_model=tag_schema.TagResponse)
async def delete_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Delete a tag.
    :param db: Async SQLAlchemy session
    :param current_user_id: User ID
    :param tag_id:  of the tag to delete
    :return: The deleted tag
    """
    return await tag_service.soft_delete_tag(db, user_id=current_user_id, tag_id=tag_id)
