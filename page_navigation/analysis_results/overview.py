import streamlit as st

from src.utils.utils import redirect_to_login, get_data
from page_navigation.analysis_results.analyses.postille import postille
from page_navigation.analysis_results.analyses.bijbelteksten import bijbelteksten
from page_navigation.analysis_results.analyses.liturgisch_jaar import liturgisch_jaar
from page_navigation.analysis_results.analyses.liedsuggesties import liedsuggesties
from page_navigation.analysis_results.analyses.structuralistische_exegese import structuralistische_exegese
from page_navigation.analysis_results.analyses.commentaren import commentaren
from page_navigation.analysis_results.analyses.theologie import theologie

# --- Categorisatie van analyse-types per tabblad ---

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


@st.dialog("Extra context")
def extra_context_dialog() -> None:
    st.text_area("Geef extra context voor deze analyse", key="extra_context_input", height=200)
    if st.button("Opslaan", type="primary"):
        st.session_state["extra_context"] = st.session_state["extra_context_input"]
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
    if not feedback_nav_summary:
        st.info("Nog geen feedback-analyses beschikbaar.")
    # Render-functies voor feedback worden in een volgende versie toegevoegd.
