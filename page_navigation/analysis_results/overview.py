import json
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
from page_navigation.analysis_results.analyses.contextduiding import contextduiding
from page_navigation.analysis_results.analyses.verdieping import verdieping
from page_navigation.analysis_results.analyses.preekschets import preekschets
from page_navigation.analysis_results.analyses.feedback_analyse import feedback_analyse
from page_navigation.analysis_results.analyses.volledige_preek import volledige_preek
from src.components.user_feedback import render_feedback_trigger

# --- Categorisatie van analyse-types per tabblad ---
REANALYSIS_LOCK_TIMEOUT_SECONDS = 30

_PERSPECTIEVEN_NAMEN = {
    "filosofie", "culturele_antropologie", "receptiegeschiedenis",
    "literaire_theorie", "psychologie", "ecologie", "postkoloniaal",
    "rechtswetenschap", "natuurwetenschappen", "politieke_speltheorie",
    "mystagogiek", "gender_queer_body", "digitale_cultuur", "ruimtelijke_ordening",
}

_VERDIEPING_NAMEN = {
    "gebeden", "gebeden_profetisch", "gebeden_dialogisch", "gebeden_eenvoudig",
    "homiletische_lowry", "homiletische_buttrick", "kunst_cultuur",
    "kindermoment", "wetslezing", "kalender", "bezinningsmoment",
}

_PREEKSCHETSEN_NAMEN = {
    "preek_jungel", "preek_fleming_rutledge", "preek_brueggemann_poet",
    "preek_literair", "preek_noordmans", "preek_kosuke_koyama",
    "preek_zornberg", "preek_brueggemann", "preek_drewermann",
    "preek_gardner_taylor", "preek_solle", "preek_peterson", "preek_standup",
}

_FEEDBACK_NAMEN = {
    "volledige_preek",
    "feedback_adversarial", "feedback_dekker", "feedback_aristoteles",
    "feedback_kolb", "feedback_schulz_von_thun", "feedback_transactional",
    "feedback_esthetiek", "feedback_metafoor", "feedback_narratief",
    "feedback_taalhandeling",
}

# Alle niet-basis namen, gebruikt om basis-analyses te filteren.
_ALL_NON_BASIS = _PERSPECTIEVEN_NAMEN | _VERDIEPING_NAMEN | _PREEKSCHETSEN_NAMEN | _FEEDBACK_NAMEN

_TABS = ["Basis", "Verdieping", "Perspectieven", "Preekschetsen", "Feedback"]

# Gewenste volgorde van basis-analyses in de zijbalk (conform develop-versie).
_BASIS_ORDER = [
    "bijbelteksten",
    "liturgisch_jaar",
    "structuralistische_exegese",
    "theology",
    "commentaries",
    "liedsuggesties",
    "sociaal_maatschappelijk",
    "waardenorientatie",
    "geloofsorientatie",
    "interpretatieve_synthese",
    "politieke_orientatie",
    "representatieve_hoorders",
    "illustraties",
    "actueel_nieuws",
    "focus_en_functie",
    "postille",
]


def _basis_sort_key(name: str) -> int:
    try:
        return _BASIS_ORDER.index(name)
    except ValueError:
        return len(_BASIS_ORDER)


def _deps_ok(at: dict, latest: dict) -> tuple[bool, list[str]]:
    """Geeft (True, []) als alle vereiste analyses aanwezig zijn, anders (False, [display namen])."""
    deps = at.get("depends_on") or []
    ontbrekend = []
    for dep in deps:
        dep_name = dep.get("name") if isinstance(dep, dict) else dep
        dep_label = dep.get("front_end_name") if isinstance(dep, dict) else dep_name
        if dep_name and dep_name not in latest:
            ontbrekend.append(dep_label or dep_name)
    return (len(ontbrekend) == 0, ontbrekend)
_TABS = ["Basis", "Verdieping", "Perspectieven", "Preekschetsen", "Feedback"]

_BASIS_ORDER = [
    "bijbelteksten",
    "liturgisch_jaar",
    "structuralistische_exegese",
    "theology",
    "commentaries",
    "liedsuggesties",
    "sociaal_maatschappelijk",
    "waardenorientatie",
    "geloofsorientatie",
    "interpretatieve_synthese",
    "politieke_orientatie",
    "representatieve_hoorders",
    "illustraties",
    # overige basis-items — worden achteraan geplaatst
    "actueel_nieuws",
    "focus_en_functie",
    "postille",
]

def _basis_sort_key(name: str) -> int:
    try:
        return _BASIS_ORDER.index(name)
    except ValueError:
        return len(_BASIS_ORDER)


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


