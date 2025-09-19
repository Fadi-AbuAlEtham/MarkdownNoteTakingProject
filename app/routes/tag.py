from typing import Annotated, List

from fastapi import APIRouter, Depends, status
from fastapi.params import Path

from app.api.deps import get_tag_service
from app.schemas import tag as tag_schema, note_tag as note_tag_schema
from app.services.tag import TagService

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get(
    "/{tag_id}",
    response_model=tag_schema.TagResponse,
    status_code=status.HTTP_200_OK,
)
async def get_tag_by_id(
    tag_id: Annotated[int, Path(title="The ID of the tag to get", gt=0)],
    tag_service: TagService = Depends(get_tag_service),
):
    """
    Get a tag by ID.
    :param tag_id: Target tag ID.
    :param tag_service: Tag service to use.
    :return: The target tag.
    """
    return await tag_service.get_tag_by_id_and_user(tag_id=tag_id)


@router.get(
    "/",
    response_model=List[tag_schema.TagResponse],
    status_code=status.HTTP_200_OK,
)
async def get_all_active_tags(
    skip: int = 0,
    limit: int = 100,
    tag_service: TagService = Depends(get_tag_service),
):
    """
    Get all active tags.
    :param skip: Starting offset
    :param limit: ending offset
    :return: List of all active tags for the current user
    """
    return await tag_service.get_all_active_tags(skip, limit)


# @router.get(
#     "/{tag_id}/notes",
#     response_model=note_tag_schema.TagWithNotesResponse,
#     status_code=status.HTTP_200_OK,
# )
# async def get_notes_for_tag(
#     tag_id: int,
#     tag_service: TagService = Depends(get_tag_service),
# ):
#     return await tag_service.get_active_notes_for_tag(
#         db, user_id=current_user_id, tag_id=tag_id
#     )


@router.post(
    "/",
    response_model=tag_schema.TagResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tag(
    tag: tag_schema.CreateTag,
    tag_service: TagService = Depends(get_tag_service),
):
    """
    Create a new tag.
    :param tag: Pydantic model that holds the new tag payload
    :return: The newly created tag
    """
    return await tag_service.create_tag(tag_to_create=tag)


@router.put("/{tag_id}", response_model=tag_schema.TagResponse)
async def update_tag(
    tag: tag_schema.UpdateTag,
    tag_id: int,
    tag_service: TagService = Depends(get_tag_service),
):
    """
    Update a tag.
    :param tag_id: Target tag id
    :param tag: Pydantic model that holds the new tag payload
    :return: The updated tag
    """
    return await tag_service.update_tag(tag_id=tag_id, tag_to_update=tag)


@router.delete("/{tag_id}", response_model=tag_schema.TagResponse)
async def delete_tag(
    tag_id: int,
    tag_service: TagService = Depends(get_tag_service),
):
    """
    Delete a tag.
    :param tag_id:  of the tag to delete
    :return: The deleted tag
    """
    return await tag_service.soft_delete_tag(tag_id=tag_id)
