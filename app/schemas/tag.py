from typing import Optional, Annotated
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from pydantic.types import StringConstraints as StrConst


class BaseTag(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Annotated[
        str,
        StrConst(min_length=2, max_length=100),
        Field(description="This is the title."),
    ]


class CreateTag(BaseTag):
    user_id: int = Field(description="Owner user ID (FK)")


class UpdateTag(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Optional[
        Annotated[
            str,
            StrConst(min_length=2, max_length=100),
            Field(description="This is the title."),
        ]
    ] = None
    user_id: Optional[int] = None


class TagResponse(BaseTag):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    created_at: datetime
