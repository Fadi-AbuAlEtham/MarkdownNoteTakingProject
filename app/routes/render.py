from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Query
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.api.deps import get_current_user_id
from app.schemas.render import RenderOut, EtagOut
from app.services import render as render_service
from app.core.utils.http_cache import etag_matches, last_modified_header

router = APIRouter(prefix="/revisions", tags=["Rendered Content"])


def _negotiate(accept: str | None) -> str:
    accept = (accept or "*/*").lower()
    for t in ("application/json", "text/html", "text/plain", "text/markdown", "*/*"):
        if t in accept:
            return t if t != "*/*" else "text/html"
    return "text/html"


@router.get("/notes/{note_id}/revisions/{revision_id}/render")
async def render_revision(
    note_id: int,
    revision_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    try:
        data = await render_service.render_revision(
            db=db, user_id=current_user_id, note_id=note_id, revision_id=revision_id
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Revision not found")

    etag = data["etag"]
    if etag_matches(request.headers.get("if-none-match"), etag):
        return Response(
            status_code=status.HTTP_304_NOT_MODIFIED,
            headers={
                "ETag": etag,
                "Vary": "Accept",
            },
        )

    ctype = _negotiate(request.headers.get("accept"))
    headers = {
        "ETag": etag,
        "Vary": "Accept",
        "Cache-Control": "private, must-revalidate",
    }
    lm = last_modified_header(data["last_modified"])
    if lm:
        headers["Last-Modified"] = lm

    if ctype == "application/json":
        out = RenderOut(
            note_id=data["note_id"],
            revision_id=data["revision_id"],
            html=data["html"],
            etag=etag,
            last_modified=data["last_modified"],
        )
        return JSONResponse(content=jsonable_encoder(out), headers=headers)
    if ctype == "text/markdown":
        return Response(
            media_type="text/markdown; charset=utf-8",
            headers=headers,
            content=data["raw_md"],
        )
    if ctype == "text/plain":
        return Response(
            media_type="text/plain; charset=utf-8",
            headers=headers,
            content=data["html"],
        )
    # default: text/html
    return Response(
        media_type="text/html; charset=utf-8",
        headers=headers,
        content=data["html"],
    )


@router.get("/notes/{note_id}/revisions/{revision_id}/etag", response_model=EtagOut)
async def get_revision_etag(
    note_id: int,
    revision_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    try:
        data = await render_service.get_revision_etag(
            db=db, user_id=current_user_id, note_id=note_id, revision_id=revision_id
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Revision not found")

    # Also emit the ETag header for convenience
    headers = {"ETag": data["etag"], "Cache-Control": "private, must-revalidate"}
    return JSONResponse(content=jsonable_encoder(EtagOut(**data)), headers=headers)


def _strip_etag(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip()
    if s.startswith("W/"):  # treat weak tags as strong for this check
        s = s[2:]
    return s.strip('"')


@router.get("/notes/{note_id}/revisions/{revision_id}/render-by-etag")
async def render_revision_by_etag(
    note_id: int,
    revision_id: int,
    request: Request,
    etag_param: str = Query(..., alias="etag", description="ETag to compare against"),
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    try:
        data = await render_service.render_revision(
            db=db, user_id=current_user_id, note_id=note_id, revision_id=revision_id
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Revision not found")

    current_etag = data["etag"]  # e.g. '"55a47f..."'
    # If query ETag matches -> 304
    if _strip_etag(etag_param) == _strip_etag(current_etag):
        return Response(
            status_code=status.HTTP_304_NOT_MODIFIED,
            headers={
                "ETag": current_etag,
                "Vary": "Accept",
            },
        )

    # Otherwise, same rendering/negotiation as /render
    ctype = _negotiate(request.headers.get("accept"))
    headers = {
        "ETag": current_etag,
        "Vary": "Accept",
        "Cache-Control": "private, must-revalidate",
    }
    lm = last_modified_header(data["last_modified"])
    if lm:
        headers["Last-Modified"] = lm

    if ctype == "application/json":
        out = RenderOut(
            note_id=data["note_id"],
            revision_id=data["revision_id"],
            html=data["html"],
            etag=current_etag,
            last_modified=data["last_modified"],
        )
        return JSONResponse(content=jsonable_encoder(out), headers=headers)
    if ctype == "text/markdown":
        return Response(
            media_type="text/markdown; charset=utf-8",
            headers=headers,
            content=data["raw_md"],
        )
    if ctype == "text/plain":
        return Response(
            media_type="text/plain; charset=utf-8",
            headers=headers,
            content=data["html"],
        )
    return Response(
        media_type="text/html; charset=utf-8",
        headers=headers,
        content=data["html"],
    )
