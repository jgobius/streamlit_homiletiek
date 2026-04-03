from datetime import datetime
from typing import Any

import requests
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


@st.dialog("Analyse verwijderen")
def confirm_delete_analysis():
    # Haal het te verwijderen item op uit session_state
    item = st.session_state.get("_pending_delete_analysis")
    if not item:
        st.rerun()
    title = item.get('title') or f"{item['church']['name']} - {datetime.strptime(item['sermon_date'], '%Y-%m-%d').strftime('%d-%m-%Y')}"
    st.write(f"Weet je zeker dat je de analyse **'{title}'** wilt verwijderen? Dit kan niet ongedaan worden gemaakt.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ja, verwijderen", type="primary", use_container_width=True):
            try:
                handler = st.session_state['api_handler']
                url = f"{handler.base_url}/api/sermon-analyses/{item['id']}/"
                headers = {"Authorization": f"Bearer {handler.jwt_handler.token}"}
                requests.delete(url, headers=headers).raise_for_status()
                st.session_state.pop("_pending_delete_analysis", None)
                st.rerun()
            except Exception as e:
                st.error(f"Fout bij verwijderen: {e}")
    with col2:
        if st.button("Annuleren", use_container_width=True):
            st.session_state.pop("_pending_delete_analysis", None)
            st.rerun()


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
                    
                # Twee kolommen: brede kolom voor 'Bekijk analyse', smalle kolom voor verwijder-knop
                col_link, col_del = st.columns([9, 1])
                with col_link:
                    if st.button("Bekijk analyse", key=f"view_analysis_{item['id']}", type="primary"):
                        st.query_params["analysis_id"] = str(item['id'])
                        st.session_state['current_analysis_id'] = str(item['id'])
                        st.switch_page(f"{st.session_state['page_navigation_dir']}/analysis_results/overview.py")
                with col_del:
                    if st.button("✕", key=f"delete_analysis_{item['id']}"):
                        st.session_state["_pending_delete_analysis"] = item
                        confirm_delete_analysis()
                