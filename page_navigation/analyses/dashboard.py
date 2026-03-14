from datetime import datetime
from typing import Any

import streamlit as st

from src.utils.utils import redirect_to_login, get_data, render_sidebar

redirect_to_login()

render_sidebar()

        
def format_title(status: str, title: str | None, congregation: str, sermon_date: str) -> str:
    
    color_map: dict[str, str] = {
        'draft': 'orange',
        'submitted': 'blue',
        'pending': 'yellow',
        'success': 'green',
        'error': 'red'
    }
    
    if title:
        return f":{color_map.get(status)}[{status.capitalize()}] - {title} - {congregation} - {sermon_date}"
    
    return f":{color_map.get(status)}[{status.capitalize()}] - {congregation} - {sermon_date}"
        


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


analysis = get_data("api/sermon-analyses/")

st.title("Preekanalyses")
st.write("Overzicht van alle preekanalyses.")

new_analysis = st.button("Nieuwe analyse", type="secondary")

if new_analysis:
    st.switch_page(f"{st.session_state['page_navigation_dir']}/analyses/new_analysis.py")

if len(analysis) == 0:
    st.info("Er zijn nog geen preekanalyses gestart.")
else:
    with st.container():
        for item in analysis:
            status = item['status']
            title = item['title']
            congregation = item['church']['name']
            sermon_date = datetime.strptime(item['sermon_date'], '%Y-%m-%d').strftime('%d-%m-%Y')
            scriptures = item['scripture_json']
            
            with st.expander(format_title(status, title, congregation, sermon_date), expanded=False):
                st.write(f"**Titel:** {title}")
                st.write(f"**Gemeente:** {congregation}")
                st.write(f"**Datum:** {sermon_date}")
                st.write(f"**Lezingen:**")
                
                for sc in scriptures:
                    st.write(f"- {sc.get('original_scripture')}")
                    
                st.page_link(label="Bekijk analyse", page=f"{st.session_state['page_navigation_dir']}/analysis_results/overview.py", query_params={"analysis_id": item['id']})
                