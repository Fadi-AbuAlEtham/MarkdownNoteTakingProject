from __future__ import annotations

from typing import Protocol, TypedDict


class SummarizeResult(TypedDict, total=False):
    summary: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class SummarizeProvider(Protocol):
    async def summarize(
        self,
        text: str,
        *,
        language: str,
        style: str,
        max_tokens: int | None = None,
    ) -> SummarizeResult: ...
