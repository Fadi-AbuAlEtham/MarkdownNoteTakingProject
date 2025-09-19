from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.api.deps import get_current_user_id
from app.schemas import grammar as gs
from app.services import grammar as grammar_service
from app.services.grammar_provider import GrammarProvider
from app.core.config import GrammarSettings
from app.services.providers.languagetool import LanguageToolProvider

_settings = GrammarSettings()
_provider = LanguageToolProvider(
    base_url=_settings.BASE_URL,
    api_key=_settings.API_KEY,
    auth_header=_settings.AUTH_HEADER,
    level=_settings.LEVEL,
)


def get_provider() -> GrammarProvider:
    return _provider


router = APIRouter(prefix="/revisions", tags=["Grammar"])


@router.post(
    "/notes/{note_id}/revisions/{revision_id}/grammar/audit",
    response_model=gs.AuditOut,
    status_code=status.HTTP_200_OK,
)
async def run_grammar_audit(
    note_id: int,
    revision_id: int,
    body: gs.AuditRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
    provider: GrammarProvider = Depends(get_provider),
):
    try:
        return await grammar_service.run_audit(
            db=db,
            user_id=current_user_id,
            note_id=note_id,
            revision_id=revision_id,
            req=body,
            provider=provider,
        )
    except Exception as e:
        # Surface provider errors as 502s (bad upstream)
        raise HTTPException(status_code=502, detail=f"Grammar provider error: {e}")


@router.post(
    "/notes/{note_id}/revisions/{revision_id}/grammar/apply-fixes",
    response_model=gs.ApplyFixesOut,
    status_code=status.HTTP_200_OK,
)
async def apply_fixes(
    note_id: int,
    revision_id: int,
    body: gs.ApplyFixesRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    return await grammar_service.apply_fixes(
        db=db,
        user_id=current_user_id,
        note_id=note_id,
        revision_id=revision_id,
        body=body,
    )
