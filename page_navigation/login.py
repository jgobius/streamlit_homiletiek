import streamlit as st

from src.api.handler import APIHandler



def get_token(api_handler: APIHandler, username:str, password:str) -> dict[str, str]:
    
    token = api_handler.post(
        endpoint="api/token/",
        data={"username": username, "password": password})
    
    return token

st.title("Inloggen")
user_name = st.text_input("Username")
password = st.text_input("Password", type="password")
login_button = st.button("Login", disabled=not user_name or not password)

if login_button:

    token = get_token(
        api_handler=st.session_state['api_handler'],
        username=user_name,
        password=password)
    
    st.session_state['session_token'] = token['access']
    
    st.switch_page(f"{st.session_state['page_navigation_dir']}/dashboard.py")