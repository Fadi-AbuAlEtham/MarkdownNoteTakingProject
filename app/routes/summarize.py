from fastapi import APIRouter, Depends, status

from app.api.deps import get_summarize_service
from app.schemas.summarize import SummarizeRequest, SummarizeOut
from app.services.summarize import SummarizeService
from app.schemas import summarize as gs

router = APIRouter(prefix="/summarize", tags=["Summarization"])


@router.post("/notes/{note_id}", response_model=gs.SummarizeOut)
async def summarize_note(
    note_id: int,
    body: gs.SummarizeRequest,
    summarize_service: SummarizeService = Depends(get_summarize_service),
):
    data = await summarize_service.summarize_note(note_id=note_id, req=body)
    return gs.SummarizeOut(**data)


@router.post(
    "/folders/{folder_id}", response_model=SummarizeOut, status_code=status.HTTP_200_OK
)
async def summarize_folder(
    folder_id: int,
    body: SummarizeRequest,
    summarize_service: SummarizeService = Depends(get_summarize_service),
):
    data = await summarize_service.summarize_folder(folder_id=folder_id, req=body)
    return SummarizeOut(**data)
