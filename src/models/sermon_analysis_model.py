from typing import Optional, Any

from pydantic import BaseModel, Field
from datetime import date


class SermonAnalysisModel(BaseModel):
    """
    Data model representing the analysis data for a sermon analysis.
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
    title: Optional[str | None] = Field(None, max_length=64)
    sermon_date: date
    # Verwijzing naar het liturgie-roosterobject wanneer 'Kerkelijk rooster volgen' is gekozen.
    liturgy: Optional[int | None] = None
    core_scriptures: Optional[str | None] = Field(None, max_length=64)
    # Gestructureerde lezingsdata als JSON-lijst; gevuld via de agent bij eigen lezingen.
    scripture_json: list[dict[str, Any]]
    use_calendar: bool
    extra_context: Optional[str | None] = Field(None, max_length=1024)
    song_books: Optional[list[int] | None] = Field(default_factory=list, max_length=64)
    bible_version: int
    # Optionele bijbelvertaling; als None gebruikt de backend de standaard.
    bible_version: Optional[int | None] = None
