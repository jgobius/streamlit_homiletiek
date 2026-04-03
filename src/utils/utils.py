from typing import Any

import requests
import streamlit as st

# Alle bijbelboeken in de Nederlandse volgorde — gebruikt in het eigen-lezingen-dialoogvenster.
BIBLE_BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numeri", "Deuteronomium", "Jozua", "Rechters", "Ruth",
    "1 Samuel", "2 Samuel", "1 Koningen", "2 Koningen", "1 Kronieken", "2 Kronieken", "Ezra",
    "Nehemia", "Ester", "Job", "Psalmen", "Spreuken", "Prediker", "Hooglied", "Jesaja",
    "Jeremia", "Klaagliederen", "Ezechiël", "Daniël", "Hosea", "Joël", "Amos", "Obadja",
    "Jona", "Micha", "Nahum", "Habakuk", "Sefanja", "Haggai", "Zacharia", "Maleachi",
    "Mattheüs", "Marcus", "Lucas", "Johannes", "Handelingen", "Romeinen",
    "1 Korintiërs", "2 Korintiërs", "Galaten", "Efeziërs", "Filippenzen", "Kolossenzen",
    "1 Tessalonicenzen", "2 Tessalonicenzen", "1 Timoteüs", "2 Timoteüs", "Titus", "Filemon",
    "Hebreeën", "Jakobus", "1 Petrus", "2 Petrus", "1 Johannes", "2 Johannes", "3 Johannes",
    "Judas", "Openbaring",
]

# Lezing-typen voor het eigen-lezingen-dialoogvenster.
READING_TYPES = ["Eerste lezing", "Tweede lezing", "Derde lezing", "Vierde lezing"]


def redirect_to_login() -> None:
    """
    Redirect the user to the login page if no session token is present.
    This function checks if a 'session_token' exists in the Streamlit session state.
    If the token is not found, it redirects the user to the login page using the
    page navigation directory stored in session state.
    Returns:
        None
    Raises:
        KeyError: If 'page_navigation_dir' is not present in st.session_state when
                  'session_token' is missing.
    Example:
        >>> redirect_to_login()
        # Redirects to login page if session_token is not in session state
    """
    
    if not 'api_handler' in st.session_state:
        return st.switch_page(f'{st.session_state["page_navigation_dir"]}/login.py')
    
    if not st.session_state['api_handler'].jwt_handler.authorized:
    
        st.switch_page(f'{st.session_state["page_navigation_dir"]}/login.py')
        
def get_data(endpoint: str) -> Any:
    """Haal data op van de API via het opgegeven endpoint."""
    return st.session_state['api_handler'].get(endpoint)


def get_cached_data(endpoint: str) -> Any:
    """Haal data op van de API (alias van get_data, voor toekomstige caching)."""
    return get_data(endpoint)


def get_churches() -> Any:
    return get_data('api/churches/')


def get_song_books() -> Any:
    return get_data('api/song-books/')


def get_structured_scriptures(
    scriptures: list[str],
    bible_version: str | None,
    language: str,
) -> list[dict[str, Any]]:
    """
    Vraag gestructureerde schriftdata op bij de agent voor elke lezing.
    Alleen succesvolle responses (HTTP 200) worden teruggegeven.
    """
    structured: list[dict[str, Any]] = []
    for scripture in scriptures:
        data = {
            "scripture_data": scripture,
            "bible_version": bible_version,
            "language": language,
        }
        response = requests.post(
            url=f"{st.secrets['API_AGENT_URL']}/structured_scripture/",
            json=data,
        )
        if response.status_code == 200:
            structured.append(response.json())
    return structured