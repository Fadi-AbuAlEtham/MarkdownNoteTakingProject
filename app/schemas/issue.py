from typing import Optional, Annotated
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from pydantic.types import StringConstraints as StrConst


class BaseIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rule: Annotated[
        str,
        StrConst(min_length=3, max_length=100),
        Field(description="This is the issue rule."),
    ]
    description: Annotated[
        str, StrConst(min_length=3), Field(description="This is the issue description")
    ]
    suggestion: Annotated[
        str, StrConst(min_length=3), Field(description="This is the issue suggestion")
    ]
    start_offset: int = Field(description="This is the issue start offset.")
    end_offset: int = Field(description="This is the issue end offset.")


class CreateIssue(BaseIssue):
    note_id: int = Field(description="Note ID (FK)")
    revision_id: int = Field(description="Revision ID (FK)")


class UpdateIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note_id: Optional[int] = None
    revision_id: Optional[int] = None
    rule: Optional[Annotated[str, StrConst(min_length=3, max_length=100)]] = None
    description: Optional[Annotated[str, StrConst(min_length=3)]] = None
    suggestion: Optional[Annotated[str, StrConst(min_length=3)]] = None
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None


class ResponseIssue(BaseIssue):
    model_config = ConfigDict(from_attributes=True)
    id: int
    note_id: int
    revision_id: int
    created_at: datetime
