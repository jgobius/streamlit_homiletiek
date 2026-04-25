import json
import os
from time import sleep

import streamlit as st
import requests

from email_validator.exceptions import EmailSyntaxError
from src.models.user_model import UserModel
from src.utils.utils import valideer_tekstinvoer
from src.api.postal_code import PostalCodeAPI

st.title("Registreren voor kerkdienstanalyses")

first_name = st.text_input("Voornaam", max_chars=150)
last_name = st.text_input("Achternaam", max_chars=150)
email = st.text_input("E-mailadres", max_chars=150)
postal_code = st.text_input("Postcode", max_chars=7)
house_number = st.text_input("Huisnummer", max_chars=10)

if house_number and postal_code:

    try:
        postal_code_api = PostalCodeAPI()
        adres_info = postal_code_api.validate_postal_code(postal_code, house_number)
        st.session_state["address"] = adres_info

        st.success(
            f'Adres gevonden: {adres_info.get("straat", "")} {house_number}, {adres_info.get("plaats")}'
        )
    except requests.exceptions.HTTPError as e:
        st.session_state["address"] = {}
        st.error(f"Adres niet gevonden.")
    except Exception as e:
        st.session_state["address"] = {}
        st.error(f"Er is een algemene fout opgetreden: {str(e)}")

st.divider()

password = st.text_input("Wachtwoord", type="password")
check_password = st.text_input("Bevestig wachtwoord", type="password")

if password != check_password and password and check_password:
    st.warning("Wachtwoorden komen niet overeen")

register = st.button("Registreren")

if register:

    # try:
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

        result = requests.post(
            url=f"{os.environ.get('API_BASE_URL')}/api/auth/register/",
            data=json.dumps(
                user_model.model_dump()
            ),
            headers={"Content-Type": "application/json"},
        )

        if result.status_code == 201:
            st.success(
                "Registratie succesvol! Je ontvangt een bevestigingsmail om je account te activeren."
            )

        else:
            st.error(f"Fout bij registratie: {result.text}")

    # except ValueError as ve:
    #     st.error(str(ve))

    # except EmailSyntaxError as e:
    #     st.error(f"Ongeldig emailadres")

    # except Exception as e:
    #     st.error(f"Er is een fout opgetreden: {str(e)}")
