from typing import Optional, Annotated, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from pydantic.types import StringConstraints as S

Title = Annotated[str, S(min_length=1, max_length=120)]
FolderStatus = Literal["active", "archived"]


class BaseFolder(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Annotated[Title, Field(description="This is the title.")]
    status: Annotated[FolderStatus, Field(description="Folder status")] = "active"


class FolderCreate(BaseFolder):
    user_id: int = Field(description="Owner user ID (FK)")
    parent_id: Optional[int] = Field(
        default=None, description="Parent folder ID (nullable)"
    )


class FolderUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Optional[Title] = None
    status: Optional[FolderStatus] = None
    parent_id: Optional[int] = None


class FolderShort(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str


class FolderResponse(BaseFolder):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    parent_id: Optional[int] = None
    created_at: datetime
    parent: Optional[FolderShort] = None
    children: List[FolderShort] = Field(default_factory=list)
