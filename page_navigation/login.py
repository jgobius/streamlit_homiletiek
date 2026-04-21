import os

import streamlit as st
import requests
from dotenv import load_dotenv

from src.api.handler import APIHandler
from src.api.jwthandler import JwtHandler

load_dotenv()

def get_token(username: str, password: str) -> APIHandler:

    jwt_handler = JwtHandler(
        username=username,
        password=password,
        base_url=os.environ.get('API_BASE_URL'),
        access_endpoint="/api/token/",
        refresh_endpoint="/api/token/refresh/",
    )
    
    api_handler = APIHandler(
        base_url=os.environ.get('API_AGENT_URL'),
        jwt_handler=jwt_handler,
    )

    return api_handler

st.title("Inloggen")
user_name = st.text_input("Username")
password = st.text_input("Password", type="password")
login_button = st.button("Login", disabled=not user_name or not password)

if st.session_state.get('login_error'):
    st.error("Ongeldige gebruikersnaam of wachtwoord. Probeer het opnieuw.")
    st.session_state['login_error'] = False

if login_button:

    try:
        api_handler = get_token(
            username=user_name,
            password=password,
        )
        st.session_state['api_handler'] = api_handler
        # Zet het refresh token klaar zodat main.py het naar de cookie kan schrijven.
        st.session_state['_pending_refresh_token'] = api_handler.jwt_handler.get_refresh_token()
        st.switch_page(f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py")

    except requests.exceptions.HTTPError as e:

        if e.response.status_code == 401:
            st.session_state['login_error'] = True
        else:
            raise e
            

    
