from typing import List
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.expression import select

from app.repositories import note as note_repo, folder as folder_repo
from app.services.summarize_provider import SummarizeProvider
from app.core.config import SummarizeSettings
from ..models import note as note_models

_settings = SummarizeSettings()


def _truncate(s: str, limit: int) -> str:
    if len(s) <= limit:
        return s
    return s[:limit]


async def summarize_note(db, user_id: int, note_id: int, req, provider):
    note = await db.scalar(
        select(note_models.Note)
        .options(selectinload(note_models.Note.tags))
        .where(
            note_models.Note.id == note_id,
            note_models.Note.user_id == user_id,
            note_models.Note.deleted_at.is_(None),
        )
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Build a better source text for the LLM
    title_block = f"# {note.title}".strip()
    body_block = (note.content_md or "").strip()
    tags_str = (
        ", ".join(
            getattr(t, "name", str(getattr(t, "id", ""))) for t in (note.tags or [])
        )
        or "none"
    )
    meta_block = (
        "-----\n"
        "Meta:\n"
        f"- Public: {bool(note.is_public)}\n"
        f"- Folder ID: {note.folder_id or 'none'}\n"
        f"- Tags: {tags_str}\n"
    )

    source_text = "\n\n".join([title_block, body_block, meta_block]).strip()

    # Let the request choose style/language if present; set sane defaults
    language = getattr(req, "language", "en") or "en"
    style = getattr(req, "style", "title_and_bullets") or "title_and_bullets"
    max_tokens = getattr(req, "max_tokens", None)

    return await provider.summarize(
        source_text, language=language, style=style, max_tokens=max_tokens
    )


async def summarize_folder(
    db: AsyncSession,
    user_id: int,
    folder_id: int,
    req,
    provider: SummarizeProvider,
):
    folder = await folder_repo.get_folder_by_id_and_user(
        db=db, user_id=user_id, folder_id=folder_id
    )
    if not folder:
        raise ValueError("Folder not found")

    notes = await note_repo.get_active_notes_in_folder(
        db=db, user_id=user_id, folder_id=folder_id
    )
    if not notes:
        raise ValueError("Folder has no active notes")

    # Concatenate titles + short excerpts to stay within limits
    pieces: List[str] = []
    remaining = _settings.MAX_CHARS_PER_CALL
    for n in notes:
        title = (n.title or "").strip()
        body = (n.content_md or "").strip()
        snippet = body[:1000]  # short excerpt per note
        chunk = f"# {title}\n\n{snippet}\n\n"
        if len(chunk) <= remaining:
            pieces.append(chunk)
            remaining -= len(chunk)
        else:
            break

    merged = "".join(pieces)
    if not merged:
        merged = (notes[0].content_md or "")[: _settings.MAX_CHARS_PER_CALL]

    res = await provider.summarize(
        merged,
        language=req.language or _settings.LANGUAGE,
        style=req.style,
        max_tokens=req.max_tokens,
    )
    return {
        "scope": "folder",
        "scope_id": folder_id,
        **res,
    }
