from sqlalchemy.orm import selectinload

from app.models import folder as models


def to_response_dict(res_type, obj) -> dict:
    """
    Convert response to dict.
    :param res_type: response type
    :param obj: Response to convert.
    :return: Response dict.
    """
    return res_type.model_validate(obj, from_attributes=True).model_dump()


def folder_graph_options():
    return (
        selectinload(models.Folder.parent).load_only(
            models.Folder.id, models.Folder.title
        ),
        selectinload(models.Folder.children).load_only(
            models.Folder.id, models.Folder.title
        ),
    )
