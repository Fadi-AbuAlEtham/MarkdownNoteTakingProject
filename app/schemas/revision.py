from typing import Optional, Annotated
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from pydantic.types import StringConstraints as StrConst

"""NoteRevision schemas

Schemas:
- BaseRevision: title, content_md
- CreateRevision: BaseRevision + note_id (required), version (int), created_by (optional)
- RevisionResponse: public fields + created_at

Notes:
- Service layer should enforce that `version` increments per note and is immutable post-create.
"""


class BaseRevision(BaseModel):
    """
    BaseRevision class acts as the parent class which contain the essential general attributes.
    """

    model_config = ConfigDict(extra="forbid")
    version: str = Field(description="This is the version")
    title: Annotated[
        str,
        StrConst(min_length=2, max_length=100),
        Field(description="This is the title."),
    ]
    content_md: Annotated[
        str,
        StrConst(min_length=3),
        Field(description="This is the version's content modified"),
    ]


class CreateRevision(BaseRevision):
    """
    CreateRevision class inherits BaseRevision. It adds two more attributes: note id
    and created by, which are required when creating a new revision.
    """

    note_id: int = Field(description="Note ID (FK)")
    created_by: int = Field(description="Owner user ID (FK)")


class UpdateRevision(BaseModel):
    """
    UpdateRevision class contains the attributes that can be modified and updated. This class
    enforces updating certain attributes not all of them.
    """

    model_config = ConfigDict(extra="forbid")
    note_id: Optional[int] = None
    created_by: Optional[int] = None
    version: Optional[str] = None
    title: Optional[Annotated[str, StrConst(min_length=2, max_length=100)]] = None
    content_md: Optional[
        Annotated[
            str,
            StrConst(min_length=3),
        ]
    ] = None


class RevisionResponse(BaseRevision):
    """
    RevisionResponse class inherits the BaseRevision class. It adds more attributes that should be
    displayed while returning the response of a certain request.
    """

    model_config = ConfigDict(from_attributes=True)
    id: int
    note_id: int
    created_by: int
    created_at: datetime
