import time

import requests
import streamlit as st

from src.utils.utils import redirect_to_login, get_data
from page_navigation.analysis_results.aanpassen_dialog import aanpassen_dialog
from page_navigation.analysis_results.analyses.contextduiding import contextduiding

REANALYSIS_LOCK_TIMEOUT_SECONDS = 30

_PERSPECTIEVEN_NAMEN = {
    "filosofie", "culturele_antropologie", "receptiegeschiedenis",
    "literaire_theorie", "psychologie", "ecologie", "postkoloniaal",
    "rechtswetenschap", "natuurwetenschappen", "politieke_speltheorie",
    "mystagogiek", "gender_queer_body", "digitale_cultuur", "ruimtelijke_ordening",
}


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
    deps = at.get("depends_on") or []
    missing = []
    for dep in deps:
        dep_name = dep.get("name") if isinstance(dep, dict) else dep
        dep_label = dep.get("front_end_name") if isinstance(dep, dict) else dep_name
        if dep_name and dep_name not in latest:
            missing.append(dep_label or dep_name)
    return (len(missing) == 0, missing)


redirect_to_login()

analysis_id = st.query_params.get("analysis_id") or st.session_state.get("current_analysis_id")

with st.sidebar:
    st.page_link(label="< Terug", page=f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py")

if not analysis_id:
    st.warning("Geen analyse geselecteerd. Ga terug naar het overzicht en selecteer een analyse.")
    st.stop()

st.session_state["current_analysis_id"] = analysis_id

analysis_results = get_data(f"api/analysis-results?sermon_analysis_id={analysis_id}")

# Houd per analysis_type alleen de nieuwste (hoogste id).
latest: dict[str, dict] = {}
for r in analysis_results:
    name = r["analysis_type"]["name"]
    if name not in latest or r["id"] > latest[name]["id"]:
        latest[name] = r

perspect_summary = [r for r in latest.values() if r["analysis_type"]["name"] in _PERSPECTIEVEN_NAMEN]

all_analysis_types = get_data("api/analysis-types/")
perspect_missing = sorted(
    [at for at in all_analysis_types
     if at.get("front_end_name") and at["name"] in _PERSPECTIEVEN_NAMEN and at["name"] not in latest],
    key=lambda x: x.get("order", 99),
)

if "selected_perspect_id" not in st.session_state or \
        st.session_state["selected_perspect_id"] not in {r["id"] for r in perspect_summary}:
    st.session_state["selected_perspect_id"] = perspect_summary[0]["id"] if perspect_summary else None

with st.sidebar:
    for r in perspect_summary:
        label = r["analysis_type"]["front_end_name"]
        is_selected = r["id"] == st.session_state["selected_perspect_id"]
        btn_type = "primary" if is_selected else "secondary"
        if st.button(label, key=f"pnav_{r['id']}", use_container_width=True, type=btn_type):
            st.session_state["selected_perspect_id"] = r["id"]
            st.rerun()

    if perspect_missing:
        with st.expander("Perspectief toevoegen"):
            for at in perspect_missing:
                _add_lock_key = f"analysis_add_lock_{analysis_id}_{at['name']}"
                _add_locked = _reanalysis_is_locked(_add_lock_key)
                _ok, _ontbr = _deps_ok(at, latest)
                _label = f"🔒 {at['front_end_name']}" if not _ok else at["front_end_name"]
                _help = ("Vereist eerst: " + ", ".join(_ontbr)) if not _ok else None
                if st.button(_label, key=f"padd_{at['name']}", use_container_width=True,
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

if not perspect_summary:
    st.info("Nog geen perspectieven beschikbaar. Voeg ze toe via 'Perspectief toevoegen' in de zijbalk.")
    st.stop()

selected_analysis = next(
    (r for r in perspect_summary if r["id"] == st.session_state["selected_perspect_id"]), None
)

if not selected_analysis:
    st.stop()


@st.dialog("Analyse-element verwijderen")
def confirm_delete_result(result: dict) -> None:
    label = result["analysis_type"]["front_end_name"]
    st.write(f"Weet je zeker dat je **'{label}'** wilt verwijderen? Dit kan niet ongedaan worden gemaakt.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ja, verwijderen", type="primary", use_container_width=True):
            try:
                handler = st.session_state["api_handler"]
                sermon_analysis_id = result["sermon_analysis"]["id"]
                url = f"{handler.base_url}/api/analysis-results/{result['id']}/?sermon_analysis_id={sermon_analysis_id}"
                headers = {"Authorization": f"Bearer {handler.jwt_handler.token}"}
                requests.delete(url, headers=headers).raise_for_status()
                st.session_state.pop("selected_perspect_id", None)
                st.rerun()
            except Exception as e:
                st.error(f"Fout bij verwijderen: {e}")
    with col2:
        if st.button("Annuleren", use_container_width=True):
            st.rerun()


@st.dialog("Perspectief opnieuw uitvoeren")
def confirm_rerun(sermon_analysis_id: int, analysis_type_name: str, front_end_name: str) -> None:
    st.write(f"Weet je zeker dat je **'{front_end_name}'** opnieuw wilt uitvoeren? Dit kan enkele minuten duren.")
    _lock_key = f"analysis_rerun_lock_{sermon_analysis_id}_{analysis_type_name}"
    _locked = _reanalysis_is_locked(_lock_key)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ja, opnieuw uitvoeren", type="primary", use_container_width=True, disabled=_locked):
            st.session_state[_lock_key] = time.time()
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
                    _release_reanalysis_lock(_lock_key)
                    st.error(f"Fout bij starten analyse: {e}")
            except Exception as e:
                _release_reanalysis_lock(_lock_key)
                st.error(f"Fout bij starten analyse: {e}")
    with col2:
        if st.button("Annuleren", use_container_width=True):
            st.rerun()


col_del, col_rerun, col_ctx = st.columns([3, 3, 4])
with col_del:
    if st.button("Verwijder", icon="🗑️", use_container_width=True):
        confirm_delete_result(selected_analysis)
with col_rerun:
    if st.button("Opnieuw", icon="🔄", use_container_width=True):
        confirm_rerun(
            sermon_analysis_id=int(analysis_id),
            analysis_type_name=selected_analysis["analysis_type"]["name"],
            front_end_name=selected_analysis["analysis_type"]["front_end_name"],
        )
with col_ctx:
    if st.button("Aanpassen", icon="✏️", use_container_width=True):
        aanpassen_dialog(selected_analysis)

st.header(selected_analysis["analysis_type"]["front_end_name"])
contextduiding(selected_analysis)
