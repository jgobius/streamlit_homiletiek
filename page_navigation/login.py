import streamlit as st
import requests

from src.api.handler import APIHandler
from src.api.jwthandler import JwtHandler

def get_token(username: str, password: str) -> APIHandler:

    jwt_handler = JwtHandler(
        username=username,
        password=password,
        base_url=st.secrets["API_BASE_URL"],
        access_endpoint="/api/token/",
        refresh_endpoint="/api/token/refresh/",
    )
    
    api_handler = APIHandler(
        base_url=st.secrets["API_BASE_URL"],
        jwt_handler=jwt_handler,
    )

    return api_handler

st.title("Inloggen")
user_name = st.text_input("Username")
password = st.text_input("Password", type="password")
login_button = st.button("Login", disabled=not user_name or not password)

if login_button:

    try:
        api_handler = get_token(
            username=user_name,
            password=password,
        )
        st.session_state['api_handler'] = api_handler
        st.switch_page(f"{st.session_state['page_navigation_dir']}/dashboard.py")
        
    except requests.exceptions.HTTPError as e:
        
        if e.response.status_code == 401:
            st.session_state['login_error'] = True
        else:
            raise e
            

    
