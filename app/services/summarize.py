from typing import List

from fastapi import HTTPException, status

from app.core.config import SummarizeSettings
from app.repositories.folder import FolderRepository
from app.repositories.note import NoteRepository
from app.services.summarize_provider import SummarizeProvider

_settings = SummarizeSettings()


class SummarizeService:
    def __init__(
        self,
        note_repo: NoteRepository,
        folder_repo: FolderRepository,
        provider: SummarizeProvider,
        user_id: int,
    ):
        self.note_repo = note_repo
        self.folder_repo = folder_repo
        self.provider = provider
        self.user_id = user_id

    async def summarize_note(self, note_id: int, req) -> dict:
        note = await self.note_repo.get_note_with_tags_by_id_user(note_id, self.user_id)
        if not note:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

        title_block = f"# {note.title}".strip()
        body_block = (note.content_md or "").strip()
        tags_str = (
            ", ".join(getattr(t, "title", str(getattr(t, "id", ""))) for t in (note.tags or []))
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
        language = getattr(req, "language", "en") or "en"
        style = getattr(req, "style", "title_and_bullets") or "title_and_bullets"
        max_tokens = getattr(req, "max_tokens", None)

        try:
            res = await self.provider.summarize(
                source_text, language=language, style=style, max_tokens=max_tokens
            )
        except Exception as exc:
            msg = str(exc)
            status_code = (
                status.HTTP_500_INTERNAL_SERVER_ERROR
                if "missing" in msg.lower() or "not available" in msg.lower()
                else status.HTTP_502_BAD_GATEWAY
            )
            raise HTTPException(status_code=status_code, detail=msg)
        return {
            "scope": "note",
            "scope_id": note_id,
            **res,
        }

    async def summarize_folder(self, folder_id: int, req) -> dict:
        folder = await self.folder_repo.get_folder_by_id_and_user(
            user_id=self.user_id, folder_id=folder_id
        )
        if not folder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")

        notes = await self.note_repo.get_active_notes_in_folder(
            user_id=self.user_id, folder_id=folder_id
        )
        if not notes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder has no active notes",
            )

        pieces: List[str] = []
        remaining = _settings.MAX_CHARS_PER_CALL
        for note in notes:
            title = (note.title or "").strip()
            body = (note.content_md or "").strip()
            snippet = body[:1000]
            chunk = f"# {title}\n\n{snippet}\n\n"
            if len(chunk) <= remaining:
                pieces.append(chunk)
                remaining -= len(chunk)
            else:
                break

        merged = "".join(pieces)
        if not merged:
            merged = (notes[0].content_md or "")[: _settings.MAX_CHARS_PER_CALL]

        try:
            res = await self.provider.summarize(
                merged,
                language=req.language or _settings.LANGUAGE,
                style=req.style,
                max_tokens=req.max_tokens,
            )
        except Exception as exc:
            msg = str(exc)
            status_code = (
                status.HTTP_500_INTERNAL_SERVER_ERROR
                if "missing" in msg.lower() or "not available" in msg.lower()
                else status.HTTP_502_BAD_GATEWAY
            )
            raise HTTPException(status_code=status_code, detail=msg)
        return {
            "scope": "folder",
            "scope_id": folder_id,
            **res,
        }
