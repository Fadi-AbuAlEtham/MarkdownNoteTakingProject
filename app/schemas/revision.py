from typing import Optional, Annotated
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from pydantic.types import StringConstraints as StrConst


class BaseRevision(BaseModel):
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
    note_id: int = Field(description="Note ID (FK)")
    created_by: int = Field(description="Owner user ID (FK)")


class UpdateRevision(BaseModel):
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
    model_config = ConfigDict(from_attributes=True)
    id: int
    note_id: int
    created_by: int
    created_at: datetime
