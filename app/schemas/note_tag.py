from typing import List
from pydantic import BaseModel, ConfigDict

from app.schemas.tag import TagResponse
from app.schemas.note import NoteResponse

class TagWithNotesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    tag: TagResponse
    notes: List[NoteResponse]
