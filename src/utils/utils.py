from typing import Any

import requests
import os
import json
import re
from typing import Any

import streamlit as st
import requests

from src.components.user_suggestions import render_suggestions_trigger

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


def clean_md(text: str) -> str:
    """Normaleer LLM-gegenereerde markdown voor robuuste Streamlit-weergave.

    Herstelt:
    - Letterlijke \\n escape-sequences naar echte newlines
    - ** tekst ** (spaties binnen bold-markers) naar **tekst**
    """
    if not text:
        return text
    text = text.replace("\\n", "\n")
    text = re.sub(r'\*\*[ \t]+(\S)', r'**\1', text)
    text = re.sub(r'(\S)[ \t]+\*\*', r'\1**', text)
    return text


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
        
def get_data(endpoint:str) -> Any:
    """
    Retrieve data from the API using the specified endpoint.
    This function uses the API handler stored in Streamlit's session state
    to fetch data from the given endpoint.
    Args:
        endpoint (str): The API endpoint path or identifier to fetch data from.
    Returns:
        Any: The data retrieved from the API endpoint.
    Raises:
        KeyError: If 'api_handler' is not found in session state.
        Exception: Any exceptions raised by the underlying API handler's get method.
    """
    
    data = st.session_state['api_handler'].get(endpoint)
    return data

@st.cache_data
def get_cached_data(endpoint:str) -> Any:
    """
    Retrieve cached data from the specified endpoint.
    Args:
        endpoint (str): The API endpoint to fetch data from.
    Returns:
        Any: The data retrieved from the specified endpoint.
    """
    
    return get_data(endpoint)

def get_structured_scriptures(scriptures: list[str], bible_version: str, language: str) -> list[dict[str, Any]]:
    """
    Fetch and structure scripture data from an API for given scripture references.
    This function takes a list of scripture references and queries an external API
    to retrieve structured data about each scripture in the specified Bible version
    and language.
    Args:
        scriptures (list[str]): A list of scripture references (e.g., ["John 3:16", "Romans 12:1"]).
        bible_version (str): The Bible version to retrieve scriptures from (e.g., "KJV", "NIV").
        language (str): The language code for the scripture content (e.g., "en", "es").
    Returns:
        list[dict[str, Any]]: A list of dictionaries containing structured scripture data
            retrieved from the API. Each dictionary corresponds to a successful API response
            for the respective scripture reference.
    Raises:
        requests.exceptions.RequestException: If the API request fails (not caught in current implementation).
    Note:
        - Only successful API responses (status code 200) are included in the returned list.
        - Failed requests are silently skipped.
        - Requires 'API_AGENT_URL' to be configured in Streamlit secrets.
    """
    st.write(scriptures)
    structured_scripture_data: list[dict[str, Any]] = []
    st.write(bible_version)
    for scripture in scriptures:

        data: dict[str, str] = {
            "scripture_data": scripture,
            "bible_version": bible_version,
            "language": language
            }
        
        response = requests.post(
            url=f"{st.secrets['API_AGENT_URL']}/structured_scripture/",
            json=data
        )
        
        if response.status_code == 200:
            structured_scripture_data.append(response.json())
            
        else:
            st.write(response.text)
            
    return structured_scripture_data


def save_scriptures(scriptures: list[dict[str, Any]]) -> None:
    """
    Save a list of scripture dictionaries to a JSON file.
    This function creates a temporary directory if it doesn't exist and writes
    the provided scriptures data to a JSON file at 'temp/scriptures.json'.
    Args:
        scriptures: A list of dictionaries containing scripture data, where each
                   dictionary can have string keys and values of any type.
    Returns:
        None
    """
    
    os.makedirs("temp", exist_ok=True)
    
    with open("temp/scriptures.json", "w") as f:
        json.dump(scriptures, f)

@st.cache_data  
def load_scriptures() -> list[dict[str, Any]] | None:
    """
    Load scriptures data from a JSON file.
    Reads scripture data from a local JSON file located at 'temp/scriptures.json'
    and returns it as a list of dictionaries.
    Returns:
        list[dict[str, Any]] | None: A list of dictionaries containing scripture data,
            or None if the file cannot be read or parsed.
    Raises:
        FileNotFoundError: If the 'temp/scriptures.json' file does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
        IOError: If an error occurs while reading the file.
    """
    
    with open("temp/scriptures.json", "r") as f:
        return json.load(f)
    
    
def _sla_thema_voorkeur_op() -> None:
    """Sla de thema-voorkeur op in de cookie zodat die na verversing behouden blijft."""
    # Lees de toggle-waarde en synchroniseer naar de voorkeur-key. De widget gebruikt
    # '_dark_mode_toggle' als key zodat 'dark_mode' zelf geen widget-key is; Streamlit
    # wist widget-keys bij paginanavigatie als het widget niet meer gerenderd wordt.
    donker = bool(st.session_state.get('_dark_mode_toggle', False))
    st.session_state['dark_mode'] = donker
    controller = st.session_state.get('cookie_controller')
    if controller:
        try:
            controller.set('dark_mode', 'true' if donker else 'false')
        except TypeError:
            pass  # controller nog niet gereed — volgende render probeert het opnieuw


def render_sidebar():
    
    with st.sidebar:
        
        with st.expander("Kerkdienstanalyses"):
            st.page_link(label="Overzicht kerkdienstanalyses", page=f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py")
            st.page_link(label="Nieuwe kerkdienstanalyse", page=f"{st.session_state['page_navigation_dir']}/analyses/new_analysis.py")
            
        with st.expander("Gemeenten"):
            st.page_link(label="Overzicht gemeenten", page=f"{st.session_state['page_navigation_dir']}/churches/churches_overview.py")
            st.page_link(label="Nieuwe gemeente", page=f"{st.session_state['page_navigation_dir']}/churches/new_church.py")
            
        with st.expander("Account"):
            st.page_link(label="Uitloggen", page=f"{st.session_state['page_navigation_dir']}/logout.py")
            # Gebruik '_dark_mode_toggle' als widget-key zodat de voorkeur-key 'dark_mode'
            # geen widget-key is. Streamlit wist widget-keys bij paginanavigatie wanneer
            # het widget niet meer gerenderd wordt; als 'dark_mode' een gewone
            # session_state-key blijft, gaat de instelling niet verloren na navigatie.
            # value= initialiseert de toggle vanuit 'dark_mode' als de widget-key nog
            # niet in session_state staat (bijv. na paginawissel).
            st.toggle(
                "Donker thema",
                key="_dark_mode_toggle",
                value=st.session_state.get('dark_mode', False),
                on_change=_sla_thema_voorkeur_op,
            )

        # Toon de suggesties-knop als de gebruiker ingelogd is (api_handler beschikbaar).
        if "api_handler" in st.session_state:
            render_suggestions_trigger(st.session_state["api_handler"])


def render_analysis_results_sidebar(analysis_results: list[dict[str, Any]]) -> None:
    
    
    
    with st.sidebar:
        st.switch_page(f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py")
        
        st.page_link(label="Overzicht preekanalyses", page=f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py")
        st.page_link(label="Analyse overzicht", page=f"{st.session_state['page_navigation_dir']}/analysis_results/overview.py", query_params={"analysis_id": analysis_results[0]['id']})
