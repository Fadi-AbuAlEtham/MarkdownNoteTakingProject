from typing import Optional, Annotated
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from pydantic.types import StringConstraints as StrConst

"""Note schemas

Write:
- CreateNote: title, content_md, is_public (default False),
  user_id (required), folder_id (optional), tag_ids (list[int], optional).

Update:
- UpdateNote: partial fields;

Read:
- NoteResponse: exposes note fields, timestamps, and deleted_at (optional)..

Notes:
- Apply business rules (e.g., max title length, folder existence, tag id validation)
  in the service layer before persisting.
"""

class BaseNote(BaseModel):
    """
    BaseNote class acts as the parent class which contain all the general essential attributes.
    """
    model_config = ConfigDict(extra="forbid")
    title: Annotated[
        str,
        StrConst(min_length=2, max_length=180),
        Field(description="This is the title."),
    ]
    content_md: Annotated[
        str,
        StrConst(min_length=3),
        Field(description="This is the version's content modified"),
    ]
    is_public: bool = Field(
        default=False,
        description="This is to indicate whether the note is public or not.",
    )


class CreateNote(BaseNote):
    """
    CreateNote class inherits the BaseNote class. It adds three more attributes which are
    required when creating a new note.
    """
    user_id: int = Field(description="Owner user ID (FK)")
    folder_id: Optional[int] = None
    tag_id: Optional[int] = None


class UpdateNote(BaseModel):
    """
    UpdateNote class contains the attributes that can be modified and updated. This class
    enforces updating certain attributes not all of them.
    """
    model_config = ConfigDict(extra="forbid")
    user_id: Optional[int] = None
    folder_id: Optional[int] = None
    tag_id: Optional[int] = None
    title: Optional[
        Annotated[
            str,
            StrConst(min_length=2, max_length=100),
        ]
    ] = None
    content_md: Optional[
        Annotated[
            str,
            StrConst(min_length=3),
        ]
    ]
    is_public: Optional[bool] = None


class NoteResponse(BaseNote):
    """
    NoteResponse class inherits the BaseNote class. It adds more attributes that should be
    displayed while returning the response of a certain request.
    """
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    folder_id: Optional[int]
    tag_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]
