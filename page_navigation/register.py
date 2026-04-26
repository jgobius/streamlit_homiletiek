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
# de knop wordt hieronder ook expliciet uitgeschakeld om te voorkomen dat
# een mismatch alsnog naar de backend gaat.
passwords_match = bool(password) and password == check_password
if password and check_password and not passwords_match:
    st.warning("Wachtwoorden komen niet overeen")

# Knop pas actief als alle verplichte velden gevuld zijn, een geldig adres
# is gevonden en beide wachtwoorden gelijk zijn. Dit voorkomt de eerder
# gemelde fout dat een lege POST naar /api/auth/register/ gaat en de
# backend reageert met "This field may not be blank.".
form_complete = bool(
    first_name
    and last_name
    and email
    and postal_code
    and house_number
    and st.session_state["address"]
    and passwords_match
)

register = st.button("Registreren", disabled=not form_complete)

if register:

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
