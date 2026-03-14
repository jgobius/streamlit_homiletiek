import streamlit as st
import json

from src.models.church_model import ChurchModel
from src.utils.utils import redirect_to_login, render_sidebar

redirect_to_login()

render_sidebar()

def get_church(id: int):
    church = st.session_state['api_handler'].get(f'api/churches/{id}/')
    return church

if st.query_params.get("church_id"):
    church_id = st.query_params.get("church_id")
    church_data = get_church(church_id)

title = 'Gemeente bewerken' if st.query_params.get("church_id") else 'Nieuwe gemeente toevoegen'
st.title(title)

name = st.text_input("Naam van de gemeente*", max_chars=128, value=church_data['name'] if st.query_params.get("church_id") else "")
place = st.text_input("Plaats van de gemeente*", max_chars=128, value=church_data['place'] if st.query_params.get("church_id") else "")
website = st.text_input("Website van de gemeente*", max_chars=200, value=church_data['website'] if st.query_params.get("church_id") else "")
context = st.text_area("Extra context over de gemeente", height=150, max_chars=1024, value=church_data.get('context', '') if st.query_params.get("church_id") else "")

button_title = "Gemeente bijwerken" if st.query_params.get("church_id") else "Gemeente toevoegen"
add_church = st.button(button_title, type="primary", disabled=not name or not place or not website)

if add_church:
    
    try:
        church = ChurchModel(
            name=name,
            place=place,
            website=website,
            context=context if context else None
        )
        
        data = json.loads(church.model_dump_json())

        if st.query_params.get("church_id"):
            response = st.session_state['api_handler'].put(f'api/churches/{church_id}/', data)
            st.switch_page(f"{st.session_state['page_navigation_dir']}/churches/churches_overview.py")
        else:
            response = st.session_state['api_handler'].post('api/churches/', data)
            
            if st.query_params.get('from_page'):
                st.switch_page(f"{st.session_state['page_navigation_dir']}/analyses/{st.query_params.get('from_page')}")
            else:
                st.switch_page(f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py")
            
    except Exception as e:
        st.error(f"Er is een fout opgetreden: {e}")
    
