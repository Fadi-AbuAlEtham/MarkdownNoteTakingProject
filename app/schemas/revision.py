from typing import Optional, Annotated, List
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
    is_public: bool = Field(description="Whether the revision is public")
    folder_id: int = Field(description="Folder ID", gt=0)
    tag_ids: List[int] = Field(default_factory=list, description="Tag IDs")

    @field_validator("version")
    def version_positive(cls, v: int) -> int:
        """
            Positive version number validation
        :param v: Raw version number value.
        :return: The validated version number.
        """
        if v < 1:
            raise ValueError("version must be >= 1")
        return v

    @field_validator("title", mode="before")
    def clean_title(cls, v: str) -> str:
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


class CreateRevision(BaseRevision):
    """
    CreateRevision class inherits BaseRevision. It adds one more attributes: note id,
    which is required when creating a new revision.
    """

    note_id: int = Field(description="Note ID (FK)")


class UpdateRevision(BaseModel):
    """
    UpdateRevision class contains the attributes that can be modified and updated. This class
    enforces updating certain attributes, not all of them.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: Optional[Title] = None
    content_md: Optional[Markdown] = None
    is_public: Optional[bool] = None
    folder_id: Optional[int] = None

    @field_validator("title", mode="before")
    def clean_title(cls, v: Optional[str]) -> Optional[str]:
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
            self.title is None
            and self.content_md is None
            and self.is_public is None
            and self.folder_id is None
            and self.tag_ids is None
        ):
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
    tags: list[int] = []

    @field_validator("tags", mode="before")
    def tags_to_ids(cls, v):
        if v is None:
            return []
        return [getattr(t, "id", t) for t in v]
