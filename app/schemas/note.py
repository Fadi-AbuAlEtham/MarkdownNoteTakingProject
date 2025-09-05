from typing import Optional, Annotated
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic.config import ConfigDict
from pydantic.types import StringConstraints as StrConst

"""Note schemas

Write:
- CreateNote: title, content_md, is_public (default False),
  folder_id (optional).

Update:
- UpdateNote: partial fields;

Read:
- NoteResponse: exposes note fields, timestamps, and deleted_at (optional)..

Notes:
- Apply business rules (e.g., max title length, folder existence, tag id validation)
  in the service layer before persisting.
"""

Title = Annotated[str, StrConst(min_length=2, max_length=200)]
Markdown = Annotated[str, StrConst(min_length=1)]


class BaseNote(BaseModel):
    """
    BaseNote class acts as the parent class which contain all the general essential attributes.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: Annotated[Title, Field(description="Note title (case-insensitive)")]
    content_md: Annotated[Markdown, Field(description="Markdown content")]
    is_public: bool = Field(default=False, description="Whether the note is public.")

    @field_validator("title", mode="before")
    def normalize_title(self, v: str) -> str:
        """
        Normalize title **before** validation.

        - Trims leading/trailing whitespace.
        - Passes through `None` or non-str values unchanged.

        Args:
            v: Raw title value.

        Returns:
            The normalized title, or `None`.
        """
        s = v.strip()
        if not s:
            raise ValueError("title cannot be empty")
        return s


class CreateNote(BaseNote):
    """
    CreateNote class inherits the BaseNote class. It one more attribute which is
    required when creating a new note.
    """

    folder_id: Optional[int] = Field(default=None, description="Folder ID (FK)")


class UpdateNote(BaseModel):
    """
    UpdateNote class contains the attributes that can be modified and updated. This class
    enforces updating certain attributes, not all of them.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    folder_id: Optional[int] = None
    title: Optional[Title] = None
    content_md: Optional[Markdown] = None
    is_public: Optional[bool] = None

    @field_validator("title", mode="before")
    def normalize_title(self, v: Optional[str]) -> Optional[str]:
        """
        Normalize title **before** validation.

        - Trims leading/trailing whitespace.
        - Passes through `None` or non-str values unchanged.

        Args:
            v: Raw title value.

        Returns:
            The normalized title, or `None`.
        """
        if v is None:
            return v
        s = v.strip()
        if not s:
            raise ValueError("title cannot be empty")
        return s

    @model_validator(mode="after")
    def at_least_one_field(self):
        """
        Enforce that at least one updatable field is provided.

        Checks fields, if all are `None`, raises a `ValueError`.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If no updatable fields are provided.
        """
        if (
            self.folder_id is None
            and self.title is None
            and self.content_md is None
            and self.is_public is None
        ):
            raise ValueError("At least one field must be provided for update")
        return self


class NoteResponse(BaseNote):
    """
    NoteResponse class inherits the BaseNote class. It adds more attributes that should be
    displayed while returning the response of a certain request.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    folder_id: Optional[int]
    version: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]
