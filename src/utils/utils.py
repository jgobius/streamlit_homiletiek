import os
import json
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