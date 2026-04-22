import os
from time import sleep

import streamlit as st
import requests

st.title('Uitloggen')

refresh_token = st.session_state['api_handler'].jwt_handler.get_refresh_token()
result = requests.post(f'{os.environ.get("API_BASE_URL")}/api/token/blacklist/', data={"refresh": refresh_token})

if result.status_code == 200:

    st.session_state.pop('api_handler')
    # Verwijder ook de gecachete UI-voorkeur zodat een volgende inlog (mogelijk
    # een andere gebruiker in dezelfde browsersessie) zijn eigen dark_mode uit
    # /api/user-preferences/ ophaalt in plaats van die van de vorige gebruiker
    # te erven.
    st.session_state.pop('dark_mode', None)
    # Ook is_superuser wissen zodat een volgende gebruiker niet per ongeluk
    # rechten erft (hoofdmenu zichtbaar) voordat hydration opnieuw draait.
    st.session_state.pop('is_superuser', None)
    st.success('Je bent succesvol uitgelogd.')

    # Directe link terug naar het inlogscherm, zodat de gebruiker niet
    # handmatig een URL hoeft in te voeren. We gebruiken st.switch_page i.p.v.
    # st.page_link omdat login.py pas ná pop('api_handler') in de navigatie
    # verschijnt (zie main.py); switch_page valideert de doelpagina pas bij
    # de volgende render en werkt daarom betrouwbaar vanaf logout.
    if st.button('Opnieuw inloggen', type='primary'):
        st.switch_page(f"{st.session_state['page_navigation_dir']}/login.py")

else:

    st.error('Er is een fout opgetreden tijdens het uitloggen. Probeer het opnieuw.')
