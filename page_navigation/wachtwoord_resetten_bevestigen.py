"""Wachtwoord-vergeten flow — stap 2 (token + nieuw wachtwoord).

De gebruiker komt hier via de resetlink uit de mail die door
/api/auth/password-reset-request/ is verstuurd. Het token zit in de
query-parameter `token`. Na het invoeren van een nieuw wachtwoord POST'en
we naar /api/auth/password-reset-confirm/, die het token verifieert,
het wachtwoord wijzigt en het token markeert als gebruikt.

URL-pad wordt expliciet gezet in main.py (`url_path` op de st.Page) zodat
de mail-link uit de backend (FRONTEND_URL/Wachtwoord_resetten_bevestigen
?token=<uuid>) precies klopt — Streamlit leidt anders het pad uit het
bestandsnaam af, en die conventie kan per renaming wijzigen.
"""

import os
from time import sleep

import requests
import streamlit as st


# Terugknop voor het geval de gebruiker per ongeluk op deze pagina belandt
# zonder geldige link (bv. door handmatig de URL te openen). Consistent
# met de andere pre-login pagina's: secundaire knop bovenaan.
if st.button("← Terug naar inloggen"):
    st.switch_page(f"{st.session_state['page_navigation_dir']}/login.py")

st.title("Nieuw wachtwoord instellen")

# Token uit de query-parameter halen. Als hij ontbreekt is dit niet de
# pagina waar de gebruiker via de mail-link terecht is gekomen, dus
# tonen we een duidelijke uitleg en stoppen we vóór het formulier — een
# leeg formulier zou anders een 400 uit de backend uitlokken.
token = st.query_params.get("token")
if not token:
    st.error(
        "Deze pagina is alleen bereikbaar via de resetlink uit de e-mail "
        "die je hebt ontvangen. Vraag een nieuwe link aan via 'Wachtwoord "
        "vergeten' op de inlogpagina."
    )
    st.stop()

password = st.text_input("Nieuw wachtwoord", type="password")
confirm_password = st.text_input("Bevestig nieuw wachtwoord", type="password")

# Mismatch-melding zodra beide velden zijn gevuld; de knop wordt hieronder
# ook expliciet uitgeschakeld zodat een mismatch nooit aan de backend wordt
# voorgelegd.
passwords_match = bool(password) and password == confirm_password
if password and confirm_password and not passwords_match:
    st.warning("Wachtwoorden komen niet overeen.")

reset = st.button(
    "Wachtwoord opslaan",
    disabled=not passwords_match,
    type="primary",
)

if reset:
    api_base_url = os.environ.get("API_BASE_URL")
    if not api_base_url:
        st.error("Configuratiefout: API_BASE_URL is niet ingesteld.")
    else:
        try:
            result = requests.post(
                url=f"{api_base_url}/api/auth/password-reset-confirm/",
                json={
                    "token": token,
                    "password": password,
                    "confirm_password": confirm_password,
                },
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            st.error(f"Kon de server niet bereiken: {e}")
        else:
            if result.status_code == 200:
                st.success(
                    "Je wachtwoord is succesvol gewijzigd. Je wordt naar de "
                    "inlogpagina doorgestuurd."
                )
                sleep(3)
                st.switch_page(
                    f"{st.session_state['page_navigation_dir']}/login.py"
                )
            else:
                # Backend levert een leesbare validatiefout op (token verlopen,
                # ongeldig, of wachtwoorden komen niet overeen).
                st.error(f"Er is iets misgegaan: {result.text}")
