import json
import os
from time import sleep

import streamlit as st
import requests
from pydantic import ValidationError

from email_validator.exceptions import EmailSyntaxError
from src.models.user_model import UserModel
from src.api.postal_code import PostalCodeAPI

# Initialiseer adres in session_state zodat een klik op Registreren nooit
# een KeyError oplevert wanneer de gebruiker postcode/huisnummer overslaat
# of de adres-API faalt.
st.session_state.setdefault("address", {})
# Bewaar het laatst opgevraagde (postcode, huisnummer)-paar zodat we de
# externe postcode-API niet bij elke Streamlit-rerun opnieuw aanroepen
# (toetsaanslag in een ander veld of klik op Registreren triggert anders
# een onnodige extra request, met kans op overschrijven van een geldig
# adres door een tijdelijke API-fout).
st.session_state.setdefault("address_lookup_key", None)

# Terugknop naar de publieke landingpage. Streamlit heeft geen native
# back-link-styling, dus een gewone secundaire knop bovenaan de pagina.
# Bewust geen type="primary": de hoofd-actie op deze pagina blijft "Registreren".
if st.button("← Terug naar hoofdpagina"):
    st.switch_page(f"{st.session_state['page_navigation_dir']}/frontpage.py")

st.title("Registreren voor kerkdienstanalyses")

first_name = st.text_input("Voornaam", max_chars=150)
last_name = st.text_input("Achternaam", max_chars=150)
email = st.text_input("E-mailadres", max_chars=150)
postal_code = st.text_input("Postcode", max_chars=7)
house_number = st.text_input("Huisnummer", max_chars=10)

# Alleen API aanroepen wanneer postcode én huisnummer ingevuld zijn én
# ten opzichte van de vorige lookup gewijzigd zijn. Zo blijft een eerder
# gevonden adres staan wanneer de gebruiker daarna alleen nog z'n
# wachtwoord intypt of op Registreren klikt.
if house_number and postal_code:
    lookup_key = (postal_code.strip(), house_number.strip())
    if lookup_key != st.session_state["address_lookup_key"]:
        try:
            postal_code_api = PostalCodeAPI()
            adres_info = postal_code_api.validate_postal_code(postal_code, house_number)
            st.session_state["address"] = adres_info
            st.session_state["address_lookup_key"] = lookup_key
        except requests.exceptions.HTTPError:
            st.session_state["address"] = {}
            st.session_state["address_lookup_key"] = lookup_key
        except Exception as e:
            st.session_state["address"] = {}
            st.session_state["address_lookup_key"] = lookup_key
            st.error(f"Er is een algemene fout opgetreden: {str(e)}")

    if st.session_state["address"]:
        adres_info = st.session_state["address"]
        st.success(
            f'Adres gevonden: {adres_info.get("straat", "")} {house_number}, {adres_info.get("plaats")}'
        )
    else:
        st.error("Adres niet gevonden.")

st.divider()

password = st.text_input("Wachtwoord", type="password")
check_password = st.text_input("Bevestig wachtwoord", type="password")

# Toon de mismatch-waarschuwing zodra beide wachtwoorden zijn ingevuld;
# de daadwerkelijke blokkade gebeurt verderop via de missing_fields-check.
passwords_match = bool(password) and password == check_password
if password and check_password and not passwords_match:
    st.warning("Wachtwoorden komen niet overeen")

