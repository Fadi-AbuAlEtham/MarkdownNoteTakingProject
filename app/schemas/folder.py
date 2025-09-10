from typing import Optional, Annotated, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic.config import ConfigDict
from pydantic.types import StringConstraints as StrConst

"""Folder schemas

Design:
- Write by IDs (`user_id`, optional `parent_id`) to keep API simple.
- Read responses may include small nested objects (`parent`, `children`) to avoid heavy recursion.

Schemas:
- BaseFolder: title + status ("active"/"archived")
- FolderCreate: BaseFolder + user_id + optional parent_id
- FolderUpdate: partial update, allows moving by changing parent_id
- FolderShort: minimal view for nested embedding
- FolderResponse: full read model including ids, timestamps, parent/children

"""


# General constraints on title and file status
Title = Annotated[str, StrConst(min_length=1, max_length=120)]
FolderStatus = Literal["active", "archived"]


class BaseFolder(BaseModel):
    """
    BaseFolder class acts as the parent class which contain the essential general attributes.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: Annotated[Title, Field(description="Folder title")]

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


class FolderCreate(BaseFolder):
    """
    FolderCreate class inherits the BaseFolder class. It adds two more attributes which are the
    user id and parent id. These attributes are essential for creating a new folder operation.
    """

    parent_id: Optional[int] = Field(
        default=None, ge=0, description="Parent folder ID; use 0 for root"
    )

    @field_validator("parent_id", mode="before")
    def zero_means_root(cls, v):
        return None if v in (0, "0", 0.0) else v


class FolderUpdate(BaseModel):
    """
    FolderUpdate class contains the attributes that can be modified and updated. This class
    enforces updating certain attributes not all of them.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: Optional[Title] = None
    status: Optional[FolderStatus] = None
    parent_id: Optional[int] = Field(
        default=None, ge=0, description="Parent folder ID; use 0 for root"
    )

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

    @field_validator("parent_id", mode="before")
    def zero_means_root(cls, v):
        return None if v in (0, "0", 0.0) else v

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
        if not any(
            getattr(self, f) is not None for f in ("title", "status", "parent_id")
        ):
            raise ValueError("At least one field must be provided for update")
        return self


class FolderShort(BaseModel):
    """
    FolderShort class contains the id and title of the folder which is used to display
    only these two attributes while showing certain things such as parent folders.
    """

    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str


class FolderResponse(BaseFolder):
    """
    FolderResponse class inherits the BaseFolder class. It adds more attributes that should be
    displayed while returning the response of a certain request.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    parent_id: Optional[int] = None
    status: FolderStatus = "active"
    created_at: datetime
    updated_at: datetime
    is_active: bool
    parent: Optional[FolderShort] = None
    children: List[FolderShort] = Field(default_factory=list)
