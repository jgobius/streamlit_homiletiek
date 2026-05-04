"""Wachtwoord-vergeten flow — stap 1 (e-mailadres invoeren).

De gebruiker komt hier vanaf de inlogpagina via de link "Wachtwoord
vergeten?". Na het invoeren van een e-mailadres POST'en we naar het
backend-endpoint /api/auth/password-reset-request/, dat altijd hetzelfde
generieke succesantwoord teruggeeft (ook als het adres onbekend is).
Dat voorkomt user-enumeratie via deze publieke endpoint. De gebruiker
krijgt vervolgens — bij een bestaand account — per mail een resetlink
naar `wachtwoord_resetten_bevestigen.py` om een nieuw wachtwoord te zetten.
"""

import os

import requests
import streamlit as st


# Terugknop naar de publieke landingpage. Consistent met de stijl op
# login.py en register.py: secundaire knop bovenaan, geen primaire opmaak
# omdat de hoofd-actie op deze pagina "Verstuur resetlink" is.
if st.button("← Terug naar inloggen"):
    st.switch_page(f"{st.session_state['page_navigation_dir']}/login.py")

st.title("Wachtwoord vergeten")

st.markdown(
    "Voer het e-mailadres in waarmee je bent geregistreerd. Je ontvangt "
    "binnen enkele minuten een e-mail met een link om een nieuw wachtwoord "
    "in te stellen."
)

email = st.text_input("E-mailadres", max_chars=150)
verstuur = st.button("Verstuur resetlink", disabled=not email, type="primary")

if verstuur:
    api_base_url = os.environ.get("API_BASE_URL")
    if not api_base_url:
        st.error("Configuratiefout: API_BASE_URL is niet ingesteld.")
    else:
        try:
            result = requests.post(
                url=f"{api_base_url}/api/auth/password-reset-request/",
                json={"email": email},
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            # Netwerk-/timeoutfouten netjes afvangen i.p.v. een Streamlit-
            # traceback aan de gebruiker tonen.
            st.error(f"Kon de server niet bereiken: {e}")
        else:
            if result.status_code == 200:
                # Bewust dezelfde melding als wanneer het adres onbekend
                # is — de backend onthult dat zelf ook niet, en we willen
                # die gelijkheid in de UI doortrekken.
                st.success(
                    "Als er een account bekend is met dit e-mailadres, "
                    "ontvang je binnen enkele minuten een e-mail met een "
                    "resetlink. Controleer ook je spam-map."
                )
            else:
                # 400 met validatiefout uit de serializer (bv. SMTP-fout).
                # `text` is voldoende — de gebruiker hoeft de JSON-structuur
                # niet te zien, maar de melding bevat doorgaans de uitleg.
                st.error(f"Er is iets misgegaan: {result.text}")
