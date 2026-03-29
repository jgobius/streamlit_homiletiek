import time

import requests
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
from page_navigation.analysis_results.analyses.sociaal_maatschappelijk import sociaal_maatschappelijk
from page_navigation.analysis_results.analyses.waardenorientatie import waardenorientatie
from page_navigation.analysis_results.analyses.geloofsorientatie import geloofsorientatie
from page_navigation.analysis_results.analyses.interpretatieve_synthese import interpretatieve_synthese
from page_navigation.analysis_results.analyses.actueel_nieuws import actueel_nieuws
from page_navigation.analysis_results.analyses.focus_en_functie import focus_en_functie
from page_navigation.analysis_results.analyses.representatieve_hoorders import representatieve_hoorders
from page_navigation.analysis_results.analyses.illustraties import illustraties
from page_navigation.analysis_results.analyses.politieke_orientatie import politieke_orientatie

REANALYSIS_LOCK_TIMEOUT_SECONDS = 30


def _reanalysis_is_locked(lock_key: str) -> bool:
    lock_time = st.session_state.get(lock_key)
    if lock_time is None:
        return False
    if time.time() - lock_time > REANALYSIS_LOCK_TIMEOUT_SECONDS:
        del st.session_state[lock_key]
        return False
    return True


def _release_reanalysis_lock(lock_key: str) -> None:
    st.session_state.pop(lock_key, None)


def _deps_ok(at: dict, latest: dict) -> tuple[bool, list[str]]:
    """Geeft (True, []) als alle vereiste analyses aanwezig zijn, anders (False, [display namen])."""
    deps = at.get("depends_on") or []
    missing = []
    for dep in deps:
        dep_name = dep.get("name") if isinstance(dep, dict) else dep
        dep_label = dep.get("front_end_name") if isinstance(dep, dict) else dep_name
        if dep_name and dep_name not in latest:
            missing.append(dep_label or dep_name)
    return (len(missing) == 0, missing)


redirect_to_login()

analysis_id = st.query_params.get('analysis_id') or st.session_state.get('current_analysis_id')

