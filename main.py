from importlib.metadata import files
import os

import streamlit as st

from src.api.handler import get_api_handler

st.session_state['page_navigation_dir'] = 'page_navigation'

def main():
    
    api_handler = get_api_handler()
    st.session_state['api_handler'] = api_handler

    welcome_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/welcome.py", title='Welcome')
    login_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/login.py", title='Login')
    dashboard_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/dashboard.py", title='Overzicht')
    settings_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/settings.py", title='Instellingen')
    context_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/context.py", title='Context')
    
    if 'session_token' not in st.session_state:
       pg = st.navigation([welcome_page, login_page, dashboard_page], position='hidden')
       pg.run()
    
    else:
       pg = st.navigation([dashboard_page, settings_page])
       pg.run()
    



if __name__ == "__main__":
    main()
