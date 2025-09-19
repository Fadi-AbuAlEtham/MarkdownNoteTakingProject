from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.api.deps import get_current_user_id
from app.schemas.summarize import SummarizeRequest, SummarizeOut
from app.services import summarize as summarize_service
from app.services.summarize_provider import SummarizeProvider
from app.services.providers.gemini_summarizer import GeminiSummarizer
from app.schemas import summarize as gs

router = APIRouter(prefix="/summarize", tags=["Summarization"])

_provider: SummarizeProvider = GeminiSummarizer()


def get_provider() -> SummarizeProvider:
    return _provider


@router.post("/summarize/notes/{note_id}", response_model=gs.SummarizeOut)
async def summarize_note(
    note_id: int,
    body: gs.SummarizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
    provider: SummarizeProvider = Depends(get_provider),
):
    res = await summarize_service.summarize_note(
        db=db, user_id=current_user_id, note_id=note_id, req=body, provider=provider
    )

    return gs.SummarizeOut(
        summary=res["summary"],
        model=res["model"],
        prompt_tokens=res.get("prompt_tokens"),
        completion_tokens=res.get("completion_tokens"),
        total_tokens=res.get("total_tokens"),
        scope="note",
        scope_id=note_id,
    )


@router.post(
    "/folders/{folder_id}", response_model=SummarizeOut, status_code=status.HTTP_200_OK
)
async def summarize_folder(
    folder_id: int,
    body: SummarizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
    provider: SummarizeProvider = Depends(get_provider),
):
    try:
        data = await summarize_service.summarize_folder(
            db=db,
            user_id=current_user_id,
            folder_id=folder_id,
            req=body,
            provider=provider,
        )
        return SummarizeOut(**data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
