import streamlit as st


st.title('Handreiking preekanalyses')

st.write(
    """
    Welkom bij de handreiking preekanalyses. 
    Deze tool helpt je bij het analyseren van preken op verschillende aspecten.
    Kies hieronder of je wilt inloggen of registreren om verder te gaan.
    De analyses worden gegenereerd op basis van de specifieke locatie, 
    de kerkelijke gemeente en de datum van de viering, waardoor een goede 
    aansluiting op de lokale context wordt gegeven.
    """
)

col1, col2 = st.columns([1, 1])

with col1:
    button_login = st.button('Inloggen')
with col2:
    button_register = st.button('Registreren')

if button_login:
    st.switch_page(f'{st.session_state["page_navigation_dir"]}/login.py')
    
if button_register:
    st.switch_page(f'{st.session_state["page_navigation_dir"]}/register.py')