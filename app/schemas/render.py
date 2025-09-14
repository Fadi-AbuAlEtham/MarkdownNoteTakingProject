from datetime import datetime
from pydantic import BaseModel, ConfigDict


class RenderOut(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    note_id: int
    revision_id: int
    html: str
    etag: str
    last_modified: datetime | None = None
