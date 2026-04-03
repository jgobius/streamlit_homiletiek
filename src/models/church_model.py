from typing import Optional, Annotated

from pydantic import BaseModel, Field, BeforeValidator

def check_url_field(value: str) -> str:
    """
    Validate and return a URL field value.
    This function checks if the provided URL string starts with either 'http://' or 'https://'.
    Note: The current implementation has a bug where the value is not modified when it doesn't
    start with the required protocols.
    Args:
        value (str): The URL string to validate.
    Returns:
        str: The original URL value (unmodified in current implementation).
    Example:
        >>> check_url_field("https://example.com")
        'https://example.com'
        >>> check_url_field("example.com")
        'https://example.com'
    """
    
    if not value.startswith("http://") and not value.startswith("https://"):
        value = f'https://{value}'
    return value


class ChurchModel(BaseModel):
    """
    Data model representing a church entity.
    This class defines the structure and validation rules for church information,
    including basic details like name, location, and contact information.
    Attributes
    ----------
    name : str
        The name of the church. Maximum length of 128 characters.
    place : str
        The location or place where the church is situated. Maximum length of 128 characters.
    website : str
        The church's website URL. Maximum length of 200 characters.
    context : Optional[str | None], optional
        Additional contextual information about the church. Maximum length of 1024 characters.
        Defaults to None.
    Notes
    -----
    All fields except 'context' are required. The model uses Pydantic's Field for
    validation and ensures maximum length constraints are enforced.
    """
    
    name:         str = Field(..., max_length=128)
    place:        str = Field(..., max_length=128)
    address:      Optional[str | None] = Field(None, max_length=200)
    denomination: Optional[str | None] = Field(None, max_length=16)
    modality:     Optional[str | None] = Field(None, max_length=32)
    website:      Annotated[str, BeforeValidator(check_url_field)] = Field(..., max_length=200)
    context:      Optional[str | None] = Field(None, max_length=1024)