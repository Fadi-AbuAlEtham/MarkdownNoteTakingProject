from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import revision as revision_repo
from app.core.utils.markdown_render import render_sanitized_html
from app.core.utils.http_cache import compute_etag


async def render_revision(
    db: AsyncSession, user_id: int, note_id: int, revision_id: int
) -> dict:
    rev = await revision_repo.get_revision_by_id_and_user_note(
        db, revision_id=revision_id, user_id=user_id, note_id=note_id
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


async def get_revision_etag(
    db: AsyncSession, user_id: int, note_id: int, revision_id: int
) -> dict:
    rev = await revision_repo.get_revision_by_id_and_user_note(
        db, revision_id=revision_id, user_id=user_id, note_id=note_id
    )
    if not rev:
        raise ValueError("Revision not found")

    # IMPORTANT: compute from the same sanitized HTML used by /render
    html = render_sanitized_html(rev.content_md or "")
    etag = compute_etag(html, getattr(rev, "updated_at", None))
    return {
        "note_id": note_id,
        "revision_id": revision_id,
        "etag": etag,
        "last_modified": getattr(rev, "updated_at", None),
    }
