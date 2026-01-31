from typing import Annotated

import streamlit as st

from email_validator import validate_email
from email_validator.exceptions import EmailSyntaxError
from src.models.user_model import UserModel


def validate_data(
    first_name: str,
    last_name: str,
    email: str,
    password: str,
    check_password: str,
) -> Annotated[UserModel, 'Validated User Model']:
    
    if password != check_password:
        raise ValueError('Wachtwoorden komen niet overeen')
    
    
    user_model = UserModel(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=password,
        check_password=check_password
    )
    return user_model

st.title('Registreren voor preekanalyses')

first_name = st.text_input('Voornaam', max_chars=150)
last_name = st.text_input('Achternaam', max_chars=150)
email = st.text_input('E-mailadres')
password = st.text_input('Wachtwoord', type='password')
check_password = st.text_input('Bevestig wachtwoord', type='password')

register = st.button('Registreren')

if register:
    
    
        st.error('Wachtwoorden komen niet overeen!')
        
    else:
        
        try:
            validate_email(email)
        
            user_model = UserModel(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password,
                check_password=check_password
            )
        
        except EmailSyntaxError as e:
            st.error(f'Ongeldig emailadres')