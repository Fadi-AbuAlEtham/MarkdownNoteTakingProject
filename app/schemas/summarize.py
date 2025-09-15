from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Optional

Style = Literal["bullets", "paragraph", "tldr", "title_and_bullets"]


class SummarizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    style: Style = Field(default="paragraph")
    language: str = Field(default="en", description="Output language (e.g., en, ar)")
    max_tokens: Optional[int] = Field(default=None, ge=64, le=2048)


class SummarizeOut(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    scope: Literal["note", "folder"]
    scope_id: int
    summary: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
