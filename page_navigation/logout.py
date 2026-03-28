import streamlit as st
import requests
from time import sleep

st.title('Uitloggen')

refresh_token = st.session_state['api_handler'].jwt_handler.get_refresh_token()
result = requests.post(f'{st.secrets["API_BASE_URL"]}/api/token/blacklist/', data={"refresh": refresh_token})

if result.status_code == 200:
    st.session_state.pop('api_handler')
    if controller := st.session_state.get('cookie_controller'):
        try:
            controller.remove('auth_refresh_token')
        except (TypeError, AttributeError):
            pass
    st.success('Je bent succesvol uitgelogd.')

else:
    
    st.error('Er is een fout opgetreden tijdens het uitloggen. Probeer het opnieuw.')
    