from datetime import datetime
from typing import Any

import streamlit as st

from src.utils.utils import redirect_to_login, get_data, render_sidebar

redirect_to_login()

render_sidebar()

def format_title(title: str | None, congregation: str, sermon_date: str) -> str:
    if title:
        return f"{title} - {congregation} - {sermon_date}"

    return f"{congregation} - {sermon_date}"

def set_analysis_id(analysis_id: int) -> None:
    st.session_state.selected_analysis_id = analysis_id


@st.dialog("Analyse verwijderen")
def confirm_delete_analysis() -> None:
    # Haal het te verwijderen item op uit session_state.
    item = st.session_state.get("_pending_delete_analysis")
    if not item:
        st.rerun()
    label = item.get('title') or f"{item['church']['name']} - {datetime.strptime(item['sermon_date'], '%Y-%m-%d').strftime('%d-%m-%Y')}"
    st.write(f"Weet je zeker dat je de analyse **'{label}'** wilt verwijderen? Dit kan niet ongedaan worden gemaakt.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ja, verwijderen", type="primary", use_container_width=True):
            try:
                handler = st.session_state['api_handler']
                handler.delete(f"api/sermon-analyses/{item['id']}/")
                st.session_state.pop("_pending_delete_analysis", None)
                # Markeer cache als vervuild zodat de lijst opnieuw opgehaald wordt.
                st.session_state["dashboard_data_dirty"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Fout bij verwijderen: {e}")
    with col2:
        if st.button("Annuleren", use_container_width=True):
            st.session_state.pop("_pending_delete_analysis", None)
            st.rerun()


# Cache de lijst om te voorkomen dat elke klik een API-roundtrip veroorzaakt.
# De vlag `dashboard_data_dirty` wordt gezet na aanmaken of verwijderen van een analyse.
if st.session_state.pop("dashboard_data_dirty", False) or "dashboard_analyses_cache" not in st.session_state:
    st.session_state["dashboard_analyses_cache"] = get_data("api/sermon-analyses/")
analysis = st.session_state["dashboard_analyses_cache"]

st.title("Kerkdienstanalyses")
st.write("Overzicht van alle kerkdienstanalyses.")

# Toon eerst de bestaande analyses, daarna de knop om een nieuwe te starten.
if len(analysis) == 0:
    st.info("Er zijn nog geen kerkdienstanalyses gestart.")
else:
    with st.container():
        for item in analysis:
            id = item["id"]
            status = item["status"]
            title = item["title"]
            congregation = item["church"]["name"]
            sermon_date = datetime.strptime(item["sermon_date"], "%Y-%m-%d").strftime(
                "%d-%m-%Y"
            )
            # Brede kolom voor de analyse-knop, smalle kolom voor de verwijder-knop.
            col_btn, col_del = st.columns([9, 1])
            with col_btn:
                st.button(
                    f"{format_title(title, congregation, sermon_date)}",
                    type="secondary",
                    key=item["id"],
                    use_container_width=True,
                    on_click=lambda id=id: set_analysis_id(id)
                )
            with col_del:
                # Verwijder-knop: sla het item op in session_state en open de bevestigingsdialoog.
                if st.button("✕", key=f"delete_{item['id']}", help="Verwijder analyse"):
                    st.session_state["_pending_delete_analysis"] = item
                    confirm_delete_analysis()

new_analysis = st.button("Nieuwe analyse", type="primary")

if new_analysis:
    st.switch_page(
        f"{st.session_state['page_navigation_dir']}/analyses/new_analysis.py"
    )

if "selected_analysis_id" in st.session_state:
    analysis_id = st.session_state.selected_analysis_id
    del st.session_state.selected_analysis_id
    # Navigeer alleen als het ID een geldig geheel getal is; een None-waarde
    # zou ?analysis_id=None in de URL produceren en de overzichtspagina laten crashen.
    if analysis_id is not None:
        st.switch_page(
            f'{st.session_state["page_navigation_dir"]}/analysis_results/overview.py',
            query_params={"analysis_id": analysis_id}
        )