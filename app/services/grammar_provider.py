from __future__ import annotations

from typing import Protocol, List, TypedDict

class IssueIn(TypedDict):
    start: int
    length: int
    message: str
    rule_id: str | None
    category: str | None
    severity: str              
    original: str
    replacements: List[str]

class GrammarProvider(Protocol):
    async def analyze(self, text: str, language: str = "en") -> List[IssueIn]: ...
