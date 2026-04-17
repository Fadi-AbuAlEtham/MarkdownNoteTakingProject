from app.core.utils.http_cache import compute_etag
from app.core.utils.markdown_render import render_sanitized_html
from app.repositories.revision import RevisionRepository


class RenderService:
    def __init__(self, revision_repo: RevisionRepository, user_id: int):
        self.revision_repo = revision_repo
        self.user_id = user_id

    async def render_revision(self, note_id: int, revision_id: int) -> dict:
        rev = await self.revision_repo.get_revision_by_id_and_user_note(
            revision_id=revision_id, user_id=self.user_id, note_id=note_id
        )
        if not rev:
            raise ValueError("Revision not found")

        html = render_sanitized_html(rev.content_md or "")
        etag = compute_etag(html, getattr(rev, "updated_at", None))
        return {
            "note_id": note_id,
            "revision_id": revision_id,
            "html": html,
            "raw_md": rev.content_md or "",
            "etag": etag,
            "last_modified": getattr(rev, "updated_at", None),
        }

    async def get_revision_etag(self, note_id: int, revision_id: int) -> dict:
        rev = await self.revision_repo.get_revision_by_id_and_user_note(
            revision_id=revision_id, user_id=self.user_id, note_id=note_id
        )
        if not rev:
            raise ValueError("Revision not found")

        html = render_sanitized_html(rev.content_md or "")
        etag = compute_etag(html, getattr(rev, "updated_at", None))
        return {
            "note_id": note_id,
            "revision_id": revision_id,
            "etag": etag,
            "last_modified": getattr(rev, "updated_at", None),
        }
