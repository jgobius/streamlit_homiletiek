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
from src.components.user_feedback import render_feedback_trigger

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
    "preek_jungel",
    "preek_fleming_rutledge",
    "preek_brueggemann_poet",
    "preek_literair",
    "preek_noordmans",
    "preek_kosuke_koyama",
    "preek_zornberg",
    "preek_brueggemann",
    "preek_drewermann",
    "preek_gardner_taylor",
    "preek_solle",
    "preek_peterson",
    "preek_standup",
}

_FEEDBACK_NAMEN = {
    "volledige_preek",
    "feedback_adversarial", "feedback_dekker", "feedback_aristoteles",
    "feedback_kolb", "feedback_schulz_von_thun", "feedback_transactional",
    "feedback_esthetiek", "feedback_metafoor", "feedback_narratief",
    "feedback_taalhandeling",
}

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

analysis_id = st.query_params.get('analysis_id') or st.session_state.get('current_analysis_id')

# Initialize tab state before sidebar renders
if 'current_tab' not in st.session_state:
    st.session_state['current_tab'] = 'Basis'
current_tab = st.session_state.get('current_tab', 'Basis')

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

all_analysis_types = get_data("api/analysis-types/")
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
                st.session_state.pop("selected_verdiep_id", None)
                st.session_state.pop("selected_perspect_id", None)
                st.session_state.pop("selected_preek_id", None)
                st.session_state.pop("selected_feedback_id", None)
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


@st.dialog("Eigen preek invoeren", width="large")
def volledige_preek_dialog(analysis_id: int, latest: dict, all_analysis_types: list) -> None:
    """Popup voor het invoeren of bewerken van de volledige preektekst."""
    existing = latest.get("volledige_preek")
    existing_result = existing.get("result", {}) if existing else {}
    if not isinstance(existing_result, dict):
        existing_result = {}

    titel = existing_result.get("titel", "")
    ondertitel = existing_result.get("ondertitel", "")
    preektekst = existing_result.get("preektekst", "")

    st.caption("Voer de preektekst in (kopieer/plak uit tekstverwerker of schrijf direct).")

    new_titel = st.text_input("Titel", value=titel,
                              placeholder="bijv. Het brood dat leven geeft")
    new_ondertitel = st.text_input("Ondertitel", value=ondertitel,
                                   placeholder="bijv. Johannes 6:35 — preek gehouden op 30 maart 2025")
    new_preektekst = st.text_area("Preektekst", value=preektekst, height=500,
                                  placeholder="Plak hier de volledige uitgeschreven preektekst...")

    _kan_opslaan = bool(new_preektekst.strip())
    if st.button("Opslaan", type="primary", use_container_width=True, disabled=not _kan_opslaan):
        updated = {
            **existing_result,
            "titel": new_titel,
            "ondertitel": new_ondertitel,
            "preektekst": new_preektekst,
        }
        try:
            handler = st.session_state["api_handler"]
            if existing:
                handler.patch(
                    f"api/analysis-results/{existing['id']}/?sermon_analysis_id={analysis_id}",
                    data={"result": updated},
                )
            else:
                vp_at = next((x for x in all_analysis_types if x["name"] == "volledige_preek"), None)
                if not vp_at:
                    st.error("Analyse-type 'volledige_preek' niet gevonden. Voer init_feedback.py uit.")
                    return
                handler.post(
                    "api/analysis-results/",
                    data={
                        "analysis_type": vp_at["id"],
                        "sermon_analysis": analysis_id,
                        "result": updated,
                    },
                )
            st.toast("Preektekst opgeslagen.")
            st.rerun()
        except Exception as e:
            st.error(f"Fout bij opslaan: {e}")


# --- Main content ---

st.segmented_control(
    "Tabblad",
    _TABS,
    key="current_tab",
    label_visibility="collapsed",
)
# Re-read after widget render (widget may have updated the value this run)
current_tab = st.session_state.get('current_tab', 'Basis')

if current_tab == "Basis":
    selected_analysis = next(
        (r for r in analyse_summary if r["id"] == st.session_state["selected_analysis_id"]), None
    )

    if not selected_analysis:
        st.stop()

    st.header(selected_analysis["analysis_type"]["front_end_name"])

    col_del, col_rerun, col_ctx, col_info = st.columns([3, 3, 3, 1])
    with col_del:
        if st.button("Verwijder", icon="🗑️"):
            confirm_delete_result(selected_analysis)
    with col_rerun:
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
        _desc = selected_analysis["analysis_type"].get("description")
        if _desc:
            with st.popover("ℹ️", use_container_width=False):
                st.markdown(_desc)

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

    render_feedback_trigger(
        analysis_result_id=selected_analysis["id"],
        section_name=selected_analysis["analysis_type"]["front_end_name"],
        handler=st.session_state["api_handler"],
        key=f"feedback_basis_{selected_analysis['id']}",
    )

