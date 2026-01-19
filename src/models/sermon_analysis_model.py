from typing import Optional

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
    
    title: str = Field(..., max_length=64)
    place:str = Field(..., max_length=64)
    congregation: str = Field(..., max_length=64)
    sermon_date: date
    website: Optional[str | None] = Field(None, max_length=64)
    scriptures: list[str] = Field(..., max_length=64)
    extra_context: Optional[str | None] = Field(None, max_length=1024)