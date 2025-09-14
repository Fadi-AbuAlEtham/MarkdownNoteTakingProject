import hashlib
from datetime import datetime
from email.utils import format_datetime


def compute_etag(payload: str, updated_at: datetime | None = None) -> str:
    src = (payload + "|" + (updated_at.isoformat() if updated_at else "")).encode(
        "utf-8"
    )
    return '"' + hashlib.sha256(src).hexdigest() + '"'


def etag_matches(if_none_match_header: str | None, etag: str) -> bool:
    if not if_none_match_header:
        return False
    candidates = [t.strip() for t in if_none_match_header.split(",")]
    return etag in candidates or "*" in candidates


def last_modified_header(dt: datetime | None) -> str | None:
    return format_datetime(dt) if dt else None
