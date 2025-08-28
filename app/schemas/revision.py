from typing import Optional, Annotated
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator
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

Title = Annotated[str, StrConst(min_length=2, max_length=200)]
Markdown = Annotated[str, StrConst(min_length=1)]


class BaseRevision(BaseModel):
    """
    BaseRevision class acts as the parent class which contain the essential general attributes.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    version: int = Field(description="Monotonic version number (>= 1)")
    title: Annotated[Title, Field(description="Revision title")]
    content_md: Annotated[Markdown, Field(description="Markdown content")]

    @field_validator("version")
    def version_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("version must be >= 1")
        return v

    @field_validator("title", mode="before")
    def clean_title(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("title cannot be empty")
        return s


class CreateRevision(BaseRevision):
    """
    CreateRevision class inherits BaseRevision. It adds two more attributes: note id
    and created by, which are required when creating a new revision.
    """

    note_id: int = Field(description="Note ID (FK)")


class UpdateRevision(BaseModel):
    """
    UpdateRevision class contains the attributes that can be modified and updated. This class
    enforces updating certain attributes not all of them.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: Optional[Title] = None
    content_md: Optional[Markdown] = None

    @field_validator("title", mode="before")
    def clean_title(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        s = v.strip()
        if not s:
            raise ValueError("title cannot be empty")
        return s

    @model_validator(mode="after")
    def at_least_one_field(self):
        if self.title is None and self.content_md is None:
            raise ValueError("At least one field must be provided for update")
        return self


class RevisionResponse(BaseRevision):
    """
    RevisionResponse class inherits the BaseRevision class. It adds more attributes that should be
    displayed while returning the response of a certain request.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    note_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
