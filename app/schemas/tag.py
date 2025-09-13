from typing import Optional, Annotated
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic.config import ConfigDict
from pydantic.types import StringConstraints as StrConst

"""Tag schemas

Schemas:
- BaseTag: title only (trimmed, validated)
- CreateTag: BaseTag (server supplies user_id)
- UpdateTag: partial update (title)
- TagResponse: public fields + timestamps (+ is_active)
"""

Title = Annotated[str, StrConst(min_length=2, max_length=64)]


class BaseTag(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: Annotated[Title, Field(description="Tag title")]

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


class CreateTag(BaseTag):
    """Payload to create a tag. Server sets user_id from auth context."""

    pass


class UpdateTag(BaseModel):
    """Partial update for a tag (rename)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: Optional[Title] = None

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
        if self.title is None:
            raise ValueError("At least one field must be provided for update")
        return self


class TagResponse(BaseTag):
    """Public tag view returned in responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TagLite(BaseModel):
    id: int
    title: str
    model_config = ConfigDict(from_attributes=True)