with st.sidebar:
    st.page_link(label="< Terug", page=f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py")

if not analysis_id:
    st.warning("Geen analyse geselecteerd. Ga terug naar het overzicht en selecteer een analyse.")
    st.stop()

# Ensure it's stored in session state for consistency when navigating between internal results
st.session_state['current_analysis_id'] = analysis_id

analysis_results = get_data(f"api/analysis-results?sermon_analysis_id={analysis_id}")
sermon_analysis = get_data(f"api/sermon-analyses/{analysis_id}/")

if sermon_analysis:
    # Set the sermon-wide extra context in session state for easy access across the page
    st.session_state["extra_context"] = sermon_analysis.get("extra_context", "")

# Houd per analysis_type alleen de nieuwste (hoogste id).
latest: dict[str, dict] = {}
for r in analysis_results:
    name = r['analysis_type']['name']
    if name not in latest or r['id'] > latest[name]['id']:
        latest[name] = r

other_results = [r for name, r in latest.items() if name != "postille"]
summary = other_results + ([latest["postille"]] if "postille" in latest else [])

if "selected_analysis_id" not in st.session_state or st.session_state["selected_analysis_id"] not in {r["id"] for r in summary}:
    st.session_state["selected_analysis_id"] = summary[0]["id"] if summary else None

all_analysis_types = get_data("api/analysis-types/")
missing_types = sorted(
    [at for at in all_analysis_types if at.get("front_end_name") and at["name"] not in latest],
    key=lambda x: x.get("order", 99),
)

with st.sidebar:
    for r in summary:
        label = r["analysis_type"]["front_end_name"]
        is_selected = r["id"] == st.session_state["selected_analysis_id"]
        btn_type = "primary" if is_selected else "secondary"
        if st.button(label, key=f"nav_{r['id']}", use_container_width=True, type=btn_type):
            st.session_state["selected_analysis_id"] = r["id"]
            st.rerun()

    if missing_types:
        st.divider()
        with st.expander("Analyse toevoegen"):
            for at in missing_types:
                _add_lock_key = f"analysis_add_lock_{analysis_id}_{at['name']}"
                _add_locked = _reanalysis_is_locked(_add_lock_key)
                _ok, _ontbr = _deps_ok(at, latest)
                _label = f"🔒 {at['front_end_name']}" if not _ok else at["front_end_name"]
                _help = ("Vereist eerst: " + ", ".join(_ontbr)) if not _ok else None
                if st.button(_label, key=f"add_{at['name']}", use_container_width=True,
                             disabled=_add_locked or not _ok, help=_help):
                    st.session_state[_add_lock_key] = time.time()
                    try:
                        agent_url = st.secrets["API_AGENT_URL"].rstrip("/")
                        response = requests.post(
                            f"{agent_url}/run_single_analysis/",
                            json={
                                "sermon_analysis_id": int(analysis_id),
                                "analysis_type_name": at["name"],
                            },
                            timeout=30,
                        )
                        response.raise_for_status()
                        st.toast(f"'{at['front_end_name']}' wordt uitgevoerd. Ververs de pagina over enkele minuten.")
                    except requests.exceptions.HTTPError as e:
                        if e.response is not None and e.response.status_code == 409:
                            st.warning(e.response.json().get("detail", "Al gestart, wacht even."))
                        else:
                            _release_reanalysis_lock(_add_lock_key)
                            st.error(f"Fout: {e}")
                    except Exception as e:
                        _release_reanalysis_lock(_add_lock_key)
                        st.error(f"Fout: {e}")

if not analysis_results:
    st.info("Bijbelteksten wordt geanalyseerd. Ververs de pagina over enkele minuten.")
    st.stop()

selected_analysis = next((r for r in summary if r["id"] == st.session_state["selected_analysis_id"]), None)

@st.dialog("Analyse-element verwijderen")
def confirm_delete_result(result: dict) -> None:
    label = result["analysis_type"]["front_end_name"]
    st.write(f"Weet je zeker dat je **'{label}'** wilt verwijderen? Dit kan niet ongedaan worden gemaakt.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ja, verwijderen", type="primary", use_container_width=True):
            try:
                handler = st.session_state['api_handler']
                sermon_analysis_id = result["sermon_analysis"]["id"]
                url = f"{handler.base_url}/api/analysis-results/{result['id']}/?sermon_analysis_id={sermon_analysis_id}"
                headers = {"Authorization": f"Bearer {handler.jwt_handler.token}"}
                requests.delete(url, headers=headers).raise_for_status()
                st.session_state.pop("selected_analysis_id", None)
                st.rerun()
            except Exception as e:
                st.error(f"Fout bij verwijderen: {e}")
    with col2:
        if st.button("Annuleren", use_container_width=True):
            st.rerun()


@st.dialog("Analyse opnieuw uitvoeren")
def confirm_rerun_analysis(sermon_analysis_id: int, analysis_type_name: str, front_end_name: str) -> None:
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


col_del, col_rerun, col_ctx = st.columns([3, 3, 4])
with col_del:
    if selected_analysis and st.button("Verwijder", icon="🗑️", use_container_width=True):
        confirm_delete_result(selected_analysis)
with col_rerun:
    if st.button("Opnieuw", icon="🔄", use_container_width=True):
        if selected_analysis and selected_analysis["analysis_type"]["name"] == "liedsuggesties":
            confirm_rerun_liedsuggesties(sermon_analysis_id=int(analysis_id))
        else:
            confirm_rerun_analysis(
                sermon_analysis_id=int(analysis_id),
                analysis_type_name=selected_analysis["analysis_type"]["name"] if selected_analysis else "",
                front_end_name=selected_analysis["analysis_type"]["front_end_name"] if selected_analysis else "",
            )
with col_ctx:
    if st.button("Aanpassen", icon="✏️", use_container_width=True):
        aanpassen_dialog(selected_analysis)

if st.session_state.get("extra_context"):
    st.info(f"**Extra context:** {st.session_state['extra_context']}")

if not selected_analysis:
    st.stop()

st.header(selected_analysis["analysis_type"]["front_end_name"])

analysis_type_name = selected_analysis.get("analysis_type", {}).get("name", "")

if analysis_type_name == "postille":
    postille(selected_analysis, latest_results=latest)
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
elif analysis_type_name == "sociaal_maatschappelijk":
    sociaal_maatschappelijk(selected_analysis)
elif analysis_type_name == "waardenorientatie":
    waardenorientatie(selected_analysis)
elif analysis_type_name == "geloofsorientatie":
    geloofsorientatie(selected_analysis)
elif analysis_type_name == "interpretatieve_synthese":
    interpretatieve_synthese(selected_analysis)
elif analysis_type_name == "actueel_nieuws":
    actueel_nieuws(selected_analysis)
elif analysis_type_name == "focus_en_functie":
    focus_en_functie(selected_analysis)
elif analysis_type_name == "representatieve_hoorders":
    representatieve_hoorders(selected_analysis)
elif analysis_type_name == "illustraties":
    illustraties(selected_analysis)
elif analysis_type_name == "politieke_orientatie":
    politieke_orientatie(selected_analysis)


