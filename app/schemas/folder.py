from typing import Optional, Annotated, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field
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

    model_config = ConfigDict(extra="forbid")
    title: Annotated[Title, Field(description="This is the title.")]
    status: Annotated[FolderStatus, Field(description="Folder status")] = "active"


class FolderCreate(BaseFolder):
    """
    FolderCreate class inherits the BaseFolder class. It adds two more attributes which are the
    user id and parent id. These attributes are essential for creating a new folder operation.
    """

    user_id: int = Field(description="Owner user ID (FK)")
    parent_id: Optional[int] = Field(
        default=None, description="Parent folder ID (nullable)"
    )


class FolderUpdate(BaseModel):
    """
    FolderUpdate class contains the attributes that can be modified an updated. This class
    enforces updating certain attributes not all of them.
    """

    model_config = ConfigDict(extra="forbid")
    title: Optional[Title] = None
    status: Optional[FolderStatus] = None
    parent_id: Optional[int] = None
    user_id: Optional[int] = None


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
    created_at: datetime
    parent: Optional[FolderShort] = None
    children: List[FolderShort] = Field(default_factory=list)
