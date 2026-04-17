from fastapi import APIRouter, Depends, status

from app.api.deps import get_grammar_service
from app.schemas import grammar as gs
from app.services.grammar import GrammarService


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
    grammar_service: GrammarService = Depends(get_grammar_service),
):
    return await grammar_service.run_audit(
        note_id=note_id, revision_id=revision_id, req=body
    )


@router.post(
    "/notes/{note_id}/revisions/{revision_id}/grammar/apply-fixes",
    response_model=gs.ApplyFixesOut,
    status_code=status.HTTP_200_OK,
)
async def apply_fixes(
    note_id: int,
    revision_id: int,
    body: gs.ApplyFixesRequest,
    grammar_service: GrammarService = Depends(get_grammar_service),
):
    return await grammar_service.apply_fixes(
        note_id=note_id, revision_id=revision_id, body=body
    )
