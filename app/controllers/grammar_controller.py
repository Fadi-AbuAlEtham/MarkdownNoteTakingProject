from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.api.deps import get_current_user_id
from app.schemas import grammar as gs
from app.services import grammar_service
from app.services.grammar_provider import GrammarProvider
from app.core.config import GrammarSettings
from app.services.providers.languagetool import LanguageToolProvider

_settings = GrammarSettings()
provider = LanguageToolProvider(
    base_url=_settings.LT_BASE_URL,
    api_key=_settings.LT_API_KEY,
    auth_header=_settings.LT_AUTH_HEADER,
    level=_settings.LT_LEVEL,
)

router = APIRouter(prefix="/revisions", tags=["Grammar"])

# Wire a provider (swap with real implementation)
class DummyProvider:
    async def analyze(self, text: str, language: str = "en"):
        # tiny demo: flag ' teh ' -> ' the '
        issues = []
        idx = text.find(" teh ")
        if idx != -1:
            issues.append({
                "start": idx+1,
                "length": 3,
                "message": "Did you mean “the”?",
                "rule_id": "DEMO_TEH",
                "category": "spelling",
                "severity": "warning",
                "original": "teh",
                "replacements": ["the"],
            })
        return issues

provider: GrammarProvider = DummyProvider()

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
):
    return await grammar_service.run_audit(
        db=db,
        user_id=current_user_id,
        note_id=note_id,
        revision_id=revision_id,
        req=body,
        provider=provider,
    )

@router.post(
    "/notes/{note_id}/revisions/{revision_id}/grammar/apply-fixes",
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
