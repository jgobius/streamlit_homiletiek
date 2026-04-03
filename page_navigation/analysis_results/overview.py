import requests
import time

import streamlit as st

from src.utils.utils import redirect_to_login, get_data
from page_navigation.analysis_results.aanpassen_dialog import aanpassen_dialog
from page_navigation.analysis_results.analyses.postille import postille
from page_navigation.analysis_results.analyses.bijbelteksten import bijbelteksten
from page_navigation.analysis_results.analyses.liturgisch_jaar import liturgisch_jaar
from page_navigation.analysis_results.analyses.liedsuggesties import liedsuggesties
from page_navigation.analysis_results.analyses.structuralistische_exegese import structuralistische_exegese
from page_navigation.analysis_results.analyses.commentaren import commentaren
from page_navigation.analysis_results.analyses.theologie import theologie

# Aantal seconden dat een heranalyse-knop geblokkeerd blijft na het indienen
REANALYSIS_LOCK_TIMEOUT_SECONDS = 30


def _reanalysis_is_locked(lock_key: str) -> bool:
    """Controleer of een heranalyse momenteel geblokkeerd is (te snel opnieuw aangevraagd)."""
    lock_time = st.session_state.get(lock_key)
    if lock_time is None:
        return False
    if time.time() - lock_time > REANALYSIS_LOCK_TIMEOUT_SECONDS:
        del st.session_state[lock_key]
        return False
    return True


def _release_reanalysis_lock(lock_key: str) -> None:
    """Verwijder een heranalyse-blokkade na een fout zodat de knop weer bruikbaar is."""
    st.session_state.pop(lock_key, None)


redirect_to_login()

# Sla analysis_id op als variabele zodat dialogen hem kunnen gebruiken
analysis_id = st.query_params.get('analysis_id')
analysis_results = get_data(f"api/analysis-results?sermon_analysis_id={analysis_id}")


summary  = [r for r in analysis_results if r['analysis_type']['name'] == "postille"]
other_results = [r for r in analysis_results if r['id'] != summary[0]['id']]
summary.extend(other_results)