# Bouw een lijst met ontbrekende of ongeldige velden zodat de gebruiker
# direct ziet waarom registratie nog niet kan. Dit lost twee
# UX-problemen op:
#   1. Bij browser-autofill (Chrome) wordt niet altijd een Streamlit-rerun
#      getriggerd, waardoor een eerder uitgeschakelde knop "vast" leek te
#      zitten zonder uitleg.
#   2. Een uitgeschakelde knop verbergt waaróm hij uit staat — een
#      expliciete melding voorkomt dat de gebruiker hoeft te raden.
def _verzamel_ontbrekende_velden() -> list[str]:
    ontbreekt: list[str] = []
    if not first_name:
        ontbreekt.append("Voornaam")
    if not last_name:
        ontbreekt.append("Achternaam")
    if not email:
        ontbreekt.append("E-mailadres")
    if not postal_code:
        ontbreekt.append("Postcode")
    if not house_number:
        ontbreekt.append("Huisnummer")
    # Adres-lookup faalde of postcode/huisnummer ontbreekt: in beide
    # gevallen heeft session_state["address"] geen bruikbare gegevens.
    if postal_code and house_number and not st.session_state["address"]:
        ontbreekt.append("Geldig adres (postcode + huisnummer combinatie niet gevonden)")
    if not password:
        ontbreekt.append("Wachtwoord")
    if not check_password:
        ontbreekt.append("Bevestig wachtwoord")
    if password and check_password and not passwords_match:
        ontbreekt.append("Wachtwoorden moeten gelijk zijn")
    return ontbreekt


missing_fields = _verzamel_ontbrekende_velden()

# Live hint boven de knop. Bij elke rerun (toetsaanslag, focuswissel,
# klik) wordt deze opnieuw opgebouwd zodat de lijst meebeweegt met de
# invoer van de gebruiker.
if missing_fields:
    st.info(
        "Nog te doen voordat je kunt registreren:\n"
        + "\n".join(f"- {veld}" for veld in missing_fields)
    )

# Knop is bewust altijd actief. Een klik triggert sowieso een
# Streamlit-rerun, waardoor door de browser ge-autofill'de waarden
# alsnog in het script terechtkomen en de adres-lookup boven aan dit
# bestand alsnog kan slagen. De definitieve validatie gebeurt in de
# klikafhandeling hieronder.
register = st.button("Registreren", type="primary")

if register:
    # Herbereken na de rerun die door de klik is afgedwongen — autofill-
    # waarden zijn nu zeker opgepikt en de adres-lookup heeft kunnen
    # draaien.
    missing_fields = _verzamel_ontbrekende_velden()
    if missing_fields:
        st.error(
            "Registratie kan nog niet voltooid worden. Ontbrekend of ongeldig:\n"
            + "\n".join(f"- {veld}" for veld in missing_fields)
        )
        st.stop()

    try:
        user_model = UserModel(
            first_name=first_name,
            last_name=last_name,
            email=email,
            street=st.session_state["address"].get("straat", ""),
            house_number=house_number,
            city=st.session_state["address"].get("plaats", ""),
            province=st.session_state["address"].get("provincie", ""),
            postal_code=st.session_state["address"].get("postcode", ""),
            password=password,
            check_password=check_password,
        )

        api_base_url = os.environ.get("API_BASE_URL")
        if not api_base_url:
            st.error("Configuratiefout: API_BASE_URL is niet ingesteld.")
        else:
            result = requests.post(
                url=f"{api_base_url}/api/auth/register/",
                data=json.dumps(user_model.model_dump()),
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            if result.status_code == 201:
                st.success(
                    "Registratie succesvol! Je ontvangt een bevestigingsmail om je account te activeren."
                )
                sleep(3)
                st.switch_page(
                    f"{st.session_state['page_navigation_dir']}/login.py"
                )
            else:
                st.error(f"Fout bij registratie: {result.text}")

    except EmailSyntaxError:
        # Pydantic's EmailStr gooit deze als het emailadres syntactisch ongeldig is.
        st.error("Ongeldig emailadres.")

    except ValidationError:
        # Pydantic v2 verpakt EmailStr-fouten meestal als ValidationError;
        # vangen we hier zodat de gebruiker een nette melding krijgt i.p.v.
        # een Streamlit-traceback.
        st.error("Ongeldig emailadres.")

    except ValueError as ve:
        st.error(str(ve))

    except requests.exceptions.RequestException as re_err:
        # Netwerk-/timeoutfouten richting de backend afvangen zodat de
        # gebruiker een leesbare melding krijgt in plaats van een traceback.
        st.error(f"Kon de server niet bereiken: {str(re_err)}")

    except Exception as e:
        st.error(f"Er is een fout opgetreden: {str(e)}")