def _trigger_analysis(analysis_id: int, at: dict, lock_key: str) -> None:
    """Stuur een verzoek naar de agent om een analyse uit te voeren."""
    st.session_state[lock_key] = time.time()
    try:
        agent_url = st.secrets["API_AGENT_URL"].rstrip("/")
        response = requests.post(
            f"{agent_url}/run_single_analysis/",
            json={
                "sermon_analysis_id": analysis_id,
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
            _release_reanalysis_lock(lock_key)
            st.error(f"Fout: {e}")
    except Exception as e:
        _release_reanalysis_lock(lock_key)
        st.error(f"Fout: {e}")


def _trigger_preekschets(analysis_id: int, at: dict, lock_key: str) -> None:
    """Stuur een verzoek naar de agent om een preekschets uit te voeren (met opgeslagen selectie)."""
    st.session_state[lock_key] = time.time()
    try:
        selectie = st.session_state.get(f"preek_selectie_{analysis_id}", {})
        kernteksten = selectie.get("kernteksten", [])
        focus_optie = selectie.get("focus_optie")
        selected_perspectieven = selectie.get("perspectieven", {})
        selected_illustraties = selectie.get("illustraties", [])
        selected_hoorders = selectie.get("hoorders", [])
        agent_url = st.secrets["API_AGENT_URL"].rstrip("/")
        response = requests.post(
            f"{agent_url}/run_single_analysis/",
            json={
                "sermon_analysis_id": int(analysis_id),
                "analysis_type_name": at["name"],
                "core_text": kernteksten,
                "focus_optie": focus_optie,
                "selected_perspectieven": selected_perspectieven,
                "selected_illustraties": selected_illustraties,
                "selected_hoorders": selected_hoorders,
            },
            timeout=30,
        )
        response.raise_for_status()
        st.toast(f"'{at['front_end_name']}' wordt uitgevoerd. Ververs de pagina over enkele minuten.")
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 409:
            st.warning(e.response.json().get("detail", "Al gestart, wacht even."))
        else:
            _release_reanalysis_lock(lock_key)
            st.error(f"Fout: {e}")
    except Exception as e:
        _release_reanalysis_lock(lock_key)
        st.error(f"Fout: {e}")


def _render_preekschets_result(selected_preek: dict, latest: dict) -> None:
    """Dispatch op basis van aanwezigheid preek_onderdelen in result."""
    result = selected_preek.get("result", {})
    if isinstance(result, dict) and result.get("preek_onderdelen"):
        preekschets(selected_preek)
    else:
        postille(selected_preek, latest_results=latest)


redirect_to_login()

# Haal analysis_id op uit query-params of session_state.
analysis_id = st.query_params.get('analysis_id') or st.session_state.get('current_analysis_id')

with st.sidebar:
    st.page_link(label="< Terug", page=f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py")

if not analysis_id:
    st.warning("Geen analyse geselecteerd. Ga terug naar het overzicht en selecteer een analyse.")
    st.stop()

st.session_state['current_analysis_id'] = analysis_id

analysis_results = get_data(f"api/analysis-results?sermon_analysis_id={analysis_id}")

# Houd per analysis_type alleen de nieuwste (hoogste id).
latest: dict[str, dict] = {}
for r in analysis_results:
    name = r['analysis_type']['name']
    if name not in latest or r['id'] > latest[name]['id']:
        latest[name] = r

# Splits resultaten op per tabblad, gesorteerd op de gewenste volgorde.
_order_key = lambda r: r["analysis_type"].get("order", 99)
analyse_summary  = sorted(
    [r for r in latest.values() if r["analysis_type"]["name"] not in _ALL_NON_BASIS],
    key=lambda r: _basis_sort_key(r["analysis_type"]["name"]),
)
verdiep_summary  = sorted([r for r in latest.values() if r["analysis_type"]["name"] in _VERDIEPING_NAMEN], key=_order_key)
perspect_summary = sorted([r for r in latest.values() if r["analysis_type"]["name"] in _PERSPECTIEVEN_NAMEN], key=_order_key)
preek_summary    = sorted([r for r in latest.values() if r["analysis_type"]["name"] in _PREEKSCHETSEN_NAMEN], key=_order_key)
feedback_summary = sorted([r for r in latest.values() if r["analysis_type"]["name"] in _FEEDBACK_NAMEN], key=_order_key)
# volledige_preek wordt niet in de navigatie getoond, maar apart beheerd.
feedback_nav_summary = [r for r in feedback_summary if r["analysis_type"]["name"] != "volledige_preek"]

# Haal alle bekende analyse-types op om vergrendelde knoppen te tonen voor
# analyses die nog niet gedraaid zijn.
if "all_analysis_types_cache" not in st.session_state:
    st.session_state["all_analysis_types_cache"] = get_data("api/analysis-types/") or []
all_analysis_types: list = st.session_state["all_analysis_types_cache"]

# Typen die nog niet in de resultaten zitten.
missing_types = sorted(
    [at for at in all_analysis_types if at.get("front_end_name") and at["name"] not in latest],
    key=lambda x: x.get("order", 99),
)
analyse_missing      = sorted([at for at in missing_types if at["name"] not in _ALL_NON_BASIS], key=lambda at: _basis_sort_key(at["name"]))
verdiep_missing      = [at for at in missing_types if at["name"] in _VERDIEPING_NAMEN]
perspect_missing     = [at for at in missing_types if at["name"] in _PERSPECTIEVEN_NAMEN]
preek_missing        = [at for at in missing_types if at["name"] in _PREEKSCHETSEN_NAMEN]
feedback_nav_missing = [at for at in missing_types if at["name"] in _FEEDBACK_NAMEN and at["name"] != "volledige_preek"]

# Bewaar geselecteerde analyse-id per tabblad in session_state.
if "selected_analysis_id" not in st.session_state or \
        st.session_state["selected_analysis_id"] not in {r["id"] for r in analyse_summary}:
    st.session_state["selected_analysis_id"] = analyse_summary[0]["id"] if analyse_summary else None

if "selected_verdiep_id" not in st.session_state or \
        st.session_state["selected_verdiep_id"] not in {r["id"] for r in verdiep_summary}:
    st.session_state["selected_verdiep_id"] = verdiep_summary[0]["id"] if verdiep_summary else None

if "selected_perspect_id" not in st.session_state or \
        st.session_state["selected_perspect_id"] not in {r["id"] for r in perspect_summary}:
    st.session_state["selected_perspect_id"] = perspect_summary[0]["id"] if perspect_summary else None

if "selected_preek_id" not in st.session_state or \
        st.session_state["selected_preek_id"] not in {r["id"] for r in preek_summary}:
    st.session_state["selected_preek_id"] = preek_summary[0]["id"] if preek_summary else None

if "selected_feedback_id" not in st.session_state or \
        st.session_state["selected_feedback_id"] not in {r["id"] for r in feedback_nav_summary}:
    st.session_state["selected_feedback_id"] = feedback_nav_summary[0]["id"] if feedback_nav_summary else None

# Huidig tabblad wordt bewaard in session_state zodat de zijbalk weet wat te tonen.
if 'current_tab' not in st.session_state:
    st.session_state['current_tab'] = 'Basis'
current_tab = st.session_state.get('current_tab', 'Basis')

# --- Zijbalk: tab-afhankelijke navigatieknoppen met slotjes ---
with st.sidebar:
    if current_tab == "Basis":
        # Beschikbare analyses: klikbare navigatieknoppen.
        for r in analyse_summary:
            label = r["analysis_type"]["front_end_name"]
            is_selected = r["id"] == st.session_state["selected_analysis_id"]
            if st.button(label, key=f"nav_{r['id']}", use_container_width=True,
                         type="primary" if is_selected else "secondary"):
                st.session_state["selected_analysis_id"] = r["id"]
                st.session_state['current_tab'] = current_tab
                st.rerun()
        # Ontbrekende analyses: vergrendelde knoppen (nog niet gedraaid in de backend).
        for at in analyse_missing:
            _ok, _ontbr = _deps_ok(at, latest)
            _label = f"🔒 {at['front_end_name']}"
            _help = ("Vereist eerst: " + ", ".join(_ontbr)) if not _ok else "Nog niet beschikbaar"
            st.button(_label, key=f"lock_{at['name']}", use_container_width=True,
                      disabled=True, help=_help, type="secondary")

    elif current_tab == "Verdieping":
        for r in verdiep_summary:
            label = r["analysis_type"]["front_end_name"]
            is_selected = r["id"] == st.session_state["selected_verdiep_id"]
            if st.button(label, key=f"vnav_{r['id']}", use_container_width=True,
                         type="primary" if is_selected else "secondary"):
                st.session_state["selected_verdiep_id"] = r["id"]
                st.session_state['current_tab'] = current_tab
                st.rerun()
        for at in verdiep_missing:
            _ok, _ontbr = _deps_ok(at, latest)
            _label = f"🔒 {at['front_end_name']}"
            _help = ("Vereist eerst: " + ", ".join(_ontbr)) if not _ok else "Nog niet beschikbaar"
            st.button(_label, key=f"vlock_{at['name']}", use_container_width=True,
                      disabled=True, help=_help, type="secondary")

    elif current_tab == "Perspectieven":
        for r in perspect_summary:
            label = r["analysis_type"]["front_end_name"]
            is_selected = r["id"] == st.session_state["selected_perspect_id"]
            if st.button(label, key=f"pnav_{r['id']}", use_container_width=True,
                         type="primary" if is_selected else "secondary"):
                st.session_state["selected_perspect_id"] = r["id"]
                st.session_state['current_tab'] = current_tab
                st.rerun()
        for at in perspect_missing:
            _ok, _ontbr = _deps_ok(at, latest)
            _label = f"🔒 {at['front_end_name']}"
            _help = ("Vereist eerst: " + ", ".join(_ontbr)) if not _ok else "Nog niet beschikbaar"
            st.button(_label, key=f"plock_{at['name']}", use_container_width=True,
                      disabled=True, help=_help, type="secondary")

    elif current_tab == "Preekschetsen":
        for r in preek_summary:
            label = r["analysis_type"]["front_end_name"]
            is_selected = r["id"] == st.session_state["selected_preek_id"]
            if st.button(label, key=f"pknav_{r['id']}", use_container_width=True,
                         type="primary" if is_selected else "secondary"):
                st.session_state["selected_preek_id"] = r["id"]
                st.session_state['current_tab'] = current_tab
                st.rerun()
        for at in preek_missing:
            _ok, _ontbr = _deps_ok(at, latest)
            _label = f"🔒 {at['front_end_name']}"
            _help = ("Vereist eerst: " + ", ".join(_ontbr)) if not _ok else "Nog niet beschikbaar"
            st.button(_label, key=f"pklock_{at['name']}", use_container_width=True,
                      disabled=True, help=_help, type="secondary")

    elif current_tab == "Feedback":
        for r in feedback_nav_summary:
            label = r["analysis_type"]["front_end_name"]
            is_selected = r["id"] == st.session_state["selected_feedback_id"]
            if st.button(label, key=f"fbnav_{r['id']}", use_container_width=True,
                         type="primary" if is_selected else "secondary"):
                st.session_state["selected_feedback_id"] = r["id"]
                st.session_state['current_tab'] = current_tab
                st.rerun()
        for at in feedback_nav_missing:
            _ok, _ontbr = _deps_ok(at, latest)
            _label = f"🔒 {at['front_end_name']}"
            _help = ("Vereist eerst: " + ", ".join(_ontbr)) if not _ok else "Nog niet beschikbaar"
            st.button(_label, key=f"fblock_{at['name']}", use_container_width=True,
                      disabled=True, help=_help, type="secondary")


if not analysis_id:
    st.warning("Geen analyse geselecteerd. Ga terug naar het overzicht en selecteer een analyse.")
    st.stop()

# Ensure it's stored in session state for consistency when navigating between internal results
st.session_state['current_analysis_id'] = analysis_id

_data_cache_key = f"overview_data_{analysis_id}"
if st.session_state.pop("analysis_data_dirty", False) or _data_cache_key not in st.session_state:
    st.session_state[_data_cache_key] = {
        "analysis_results": get_data(f"api/analysis-results?sermon_analysis_id={analysis_id}"),
        "sermon_analysis": get_data(f"api/sermon-analyses/{analysis_id}/"),
    }
_cached_data = st.session_state[_data_cache_key]
analysis_results = _cached_data["analysis_results"]
sermon_analysis = _cached_data["sermon_analysis"]

if sermon_analysis:
    st.session_state["extra_context"] = sermon_analysis.get("extra_context", "")
    church = sermon_analysis.get("church", {})
    st.session_state["church_place"] = church.get("place", "") if isinstance(church, dict) else ""
    st.session_state["church_name"] = church.get("name", "") if isinstance(church, dict) else ""

# Houd per analysis_type alleen de nieuwste (hoogste id).
latest: dict[str, dict] = {}
for r in analysis_results:
    name = r['analysis_type']['name']
    if name not in latest or r['id'] > latest[name]['id']:
        latest[name] = r

summary = list(latest.values())

_ALL_NON_BASIS = _PERSPECTIEVEN_NAMEN | _VERDIEPING_NAMEN | _PREEKSCHETSEN_NAMEN | _FEEDBACK_NAMEN

analyse_summary   = sorted(
    [r for r in summary if r["analysis_type"]["name"] not in _ALL_NON_BASIS],
    key=lambda r: _basis_sort_key(r["analysis_type"]["name"]),
)
# Verdieping t/m Feedback: volgorde via het `order`-veld uit de API (vastgelegd in de init-scripts).
# Basis gebruikt een handmatige _BASIS_ORDER omdat de gewenste volgorde daar afwijkt van de API-order.
_order_key = lambda r: r["analysis_type"].get("order", 99)
verdiep_summary   = sorted([r for r in summary if r["analysis_type"]["name"] in _VERDIEPING_NAMEN], key=_order_key)
perspect_summary  = sorted([r for r in summary if r["analysis_type"]["name"] in _PERSPECTIEVEN_NAMEN], key=_order_key)
preek_summary     = sorted([r for r in summary if r["analysis_type"]["name"] in _PREEKSCHETSEN_NAMEN], key=_order_key)
feedback_summary  = sorted([r for r in summary if r["analysis_type"]["name"] in _FEEDBACK_NAMEN], key=_order_key)

if "all_analysis_types_cache" not in st.session_state:
    st.session_state["all_analysis_types_cache"] = get_data("api/analysis-types/")
all_analysis_types = st.session_state["all_analysis_types_cache"]
missing_types = sorted(
    [at for at in all_analysis_types if at.get("front_end_name") and at["name"] not in latest],
    key=lambda x: x.get("order", 99),
)
analyse_missing  = sorted(
    [at for at in missing_types if at["name"] not in _ALL_NON_BASIS],
    key=lambda at: _basis_sort_key(at["name"]),
)
verdiep_missing  = [at for at in missing_types if at["name"] in _VERDIEPING_NAMEN]
perspect_missing = [at for at in missing_types if at["name"] in _PERSPECTIEVEN_NAMEN]
preek_missing    = [at for at in missing_types if at["name"] in _PREEKSCHETSEN_NAMEN]
feedback_missing = [at for at in missing_types if at["name"] in _FEEDBACK_NAMEN]

# feedback_nav_* excludeert volledige_preek — die wordt apart via een dialoog beheerd
feedback_nav_summary = [r for r in feedback_summary if r["analysis_type"]["name"] != "volledige_preek"]
feedback_nav_missing = [at for at in feedback_missing if at["name"] != "volledige_preek"]

# Validate selected IDs for each tab
if "selected_analysis_id" not in st.session_state or \
        st.session_state["selected_analysis_id"] not in {r["id"] for r in analyse_summary}:
    st.session_state["selected_analysis_id"] = analyse_summary[0]["id"] if analyse_summary else None

if "selected_verdiep_id" not in st.session_state or \
        st.session_state["selected_verdiep_id"] not in {r["id"] for r in verdiep_summary}:
    st.session_state["selected_verdiep_id"] = verdiep_summary[0]["id"] if verdiep_summary else None

if "selected_perspect_id" not in st.session_state or \
        st.session_state["selected_perspect_id"] not in {r["id"] for r in perspect_summary}:
    st.session_state["selected_perspect_id"] = perspect_summary[0]["id"] if perspect_summary else None

if "selected_preek_id" not in st.session_state or \
        st.session_state["selected_preek_id"] not in {r["id"] for r in preek_summary}:
    st.session_state["selected_preek_id"] = preek_summary[0]["id"] if preek_summary else None

if "selected_feedback_id" not in st.session_state or \
        st.session_state["selected_feedback_id"] not in {r["id"] for r in feedback_nav_summary}:
    st.session_state["selected_feedback_id"] = feedback_nav_summary[0]["id"] if feedback_nav_summary else None

# --- Sidebar block 2: tab-conditional analysis buttons ---
with st.sidebar:
    if current_tab == "Basis":
        for r in analyse_summary:
            label = r["analysis_type"]["front_end_name"]
            is_selected = r["id"] == st.session_state["selected_analysis_id"]
            btn_type = "primary" if is_selected else "secondary"
            if st.button(label, key=f"nav_{r['id']}", use_container_width=True, type=btn_type):
                st.session_state["selected_analysis_id"] = r["id"]
                st.session_state['current_tab'] = current_tab
                st.rerun()

        if analyse_missing:
            with st.expander("Analyse toevoegen"):
                for at in analyse_missing:
                    _add_lock_key = f"analysis_add_lock_{analysis_id}_{at['name']}"
                    _add_locked = _reanalysis_is_locked(_add_lock_key)
                    _ok, _ontbr = _deps_ok(at, latest)
                    _label = f"🔒 {at['front_end_name']}" if not _ok else at["front_end_name"]
                    _help = ("Vereist eerst: " + ", ".join(_ontbr)) if not _ok else None
                    if st.button(_label, key=f"add_{at['name']}", use_container_width=True,
                                 disabled=_add_locked or not _ok, help=_help):
                        _trigger_analysis(int(analysis_id), at, _add_lock_key)

    elif current_tab == "Verdieping":
        for r in verdiep_summary:
            label = r["analysis_type"]["front_end_name"]
            is_selected = r["id"] == st.session_state["selected_verdiep_id"]
            btn_type = "primary" if is_selected else "secondary"
            if st.button(label, key=f"vnav_{r['id']}", use_container_width=True, type=btn_type):
                st.session_state["selected_verdiep_id"] = r["id"]
                st.session_state['current_tab'] = current_tab
                st.rerun()

        if verdiep_missing:
            with st.expander("Verdieping toevoegen"):
                for at in verdiep_missing:
                    _add_lock_key = f"analysis_add_lock_{analysis_id}_{at['name']}"
                    _add_locked = _reanalysis_is_locked(_add_lock_key)
                    _ok, _ontbr = _deps_ok(at, latest)
                    _label = f"🔒 {at['front_end_name']}" if not _ok else at["front_end_name"]
                    _help = ("Vereist eerst: " + ", ".join(_ontbr)) if not _ok else None
                    if st.button(_label, key=f"vadd_{at['name']}", use_container_width=True,
                                 disabled=_add_locked or not _ok, help=_help):
                        _trigger_analysis(int(analysis_id), at, _add_lock_key)

    elif current_tab == "Perspectieven":
        for r in perspect_summary:
            label = r["analysis_type"]["front_end_name"]
            is_selected = r["id"] == st.session_state["selected_perspect_id"]
            btn_type = "primary" if is_selected else "secondary"
            if st.button(label, key=f"pnav_{r['id']}", use_container_width=True, type=btn_type):
                st.session_state["selected_perspect_id"] = r["id"]
                st.session_state['current_tab'] = current_tab
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
                        _trigger_analysis(int(analysis_id), at, _add_lock_key)

    elif current_tab == "Preekschetsen":
        for r in preek_summary:
            label = r["analysis_type"]["front_end_name"]
            is_selected = r["id"] == st.session_state["selected_preek_id"]
            btn_type = "primary" if is_selected else "secondary"
            if st.button(label, key=f"pknav_{r['id']}", use_container_width=True, type=btn_type):
                st.session_state["selected_preek_id"] = r["id"]
                st.session_state['current_tab'] = current_tab
                st.rerun()

        with st.expander("Preekschets toevoegen"):
            _preek_ready = st.session_state.get(f"preek_selectie_{analysis_id}", {}).get("opgeslagen", False)
            if not preek_missing:
                st.caption("Geen preekschets-types beschikbaar.")
            for at in preek_missing:
                _add_lock_key = f"analysis_add_lock_{analysis_id}_{at['name']}"
                _add_locked = _reanalysis_is_locked(_add_lock_key)
                _ok, _ontbr = _deps_ok(at, latest)
                if not _preek_ready:
                    _label = f"🔒 {at['front_end_name']}"
                    _help = "Stel eerst de selectie in via 'Selectie instellen / wijzigen'."
                elif not _ok:
                    _label = f"🔒 {at['front_end_name']}"
                    _help = "Vereist eerst: " + ", ".join(_ontbr)
                else:
                    _label = at["front_end_name"]
                    _help = None
                if st.button(_label, key=f"pkadd_{at['name']}", use_container_width=True,
                             disabled=_add_locked or not _preek_ready or not _ok, help=_help):
                    _trigger_preekschets(int(analysis_id), at, _add_lock_key)

    elif current_tab == "Feedback":
        # Feedback-analysen navigatie
        for r in feedback_nav_summary:
            label = r["analysis_type"]["front_end_name"]
            is_selected = r["id"] == st.session_state["selected_feedback_id"]
            btn_type = "primary" if is_selected else "secondary"
            if st.button(label, key=f"fbnav_{r['id']}", use_container_width=True, type=btn_type):
                st.session_state["selected_feedback_id"] = r["id"]
                st.session_state['current_tab'] = current_tab
                st.rerun()

        if feedback_nav_missing:
            with st.expander("Feedback toevoegen"):
                for at in feedback_nav_missing:
                    _add_lock_key = f"analysis_add_lock_{analysis_id}_{at['name']}"
                    _add_locked = _reanalysis_is_locked(_add_lock_key)
                    _ok, _ontbr = _deps_ok(at, latest)
                    _label = f"🔒 {at['front_end_name']}" if not _ok else at["front_end_name"]
                    _help = ("Vereist eerst: " + ", ".join(_ontbr)) if not _ok else None
                    if st.button(_label, key=f"fbadd_{at['name']}", use_container_width=True,
                                 disabled=_add_locked or not _ok, help=_help):
                        _trigger_analysis(int(analysis_id), at, _add_lock_key)

if not analysis_results:
    st.info("Bijbelteksten wordt geanalyseerd. Ververs de pagina over enkele minuten.")
    st.stop()

# --- Dialogs ---


@st.dialog("Selectie van input voor preekschetsen", width="large")
def preekschets_selectie_dialog(analysis_id: int, latest: dict, perspect_summary: list) -> None:
    """Popup voor het instellen en opslaan van de preekschets-input selectie."""

    # -- Focus-en-functie (geen voorselectie) --
    focus = latest.get("focus_en_functie", {})
    focus_result = focus.get("result", {}) if focus else {}
    opties = focus_result.get("opties", []) if isinstance(focus_result, dict) else []

    st.subheader("Focus-en-functie")
    focus_optie_value = None
    if opties:
        optie_labels = [f"Optie {o.get('nummer', i + 1)}: {o.get('korte_titel', '')}" for i, o in enumerate(opties)]
        keuze = st.radio(
            "Focus-en-functie optie",
            options=optie_labels,
            index=None,
            label_visibility="collapsed",
            key=f"dlg_focus_radio_{analysis_id}",
        )
        if keuze:
            idx = optie_labels.index(keuze)
            focus_optie_value = opties[idx].get("nummer")
    else:
        st.caption("*Focus-en-functie nog niet beschikbaar*")

    st.divider()

    # -- Kerntekst(en) --
    bijbel = latest.get("bijbelteksten", {})
    bijbel_result = bijbel.get("result", {}) if bijbel else {}
    verzen = []
    if isinstance(bijbel_result, dict):
        for scripture_ref, scripture_data in bijbel_result.items():
            book_chapter = scripture_ref.rstrip(".").strip()
            for verse in (scripture_data.get("verses", []) if isinstance(scripture_data, dict) else []):
                number = verse.get("number", "")
                text = verse.get("modern_text", "").strip()
                verzen.append({"ref": f"{book_chapter}:{number}", "text": text})

    st.subheader("Kerntekst(en)")
    selected_refs = []
    if verzen:
        for v in verzen:
            ref = v["ref"]
            preview = v["text"][:110] + ("…" if len(v["text"]) > 110 else "")
            label = f"**{ref}** — {preview}"
            if st.checkbox(label, key=f"dlg_kt_{analysis_id}_{ref}"):
                selected_refs.append(ref)
    else:
        st.caption("*Bijbelteksten nog niet beschikbaar*")

    st.divider()

    # -- Perspectieven --
    selected_perspectieven: dict[str, list] = {}
    if perspect_summary:
        st.subheader("Perspectieven")
        for perspect in perspect_summary:
            name = perspect["analysis_type"]["name"]
            front_end_name = perspect["analysis_type"]["front_end_name"]
            result = perspect.get("result", {})
            if isinstance(result, str):
                cleaned = result.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[-1]
                    if cleaned.endswith("```"):
                        cleaned = cleaned[: cleaned.rfind("```")]
                try:
                    result = json.loads(cleaned)
                except (json.JSONDecodeError, ValueError):
                    result = {}
            analyses = result.get("analyses", []) if isinstance(result, dict) else []
            if analyses:
                with st.expander(front_end_name, expanded=False):
                    selected_onderdelen = []
                    for item in analyses:
                        nummer = item.get("nummer", "")
                        titel = item.get("titel", "")
                        label = f"{nummer}. {titel}" if nummer else titel
                        if st.checkbox(label, key=f"dlg_perspect_{analysis_id}_{name}_{nummer}"):
                            selected_onderdelen.append(nummer)
                    selected_perspectieven[name] = selected_onderdelen
        st.divider()

    # -- Illustraties --
    selected_illustraties: list[int] = []
    illustraties_data = latest.get("illustraties", {})
    illustraties_result = illustraties_data.get("result", {}) if illustraties_data else {}
    illustraties_lijst = illustraties_result.get("illustraties", []) if isinstance(illustraties_result, dict) else []
    if illustraties_lijst:
        st.subheader("Illustraties")
        for ill in illustraties_lijst:
            nummer = ill.get("nummer", 0)
            titel = ill.get("titel", "")
            ill_type = ill.get("metadata", {}).get("type", "")
            label = f"#{nummer} — {titel}" + (f"  ({ill_type})" if ill_type else "")
            if st.checkbox(label, key=f"dlg_ill_{analysis_id}_{nummer}"):
                selected_illustraties.append(nummer)
        st.divider()

    # -- Representatieve hoorders --
    selected_hoorders: list[str] = []
    hoorders_data = latest.get("representatieve_hoorders", {})
    hoorders_result = hoorders_data.get("result", {}) if hoorders_data else {}
    personas = hoorders_result.get("personas", []) if isinstance(hoorders_result, dict) else []
    if personas:
        st.subheader("Representatieve hoorders")
        for persona in personas:
            naam_obj = persona.get("naam", {})
            voornaam = naam_obj.get("voornaam", "")
            achternaam = naam_obj.get("achternaam", "")
            volledige_naam = f"{voornaam} {achternaam}".strip()
            leeftijd = persona.get("leeftijd", "")
            label = f"👤 {volledige_naam}" + (f" ({leeftijd})" if leeftijd else "")
            if st.checkbox(label, key=f"dlg_hoorder_{analysis_id}_{volledige_naam}"):
                selected_hoorders.append(volledige_naam)
        st.divider()

    # -- Opslaan --
    _kan_opslaan = bool(selected_refs) and focus_optie_value is not None
    if not selected_refs:
        st.warning("Selecteer minimaal één kerntekst.")
    if focus_optie_value is None:
        st.warning("Selecteer een focus-en-functie optie.")
    if st.button("Opslaan", type="primary", use_container_width=True, disabled=not _kan_opslaan):
        st.session_state[f"preek_selectie_{analysis_id}"] = {
            "kernteksten": selected_refs,
            "focus_optie": focus_optie_value,
            "perspectieven": selected_perspectieven,
            "illustraties": selected_illustraties,
            "hoorders": selected_hoorders,
            "opgeslagen": True,
        }
        st.rerun()


# --- Tabbladnavigatie ---
st.segmented_control(
    "Tabblad",
    _TABS,
    key="current_tab",
    label_visibility="collapsed",
)
# Herlaad na de widget-render zodat de widget-waarde van deze render gebruikt wordt.
current_tab = st.session_state.get('current_tab', 'Basis')

if not analysis_results:
    st.info("Bijbelteksten wordt geanalyseerd. Ververs de pagina over enkele minuten.")
    st.stop()

# --- Hoofdinhoud per tabblad ---
if current_tab == "Basis":
    selected_analysis = next(
        (r for r in analyse_summary if r["id"] == st.session_state["selected_analysis_id"]), None
    )
    if not selected_analysis:
        st.stop()

    _, btn_col = st.columns([7, 3])
    with btn_col:
        if st.button("Extra context", icon="✏️", use_container_width=True):
            extra_context_dialog()

    if st.session_state.get("extra_context"):
        st.info(f"**Extra context:** {st.session_state['extra_context']}")

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

elif current_tab == "Verdieping":
    selected_verdiep = next(
        (r for r in verdiep_summary if r["id"] == st.session_state["selected_verdiep_id"]), None
    )
    if not verdiep_summary:
        st.info("Nog geen verdieping beschikbaar.")
    # Render-functies voor verdieping worden in een volgende versie toegevoegd.

elif current_tab == "Perspectieven":
    selected_perspect = next(
        (r for r in perspect_summary if r["id"] == st.session_state["selected_perspect_id"]), None
    )
    if not perspect_summary:
        st.info("Nog geen perspectieven beschikbaar.")
    # Render-functies voor perspectieven worden in een volgende versie toegevoegd.

elif current_tab == "Preekschetsen":
    selected_preek = next(
        (r for r in preek_summary if r["id"] == st.session_state["selected_preek_id"]), None
    )
    if not preek_summary:
        st.info("Nog geen preekschetsen beschikbaar.")
    # Render-functies voor preekschetsen worden in een volgende versie toegevoegd.

elif current_tab == "Feedback":
    selected_feedback = next(
        (r for r in feedback_nav_summary if r["id"] == st.session_state["selected_feedback_id"]), None
    )
    # Sectie voor de eigen preektekst (volledige_preek).
    # Dit type wordt apart beheerd: niet in de navigatie, maar inline bovenaan het tabblad.
    volledige_preek_data = latest.get("volledige_preek")
    if volledige_preek_data:
        # Toon de inline bewerker voor de preektekst.
        with st.expander("Eigen preektekst", expanded=not bool(selected_feedback)):
            volledige_preek(volledige_preek_data, int(analysis_id))
    else:
        # Zoek het analysis-type op om het aan te kunnen maken via de agent.
        vp_type = next((at for at in feedback_missing if at["name"] == "volledige_preek"), None)
        if vp_type:
            _, btn_col = st.columns([7, 3])
            with btn_col:
                _vp_lock_key = f"analysis_add_lock_{analysis_id}_volledige_preek"
                if st.button("Eigen preek invoeren", icon="✏️", use_container_width=True,
                             disabled=_reanalysis_is_locked(_vp_lock_key)):
                    _trigger_analysis(int(analysis_id), vp_type, _vp_lock_key)
    if not feedback_nav_summary:
        st.info("Nog geen feedback-analyses beschikbaar.")
    elif selected_feedback:
        feedback_analyse(selected_feedback)
