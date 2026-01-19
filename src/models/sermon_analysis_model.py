from typing import Optional

from pydantic import BaseModel, Field
from datetime import date


class SermonAnalysisModel(BaseModel):
    
    title: str = Field(..., max_length=64)
    place:str = Field(..., max_length=64)
    congregation: str = Field(..., max_length=64)
    sermon_date: date
    website: Optional[str | None] = Field(None, max_length=64)
    scriptures: list[str] = Field(..., max_length=64)
    extra_context: Optional[str | None] = Field(None, max_length=1024)