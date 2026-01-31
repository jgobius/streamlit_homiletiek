from datetime import datetime
from typing import Any

import streamlit as st

from src.utils.utils import redirect_to_login

redirect_to_login()

def get_sermon_analysis():
    
    analysis = st.session_state['api_handler'].get('api/sermon-analyses')
    
    return analysis

def set_scripture(scriptures:list[dict[str, Any]]) -> str:
    
    if len(scriptures) == 0:
        return ""
    
    scripture_str = ""
    for scripture in scriptures:
        book = scripture['start_verse']['scripture_book']['book']
        chapter = scripture['start_verse']['chapter']['value']
        verse_start = scripture['start_verse']['number']['value']
        verse_end = scripture['end_verse']['number']['value']
        
        if verse_start == verse_end:
            scripture_str += f"{book} {chapter}:{verse_start}, "
        else:
            scripture_str += f"{book} {chapter}:{verse_start}-{verse_end}, "
    
    return scripture_str.rstrip(', ')


analysis = get_sermon_analysis()
st.title("Preekanalyses")
st.write("Overzicht van alle preekanalyses.")

new_analysis = st.button("Nieuwe analyse", type="primary")

if new_analysis:
    st.switch_page(f"{st.session_state['page_navigation_dir']}/analyses/new_analysis.py")

if len(analysis) == 0:
    st.info("Er zijn nog geen preekanalyses gestart.")
else:
    with st.container():
        for item in analysis:
            
            title = item['title']
            congregation = item['church']['name']
            sermon_date = datetime.strptime(item['sermon_date'], '%Y-%m-%d').strftime('%d-%m-%Y')
            scriptures = item['scriptures']
            
            with st.expander(f"{title} - {congregation} - {sermon_date}"):
                st.write(f"**Titel:** {title}")
                st.write(f"**Gemeente:** {congregation}")
                st.write(f"**Datum:** {sermon_date}")
                st.write(f"**Schriftlezingen:** {scriptures}")