import os

import streamlit as st
import requests


# Uitloggen gebeurt in één render: HTTP blacklist-call, sessie wissen, en
# direct daarna de 'Uitgelogd'-weergave tonen. We roepen bewust GEEN
# st.rerun() aan. Een rerun zou main.py opnieuw door de sessie-herstel-logica
# laten lopen, die op de eerste mislukte herstel-poging een st.stop() doet
# ("wachten tot de cookie-controller JS de cookies doorstuurt"). Na uitloggen
# is die cookie blacklisted en levert die st.stop een blanco pagina op; de
# cookie-controller vuurt niet opnieuw, dus de pagina blijft leeg.
if 'api_handler' in st.session_state:
    refresh_token = st.session_state['api_handler'].jwt_handler.get_refresh_token()
    result = requests.post(
        f'{os.environ.get("API_BASE_URL")}/api/token/blacklist/',
        data={"refresh": refresh_token},
    )

    if result.status_code != 200:
        st.title('Uitloggen')
        st.error('Er is een fout opgetreden tijdens het uitloggen. Probeer het opnieuw.')
        st.stop()

    st.session_state.pop('api_handler')
    # Verwijder ook de gecachete UI-voorkeur zodat een volgende inlog (mogelijk
    # een andere gebruiker in dezelfde browsersessie) zijn eigen dark_mode uit
    # /api/user-preferences/ ophaalt in plaats van die van de vorige gebruiker
    # te erven.
    st.session_state.pop('dark_mode', None)
    # Ook is_superuser wissen zodat een volgende gebruiker niet per ongeluk
    # rechten erft (hoofdmenu zichtbaar) voordat hydration opnieuw draait.
    st.session_state.pop('is_superuser', None)
    # Voorkom dat main.py op de volgende render (bv. na klik op 'Opnieuw
    # inloggen') zijn st.stop-guard triggert bij een mislukte sessie-
    # herstelpoging met de ongeldige cookie. Zie de toelichting bovenaan.
    st.session_state['_restore_attempts'] = 1

# api_handler is afwezig — uitloggen is voltooid. Titel in verleden tijd en
# een directe knop terug naar het inlogscherm, zodat de gebruiker niet
# handmatig een URL hoeft in te typen.
st.title('Uitgelogd')
st.success('Je bent succesvol uitgelogd.')

if st.button('Opnieuw inloggen', type='primary'):
    st.switch_page(f"{st.session_state['page_navigation_dir']}/login.py")
