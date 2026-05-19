import os

import streamlit as st
import requests
from dotenv import load_dotenv

from src.api.handler import APIHandler
from src.api.jwthandler import JwtHandler

load_dotenv()

def get_token(username: str, password: str) -> APIHandler:

    jwt_handler = JwtHandler(
        username=username,
        password=password,
        base_url=os.environ.get('API_BASE_URL'),
        access_endpoint="/api/token/",
        refresh_endpoint="/api/token/refresh/",
    )
    
    # APIHandler praat met de Django-backend (API_BASE_URL, poort 8000),
    # niet met de agent — anders levert bv. /api/sermon-analyses/ een 404 op.
    api_handler = APIHandler(
        base_url=os.environ.get('API_BASE_URL'),
        jwt_handler=jwt_handler,
    )

    return api_handler

# Terugknop naar de publieke landingpage. Streamlit heeft geen native
# back-link-styling, dus een gewone secundaire knop bovenaan de pagina.
# Bewust geen type="primary": de hoofd-actie op deze pagina blijft "Login".
if st.button("← Terug naar hoofdpagina"):
    st.switch_page(f"{st.session_state['page_navigation_dir']}/frontpage.py")

st.title("Inloggen")

# Inputs + Login in st.form zodat Enter in een tekstveld het formulier
# submit. Buiten een form rerunt Streamlit per toetsaanslag en triggert
# Enter geen knop — daardoor moest de gebruiker eerder expliciet op Login
# klikken. Binnen een form rerunt de pagina niet op input-changes, dus de
# eerdere `disabled=not user_name or not password`-truc werkt hier niet;
# in plaats daarvan valideren we na submit.
with st.form("login_form"):
    user_name = st.text_input("Username")
    password = st.text_input("Password", type="password")
    login_button = st.form_submit_button("Login")

# "Wachtwoord vergeten?" — secundaire actie, daarom als losse knop onder
# de Login-knop. We gebruiken een gewone knop (geen markdown-link) zodat
# de navigatie via st.switch_page loopt en de Streamlit-routing intact
# blijft (een markdown-link zou de volledige app herstarten).
if st.button("Wachtwoord vergeten?"):
    st.switch_page(f"{st.session_state['page_navigation_dir']}/wachtwoord_vergeten.py")

if login_button and (not user_name or not password):
    # Validatie verplaatst van knop-`disabled` naar post-submit, omdat
    # st.form pas rerunt bij submit en de knop-state dus niet live op de
    # input-velden reageert.
    st.error("Vul zowel gebruikersnaam als wachtwoord in.")
elif login_button:

    try:
        api_handler = get_token(
            username=user_name,
            password=password,
        )
        st.session_state['api_handler'] = api_handler
        # Zet het refresh token klaar zodat main.py het naar de cookie kan schrijven.
        st.session_state['_pending_refresh_token'] = api_handler.jwt_handler.get_refresh_token()
        st.switch_page(f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py")

    except requests.exceptions.HTTPError as e:
        # Foutmelding direct tonen i.p.v. via session_state op de volgende rerun:
        # Streamlit rendert top-to-bottom, dus een vlag die ná de render-fase
        # wordt gezet zou pas verschijnen op een volgende rerun — die er hier
        # niet automatisch komt, waardoor de gebruiker niets zag.
        status_code = e.response.status_code if e.response is not None else None
        if status_code == 401:
            # Django SimpleJWT geeft voor zowel verkeerde inloggegevens als een
            # niet-geactiveerd account dezelfde 401 met dezelfde detail-tekst,
            # dus we kunnen ze client-side niet onderscheiden — daarom beide
            # mogelijkheden expliciet noemen.
            st.error(
                "Inloggen mislukt. Mogelijke oorzaken: ongeldige gebruikersnaam of "
                "wachtwoord, of het account is nog niet geactiveerd. Controleer je "
                "e-mail voor de activatielink."
            )
        else:
            st.error(f"Onverwachte fout bij inloggen (status {status_code}): {e}")

    except requests.exceptions.RequestException as e:
        # Netwerkfout, timeout, DNS-probleem — afvangen zodat de gebruiker
        # geen Streamlit-traceback ziet.
        st.error(f"Kon de server niet bereiken: {e}")

    
