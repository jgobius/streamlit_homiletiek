import streamlit as st


st.title('Welkom')

button_clicked = st.button('Ga naar Inloggen')

if button_clicked:
    st.switch_page(f'{st.session_state["page_navigation_dir"]}/login.py')