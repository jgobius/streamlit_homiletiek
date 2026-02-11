from typing import Any

import streamlit as st
import requests


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
        
def get_churches():
    churches = st.session_state['api_handler'].get('api/churches/')
    return churches

@st.cache_data
def get_song_books():
    song_books = st.session_state['api_handler'].get('api/song-books/')
    return song_books

@st.cache_data
def get_bible_versions():
    bible_versions = st.session_state['api_handler'].get('api/bible-versions/')
    return bible_versions

def get_structured_scriptures(scriptures: list[str], bible_version: str, language: str) -> list[dict[str, Any]]:
    
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
            
    return structured_scripture_data