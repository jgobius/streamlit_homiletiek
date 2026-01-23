from datetime import datetime
from typing import Any

import streamlit as st

from src.utils.utils import redirect_to_login

redirect_to_login()

@st.cache_data
def get_sermon_analysis():
    
    analysis = st.session_state['api_handler'].get('api/sermon-analyses')
    
    return analysis

def set_scripture(scriptures:list[dict[str, Any]]) -> str:
    
    if len(scriptures) == 0:
        return ""
    
    scripture_str = ""
    for scripture in scriptures:
        book = scripture['start_verse']['scripture_book']['book']
        chapter = scripture['chapter']['value']
        verse_start = scripture['verse_start']['number']['value']
        verse_end = scripture['verse_end']['number']['value']
        
        if verse_start == verse_end:
            scripture_str += f"{book} {chapter}:{verse_start}, "
        else:
            scripture_str += f"{book} {chapter}:{verse_start}-{verse_end}, "
    
    return scripture_str.rstrip(', ')


analysis = get_sermon_analysis()

st.title("Preekanalyses")

new_analysis = st.button("Nieuwe analyse", type="primary")

if new_analysis:
    st.switch_page(f"{st.session_state['page_navigation_dir']}/new_analysis.py")

with st.container():
    for item in analysis:
        
        title = item['title']
        congregation = item['congregation']
        sermon_date = datetime.strptime(item['sermon_date'], '%Y-%m-%d').strftime('%d-%m-%Y')
        # scriptures = set_scripture(item['scripture_references'])
        
        with st.expander(f"{title} - {congregation} - {sermon_date}"):
            st.write(f"**Titel:** {title}")
            st.write(f"**Gemeente:** {congregation}")
            st.write(f"**Datum:** {sermon_date}")