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

    # Veeg de complete session_state schoon op een whitelist na. Eerdere
    # versies popten alleen 'api_handler', 'dark_mode' en 'is_superuser';
    # daardoor bleven user-specifieke caches als 'dashboard_analyses_cache'
    # en 'user_email' staan en kreeg een volgende gebruiker in dezelfde
    # browser de gecachete /api/sermon-analyses/-response van de vorige
    # gebruiker te zien — een privacy-lek voor accounts zonder eigen
    # analyses. Een whitelist-aanpak voorkomt ook dat nieuwe user-data-keys
    # in de toekomst per ongeluk blijven hangen.
    #
    # Behouden: 'page_navigation_dir' (navigatie-root, niet user-specifiek)
    # en 'cookie_controller' (live JS-handle, hergebruikt voor de cookies
    # waarmee main.py de sessie probeert te herstellen).
    _te_behouden = {'page_navigation_dir', 'cookie_controller'}
    for _key in list(st.session_state.keys()):
        if _key not in _te_behouden:
            del st.session_state[_key]
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

# Tweede actie: terug naar de publieke landingpage. Bewust secundair (default
# type) zodat 'Opnieuw inloggen' visueel de hoofd-actie blijft.
if st.button('Terug naar hoofdpagina'):
    st.switch_page(f"{st.session_state['page_navigation_dir']}/frontpage.py")