with st.sidebar:
    st.page_link(label="< Terug", page=f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py")

    selected_analysis = st.radio(
        "Analyse",
        options=summary,
        format_func=lambda x: x['analysis_type']['front_end_name'],
        label_visibility="collapsed",
    )


@st.dialog("Analyse-element verwijderen")
def confirm_delete_result(result: dict) -> None:
    """Bevestigingsdialoog voor het permanent verwijderen van een analyseresultaat."""
    label = result["analysis_type"]["front_end_name"]
    st.write(f"Weet je zeker dat je **'{label}'** wilt verwijderen? Dit kan niet ongedaan worden gemaakt.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ja, verwijderen", type="primary", use_container_width=True):
            try:
                handler = st.session_state['api_handler']
                sermon_analysis_id = result["sermon_analysis"]["id"]
                # Bouw de verwijder-URL op met het sermon_analysis_id als query-parameter
                url = f"{handler.base_url}/api/analysis-results/{result['id']}/?sermon_analysis_id={sermon_analysis_id}"
                headers = {"Authorization": f"Bearer {handler.jwt_handler.token}"}
                requests.delete(url, headers=headers).raise_for_status()
                st.rerun()
            except Exception as e:
                st.error(f"Fout bij verwijderen: {e}")
    with col2:
        if st.button("Annuleren", use_container_width=True):
            st.rerun()


@st.dialog("Analyse opnieuw uitvoeren")
def confirm_rerun_analysis(sermon_analysis_id: int, analysis_type_name: str, front_end_name: str) -> None:
    """Bevestigingsdialoog voor het opnieuw uitvoeren van een analyse via de agent."""
    st.write(f"Weet je zeker dat je **'{front_end_name}'** opnieuw wilt uitvoeren? Dit kan enkele minuten duren.")
    _rerun_lock_key = f"analysis_rerun_lock_{sermon_analysis_id}_{analysis_type_name}"
    _rerun_locked = _reanalysis_is_locked(_rerun_lock_key)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ja, opnieuw uitvoeren", type="primary", use_container_width=True, disabled=_rerun_locked):
            st.session_state[_rerun_lock_key] = time.time()
            try:
                agent_url = st.secrets["API_AGENT_URL"].rstrip("/")
                response = requests.post(
                    f"{agent_url}/run_single_analysis/",
                    json={
                        "sermon_analysis_id": sermon_analysis_id,
                        "analysis_type_name": analysis_type_name,
                    },
                    timeout=10,
                )
                response.raise_for_status()
                st.toast(f"'{front_end_name}' wordt opnieuw uitgevoerd. Ververs de pagina over enkele minuten.")
                st.rerun()
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 409:
                    st.warning(e.response.json().get("detail", "Al gestart, wacht even."))
                else:
                    _release_reanalysis_lock(_rerun_lock_key)
                    st.error(f"Fout bij starten analyse: {e}")
            except Exception as e:
                _release_reanalysis_lock(_rerun_lock_key)
                st.error(f"Fout bij starten analyse: {e}")
    with col2:
        if st.button("Annuleren", use_container_width=True):
            st.rerun()


@st.dialog("Liedsuggesties opnieuw uitvoeren")
def confirm_rerun_liedsuggesties(sermon_analysis_id: int) -> None:
    """Dialoog voor het opnieuw uitvoeren van liedsuggesties met keuze van liedbundels."""
    all_books = get_data("api/song-books/")
    selected = st.multiselect(
        "Selecteer liedbundels (20 suggesties per bundel):",
        options=all_books,
        format_func=lambda b: b["name"],
    )
    _lied_lock_key = f"analysis_rerun_lock_{sermon_analysis_id}_liedsuggesties"
    _lied_locked = _reanalysis_is_locked(_lied_lock_key)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Uitvoeren", type="primary", use_container_width=True, disabled=_lied_locked):
            if not selected:
                st.warning("Selecteer minimaal één liedbundel.")
                return
            st.session_state[_lied_lock_key] = time.time()
            try:
                agent_url = st.secrets["API_AGENT_URL"].rstrip("/")
                response = requests.post(
                    f"{agent_url}/run_single_analysis/",
                    json={
                        "sermon_analysis_id": sermon_analysis_id,
                        "analysis_type_name": "liedsuggesties",
                        "song_books": [b["id"] for b in selected],
                    },
                    timeout=10,
                )
                response.raise_for_status()
                st.toast("Liedsuggesties worden opnieuw uitgevoerd. Ververs de pagina over enkele minuten.")
                st.rerun()
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 409:
                    st.warning(e.response.json().get("detail", "Al gestart, wacht even."))
                else:
                    _release_reanalysis_lock(_lied_lock_key)
                    st.error(f"Fout bij starten analyse: {e}")
            except Exception as e:
                _release_reanalysis_lock(_lied_lock_key)
                st.error(f"Fout bij starten analyse: {e}")
    with col2:
        if st.button("Annuleren", use_container_width=True):
            st.rerun()


# Toon de naam van de geselecteerde analyse als paginatitel
st.header(selected_analysis["analysis_type"]["front_end_name"])

# Vier actieknoppen onder de titel: Verwijder, Opnieuw, Aanpassen, Informatie
col_del, col_rerun, col_ctx, col_info = st.columns([3, 3, 3, 1])
with col_del:
    if st.button("Verwijder", icon="🗑️"):
        confirm_delete_result(selected_analysis)
with col_rerun:
    # Liedsuggesties heeft een eigen dialoog met bundelselectie
    if st.button("Opnieuw", icon="🔄"):
        if selected_analysis["analysis_type"]["name"] == "liedsuggesties":
            confirm_rerun_liedsuggesties(sermon_analysis_id=int(analysis_id))
        else:
            confirm_rerun_analysis(
                sermon_analysis_id=int(analysis_id),
                analysis_type_name=selected_analysis["analysis_type"]["name"],
                front_end_name=selected_analysis["analysis_type"]["front_end_name"],
            )
with col_ctx:
    if st.button("Aanpassen", icon="✏️"):
        aanpassen_dialog(selected_analysis)
with col_info:
    # Beschrijving komt uit de database via het analysis_type-object
    _desc = selected_analysis["analysis_type"].get("description")
    if _desc:
        with st.popover("ℹ️", use_container_width=False):
            st.markdown(_desc)

analysis_type_name = selected_analysis.get("analysis_type", {}).get("name", "")

if analysis_type_name == "postille":
    postille(selected_analysis)
elif analysis_type_name == "bijbelteksten":
    bijbelteksten(selected_analysis)
elif analysis_type_name == "liturgisch_jaar":
    liturgisch_jaar(selected_analysis)
elif analysis_type_name == "liedsuggesties":
    liedsuggesties(selected_analysis)
elif analysis_type_name == "structuralistische_exegese":
    structuralistische_exegese(selected_analysis)
elif analysis_type_name == "commentaries":
    commentaren(selected_analysis)
elif analysis_type_name == "theology":
    theologie(selected_analysis)
