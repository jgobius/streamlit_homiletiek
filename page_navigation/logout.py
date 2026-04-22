import os

import streamlit as st
import requests


# Flow in twee fasen:
#
# 1. Eerste render (gebruiker klikt 'Uitloggen' in de sidebar): api_handler zit
#    nog in session_state. We voeren de token-blacklist-call uit, wissen de
#    sessie, en doen st.rerun(). Door die rerun bouwt main.py de navigatie
#    opnieuw op, nu zonder api_handler — waardoor logout.py in de
#    'unauthenticated' paginalijst draait en de knop-callback hieronder op de
#    volgende render betrouwbaar kan switchen naar login.py.
#
# 2. Tweede render (of elke latere keer dat de pagina wordt bezocht zonder
#    login): api_handler is afwezig. We tonen de 'Uitgelogd'-bevestiging en
#    een knop die naar login navigeert. De titel is bewust verleden tijd —
#    op het moment dat de gebruiker dit ziet is het uitloggen al afgerond.
if 'api_handler' in st.session_state:
    refresh_token = st.session_state['api_handler'].jwt_handler.get_refresh_token()
    result = requests.post(
        f'{os.environ.get("API_BASE_URL")}/api/token/blacklist/',
        data={"refresh": refresh_token},
    )

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
        # Rerun nodig zodat main.py de navigatie opnieuw opbouwt (nu zonder
        # api_handler) vóórdat we de knop + switch_page-callback renderen.
        st.rerun()
    else:
        st.title('Uitloggen')
        st.error('Er is een fout opgetreden tijdens het uitloggen. Probeer het opnieuw.')
        st.stop()

# api_handler is afwezig — uitloggen is voltooid. Titel in verleden tijd en
# een directe knop terug naar het inlogscherm, zodat de gebruiker niet
# handmatig een URL hoeft in te typen.
st.title('Uitgelogd')
st.success('Je bent succesvol uitgelogd.')

if st.button('Opnieuw inloggen', type='primary'):
    st.switch_page(f"{st.session_state['page_navigation_dir']}/login.py")
