import json
from time import sleep

import streamlit as st
import requests

from email_validator.exceptions import EmailSyntaxError
from src.models.user_model import UserModel


def validate_data(
    first_name: str,
    last_name: str,
    email: str,
    password: str,
    check_password: str,
) -> str:
    
    if password != check_password:
        raise ValueError('Wachtwoorden komen niet overeen')
    
    
    user_model = UserModel(
        first_name=first_name,
        last_name=last_name,
        email=email,
        username=email,
        password=password,
        check_password=check_password
    )
    
    return json.dumps(user_model.model_dump())

st.title('Registreren voor kerkdienstanalyses')

first_name = st.text_input('Voornaam', max_chars=150)
last_name = st.text_input('Achternaam', max_chars=150)
email = st.text_input('E-mailadres')
password = st.text_input('Wachtwoord', type='password')
check_password = st.text_input('Bevestig wachtwoord', type='password')

register = st.button('Registreren')

if register:
    
        try:
            data:str = validate_data(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password,
                check_password=check_password,
            )
            result = requests.post(
                url=f"{st.secrets['API_BASE_URL']}/api/auth/register/",
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            if result.status_code == 201:
                st.success('Registratie succesvol! Je wordt doorgestuurd naar de login pagina.')
                sleep(3)
                st.switch_page(f"{st.session_state['page_navigation_dir']}/login.py")

            else:
                st.error(f'Fout bij registratie: {result.text}')
            
        except ValueError as ve:
            st.error(str(ve))
        
        except EmailSyntaxError as e:
            st.error(f'Ongeldig emailadres')
            
        except Exception as e:
            st.error(f'Er is een fout opgetreden: {str(e)}')