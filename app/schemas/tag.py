from typing import Optional, Annotated
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from pydantic.types import StringConstraints as StrConst

"""Tag schemas

Schemas:
- BaseTag: `title` 
- CreateTag: BaseTag + user_id (owner)
- UpdateTag: partial update of `title`
- TagResponse: public fields + timestamps

Usage:
- Combine with NoteCreate/NoteUpdate via `tag_ids` for many-to-many management.
"""


class BaseTag(BaseModel):
    """
    BaseTag class as the parent class which contain the essential general attributes.
    """

    model_config = ConfigDict(extra="forbid")
    title: Annotated[
        str,
        StrConst(min_length=2, max_length=64),
        Field(description="This is the title."),
    ]


class CreateTag(BaseTag):
    """
    CreateTag class inherits the BaseTag. It adds the user id attribute which is essnsial
    for adding a new tag.
    """

    user_id: int = Field(description="Owner user ID (FK)")


class UpdateTag(BaseModel):
    """
    UpdateTag class contains the attributes that can be modified. It's main purpose is to
    enforce updating certain attributes not all of them.
    """

    model_config = ConfigDict(extra="forbid")
    title: Optional[
        Annotated[
            str,
            StrConst(min_length=2, max_length=100),
            Field(description="This is the title."),
        ]
    ] = None
    user_id: Optional[int] = None


class TagResponse(BaseTag):
    """
    TagResponse class inherits the BaseTag class. It adds three more attributes to display
    while returning the response of a certain request.
    """

    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    created_at: datetime
