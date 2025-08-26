from typing import Optional, Annotated
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from pydantic.types import StringConstraints as StrConst

"""Issue schemas

Schemas:
- BaseIssue: rule (≤ 100 chars), description, suggestion, start_offset, end_offset
- CreateIssue: BaseIssue + note_id (required), revision_id (optional)
- ResponseIssue: public fields + created_at

Offsets:
- Offsets reference character positions in the note/revision text (0-based, inclusive start, exclusive end).
- Validate bounds in the service layer against the target content length.
"""


class BaseIssue(BaseModel):
    """
    BaseIssue class acts as the parent class which contain the essential general attributes.
    """

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
    """
    CreateIssue class inherits the BaseIssue class. It adds two specific attributes
    which are the note id and revision id which are required when creating a new issue.
    """

    note_id: int = Field(description="Note ID (FK)")
    revision_id: int = Field(description="Revision ID (FK)")


class UpdateIssue(BaseModel):
    """
    UpdateIssue class contains the attributes that can be modified an updated. This class
    enforces updating certain attributes not all of them.
    """

    model_config = ConfigDict(extra="forbid")
    note_id: Optional[int] = None
    revision_id: Optional[int] = None
    rule: Optional[Annotated[str, StrConst(min_length=3, max_length=100)]] = None
    description: Optional[Annotated[str, StrConst(min_length=3)]] = None
    suggestion: Optional[Annotated[str, StrConst(min_length=3)]] = None
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None


class ResponseIssue(BaseIssue):
    """
    ResponseIssue class inherits the BaseIssue class. It adds more attributes that should be
    displayed while returning the response of a certain request.
    """

    model_config = ConfigDict(from_attributes=True)
    id: int
    note_id: int
    revision_id: int
    created_at: datetime