elif current_tab == "Verdieping":
    selected_verdiep = next(
        (r for r in verdiep_summary if r["id"] == st.session_state["selected_verdiep_id"]), None
    )

    if not verdiep_summary:
        st.info("Nog geen verdieping beschikbaar. Voeg ze toe via 'Verdieping toevoegen' in de zijbalk.")
    else:
        if selected_verdiep:
            st.header(selected_verdiep["analysis_type"]["front_end_name"])
        col_del, col_rerun, col_ctx, col_info = st.columns([3, 3, 3, 1])
        with col_del:
            if selected_verdiep and st.button("Verwijder", icon="🗑️", key="v_del"):
                confirm_delete_result(selected_verdiep)
        with col_rerun:
            if st.button("Opnieuw", icon="🔄", key="v_rerun"):
                confirm_rerun_analysis(
                    sermon_analysis_id=int(analysis_id),
                    analysis_type_name=selected_verdiep["analysis_type"]["name"] if selected_verdiep else "",
                    front_end_name=selected_verdiep["analysis_type"]["front_end_name"] if selected_verdiep else "",
                )
        with col_ctx:
            if st.button("Aanpassen", icon="✏️", key="v_ctx"):
                aanpassen_dialog(selected_verdiep)
        with col_info:
            _desc = selected_verdiep["analysis_type"].get("description") if selected_verdiep else None
            if _desc:
                with st.popover("ℹ️", use_container_width=False):
                    st.markdown(_desc)

        if selected_verdiep:
            verdieping(selected_verdiep, analysis_type_name=selected_verdiep["analysis_type"]["name"])
            render_feedback_trigger(
                analysis_result_id=selected_verdiep["id"],
                section_name=selected_verdiep["analysis_type"]["front_end_name"],
                handler=st.session_state["api_handler"],
                key=f"feedback_verdiep_{selected_verdiep['id']}",
            )

elif current_tab == "Perspectieven":
    selected_perspect = next(
        (r for r in perspect_summary if r["id"] == st.session_state["selected_perspect_id"]), None
    )

    if not perspect_summary:
        st.info("Nog geen perspectieven beschikbaar. Voeg ze toe via 'Perspectief toevoegen' in de zijbalk.")
    else:
        if selected_perspect:
            st.header(selected_perspect["analysis_type"]["front_end_name"])
        col_del, col_rerun, col_ctx, col_info = st.columns([3, 3, 3, 1])
        with col_del:
            if selected_perspect and st.button("Verwijder", icon="🗑️", key="p_del"):
                confirm_delete_result(selected_perspect)
        with col_rerun:
            if st.button("Opnieuw", icon="🔄", key="p_rerun"):
                confirm_rerun_analysis(
                    sermon_analysis_id=int(analysis_id),
                    analysis_type_name=selected_perspect["analysis_type"]["name"] if selected_perspect else "",
                    front_end_name=selected_perspect["analysis_type"]["front_end_name"] if selected_perspect else "",
                )
        with col_ctx:
            if st.button("Aanpassen", icon="✏️", key="p_ctx"):
                aanpassen_dialog(selected_perspect)
        with col_info:
            _desc = selected_perspect["analysis_type"].get("description") if selected_perspect else None
            if _desc:
                with st.popover("ℹ️", use_container_width=False):
                    st.markdown(_desc)

        if selected_perspect:
            contextduiding(selected_perspect)
            render_feedback_trigger(
                analysis_result_id=selected_perspect["id"],
                section_name=selected_perspect["analysis_type"]["front_end_name"],
                handler=st.session_state["api_handler"],
                key=f"feedback_perspect_{selected_perspect['id']}",
            )

