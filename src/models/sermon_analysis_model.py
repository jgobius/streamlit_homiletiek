from typing import Optional, Any

from pydantic import BaseModel, Field
from datetime import date


class SermonAnalysisModel(BaseModel):
    """
    Pydantic model representing the analysis data for a sermon analysis.
    Attributes:
        title (str): The title of the sermon, maximum 64 characters.
        place (str): The location where the sermon was delivered, maximum 64 characters.
        congregation (str): The name of the congregation, maximum 64 characters.
        sermon_date (date): The date when the sermon was delivered.
        website (Optional[str | None]): Optional URL of the sermon or church website, maximum 64 characters.
        scriptures (list[str]): List of scripture references used in the sermon, each maximum 64 characters.
        extra_context (Optional[str | None]): Optional additional contextual information about the sermon, maximum 1024 characters.
    """
    
    church: int
    title: str = Field(..., max_length=64)
    sermon_date: date
    core_scriptures: str = Field(..., max_length=64)
    scripture_json: list[dict[str, Any]]
    use_calender: bool
    extra_context: Optional[str | None] = Field(None, max_length=1024)
    song_books: list[int] = Field(default_factory=list, max_length=64)
    