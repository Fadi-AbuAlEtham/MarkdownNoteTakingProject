from __future__ import annotations
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict

Severity = Literal["info", "warning", "error"]

class AuditRequest(BaseModel):
    provider: Literal["languagetool"] = "languagetool"
    language: str = "en"

class IssueOut(BaseModel):
    id: int
    start: int
    length: int
    message: str
    rule_id: Optional[str] = None
    category: Optional[str] = None
    severity: Severity = "info"
    original: str
    replacements: List[str] = []
    is_applied: bool

    model_config = ConfigDict(from_attributes=True)

class AuditOut(BaseModel):
    audit_id: int
    revision_id: int
    provider: str
    language: str
    issue_count: int
    issues: List[IssueOut] = []

class ApplyFixesRequest(BaseModel):
    issue_ids: Optional[List[int]] = None
    min_severity: Severity = "info"
    strategy: Literal["first_suggestion"] = "first_suggestion"  