elif current_tab == "Preekschetsen":
    _selectie = st.session_state.get(f"preek_selectie_{analysis_id}", {})
    if st.button("Selectie instellen / wijzigen", icon="✏️"):
        preekschets_selectie_dialog(int(analysis_id), latest, perspect_summary)
    if _selectie.get("opgeslagen"):
        _kt = _selectie.get("kernteksten", [])
        _fo = _selectie.get("focus_optie")
        _n_persp = sum(len(v) for v in _selectie.get("perspectieven", {}).values())
        _n_ill = len(_selectie.get("illustraties", []))
        _n_hoord = len(_selectie.get("hoorders", []))
        st.caption(
            f"Opgeslagen: {len(_kt)} kerntekst(en) · focus optie {_fo} · "
            f"{_n_persp} perspectief-onderdelen · {_n_ill} illustraties · {_n_hoord} hoorders"
        )

    selected_preek = next(
        (r for r in preek_summary if r["id"] == st.session_state["selected_preek_id"]), None
    )

    if not preek_summary:
        st.info("Nog geen preekschetsen beschikbaar. Stel eerst de selectie in via de knop hierboven, voeg dan een preekschets toe via de zijbalk.")
    else:
        if selected_preek:
            st.header(selected_preek["analysis_type"]["front_end_name"])
        col_del, col_rerun, col_ctx, col_info = st.columns([3, 3, 3, 1])
        with col_del:
            if selected_preek and st.button("Verwijder", icon="🗑️", key="pk_del"):
                confirm_delete_result(selected_preek)
        with col_rerun:
            if st.button("Opnieuw", icon="🔄", key="pk_rerun"):
                confirm_rerun_analysis(
                    sermon_analysis_id=int(analysis_id),
                    analysis_type_name=selected_preek["analysis_type"]["name"] if selected_preek else "",
                    front_end_name=selected_preek["analysis_type"]["front_end_name"] if selected_preek else "",
                )
        with col_ctx:
            if st.button("Aanpassen", icon="✏️", key="pk_ctx"):
                aanpassen_dialog(selected_preek)
        with col_info:
            _desc = selected_preek["analysis_type"].get("description") if selected_preek else None
            if _desc:
                with st.popover("ℹ️", use_container_width=False):
                    st.markdown(_desc)

        if selected_preek:
            _render_preekschets_result(selected_preek, latest)
            render_feedback_trigger(
                analysis_result_id=selected_preek["id"],
                section_name=selected_preek["analysis_type"]["front_end_name"],
                handler=st.session_state["api_handler"],
                key=f"feedback_preek_{selected_preek['id']}",
            )

elif current_tab == "Feedback":
    if st.button("Eigen preek invoeren", icon="✏️"):
        volledige_preek_dialog(int(analysis_id), latest, all_analysis_types)
    _vp = latest.get("volledige_preek")
    if _vp:
        _vp_titel = _vp.get("result", {}).get("titel", "") if isinstance(_vp.get("result"), dict) else ""
        if _vp_titel:
            st.caption(f"Opgeslagen: {_vp_titel[:50]}")

    selected_feedback = next(
        (r for r in feedback_nav_summary if r["id"] == st.session_state["selected_feedback_id"]), None
    )

    if not feedback_nav_summary:
        if not latest.get("volledige_preek"):
            st.info("Voer eerst een preektekst in of genereer deze via de knop hierboven.")
        else:
            st.info("Voeg feedbackanalyses toe via 'Feedback toevoegen' in de zijbalk.")
    else:
        if selected_feedback:
            st.header(selected_feedback["analysis_type"]["front_end_name"])
        col_del, col_rerun, col_ctx, col_info = st.columns([3, 3, 3, 1])
        with col_del:
            if selected_feedback and st.button("Verwijder", icon="🗑️", key="fb_del"):
                confirm_delete_result(selected_feedback)
        with col_rerun:
            if st.button("Opnieuw", icon="🔄", key="fb_rerun"):
                confirm_rerun_analysis(
                    sermon_analysis_id=int(analysis_id),
                    analysis_type_name=selected_feedback["analysis_type"]["name"] if selected_feedback else "",
                    front_end_name=selected_feedback["analysis_type"]["front_end_name"] if selected_feedback else "",
                )
        with col_ctx:
            if st.button("Aanpassen", icon="✏️", key="fb_ctx"):
                aanpassen_dialog(selected_feedback)
        with col_info:
            _desc = selected_feedback["analysis_type"].get("description") if selected_feedback else None
            if _desc:
                with st.popover("ℹ️", use_container_width=False):
                    st.markdown(_desc)

        if selected_feedback:
            feedback_analyse(selected_feedback)
            render_feedback_trigger(
                analysis_result_id=selected_feedback["id"],
                section_name=selected_feedback["analysis_type"]["front_end_name"],
                handler=st.session_state["api_handler"],
                key=f"feedback_fb_{selected_feedback['id']}",
            )
