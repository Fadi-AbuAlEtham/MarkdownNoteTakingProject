from typing import Optional, Annotated
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from pydantic.types import StringConstraints as StrConst


class BaseNote(BaseModel):
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
    user_id: int = Field(description="Owner user ID (FK)")
    folder_id: Optional[int] = None


class UpdateNote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: Optional[int] = None
    folder_id: Optional[int] = None
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
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    folder_id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]
