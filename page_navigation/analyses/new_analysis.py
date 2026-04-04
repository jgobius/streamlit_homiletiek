import json
import time
from datetime import date, datetime, timedelta
from typing import Any

import requests
import streamlit as st

from src.models.sermon_analysis_model import SermonAnalysisModel
from src.utils.utils import (
    get_data,
    get_cached_data,
    get_structured_scriptures,
    redirect_to_login,
    BIBLE_BOOKS,
    READING_TYPES,
    redirect_to_login,
    get_structured_scriptures,
    render_sidebar,
    save_scriptures,
    load_scriptures,
)

redirect_to_login()

# Na het starten van een analyse wordt een lock ingesteld om dubbele inzendingen te voorkomen.
_ANALYSIS_LOCK_TIMEOUT_SECONDS = 120


########### HULPFUNCTIES ###########


def _sanitize_cv(key: str) -> None:
    """Verwijder ongeldige tekens uit het hoofdstuk/verzen-veld (alleen cijfers, :, - en a/b)."""
    raw = st.session_state.get(key, "")
    cleaned = "".join(c for c in raw if c.isdigit() or c in ":-ab")
    if cleaned != raw:
        st.session_state[key] = cleaned


@st.dialog("Eigen lezingen toevoegen", width="large")
def _show_own_readings_dialog() -> None:
    """Pop-up om eigen lezingen te configureren (bijbelboek + hoofdstuk/verzen per lezing)."""
    st.write("Configureer hier de eigen lezingen voor de dienst (minimaal één).")

    if "own_readings" not in st.session_state:
        st.session_state["own_readings"] = {rt: {"book": "", "chapter_verses": ""} for rt in READING_TYPES}

    if "own_readings_count" not in st.session_state:
        st.session_state["own_readings_count"] = 1

    count = st.session_state["own_readings_count"]
    active_types = READING_TYPES[:count]

    for rt in active_types:
        st.markdown(f"**{rt}**")
        col1, col2 = st.columns([1, 1])

        current_data = st.session_state["own_readings"].get(rt, {"book": "", "chapter_verses": ""})

        with col1:
            book_options = [""] + BIBLE_BOOKS
            book_index = book_options.index(current_data["book"]) if current_data["book"] in book_options else 0
            st.selectbox(
                f"Bijbelboek ({rt})",
                options=book_options,
                index=book_index,
                key=f"book_select_{rt}",
                label_visibility="collapsed",
            )
        with col2:
            book_selected = bool(st.session_state.get(f"book_select_{rt}", ""))
            cv_key = f"cv_input_{rt}"
            if cv_key not in st.session_state:
                st.session_state[cv_key] = current_data["chapter_verses"]
            # Leegmaken als er geen boek geselecteerd is
            if not book_selected:
                st.session_state[cv_key] = ""
            st.text_input(
                f"Hoofdstuk/verzen ({rt})",
                key=cv_key,
                placeholder="Bijv. 1:1-10",
                label_visibility="collapsed",
                disabled=not book_selected,
                on_change=_sanitize_cv,
                args=(cv_key,),
            )

    btn_col1, btn_col2 = st.columns([1, 1])
    with btn_col1:
        if count < len(READING_TYPES):
            if st.button("+ Lezing toevoegen"):
                st.session_state["own_readings_count"] = count + 1
                st.rerun()
    with btn_col2:
        if count > 1:
            if st.button("- Lezing verwijderen"):
                last_rt = READING_TYPES[count - 1]
                st.session_state["own_readings"][last_rt] = {"book": "", "chapter_verses": ""}
                st.session_state.pop(f"book_select_{last_rt}", None)
                st.session_state.pop(f"cv_input_{last_rt}", None)
                st.session_state["own_readings_count"] = count - 1
                st.rerun()

    st.markdown("---")
    if st.button("Opslaan en sluiten", type="primary"):
        selected = []
        new_own_readings = {}
        incomplete = []
        for rt in READING_TYPES:
            if rt in active_types:
                book = st.session_state[f"book_select_{rt}"]
                cv = st.session_state[f"cv_input_{rt}"]
                new_own_readings[rt] = {"book": book, "chapter_verses": cv}
                if book and cv:
                    selected.append(f"{book} {cv}")
                elif book and not cv:
                    incomplete.append(rt)
            else:
                new_own_readings[rt] = {"book": "", "chapter_verses": ""}

        if incomplete:
            st.error(f"Vul ook de hoofdstuk/verzen in voor: {', '.join(incomplete)}.")
        elif not selected:
            st.error("Selecteer minimaal één lezing (Boek én Hoofdstuk/verzen).")
        else:
            # Gestructureerde lezingen wissen als de selectie gewijzigd is
            if st.session_state.get("selected_scriptures") != selected:
                st.session_state["structured_scriptures"] = []
                st.session_state["scriptures_approved"] = False

            st.session_state["own_readings"] = new_own_readings
            st.session_state["selected_scriptures"] = selected
            st.rerun()


def _get_scripture_text(scripture_dict: dict[str, Any] | None) -> str:
    """Zet een scripture-dict om naar een leesbare tekst met versnummers."""
    if scripture_dict is None:
        return ""
    reading = ""
    for item in scripture_dict.get("verses", []):
        reading += f"{item.get('verse')}. {item.get('text')} \n"
    return reading


@st.dialog("Details roosterlezing", width="large")
def _show_scripture_details(scripture: dict[str, Any]) -> None:
    """Pop-up met de volledige tekst van de roosterlezingen voor de geselecteerde datum."""
    scripture_data = scripture.get("scriptures") or {}
    st.markdown(f'**Eerste lezing:\t{scripture.get("first_scripture")}**')
    st.markdown(_get_scripture_text(scripture_data.get("first_scripture")))
    st.markdown(f'**Tweede lezing:**\t{scripture.get("second_scripture")}')
    st.markdown(_get_scripture_text(scripture_data.get("second_scripture")))
    st.markdown(f'**Psalm:**\t{scripture.get("psalm")}')
    st.markdown(_get_scripture_text(scripture_data.get("psalm")))
    st.markdown(f'**Evangelie:**\t{scripture.get("gospel")}')
    st.markdown(_get_scripture_text(scripture_data.get("gospel")))


def _clean_up_session_state() -> None:
    """Verwijder alle analyse-gerelateerde session state na het indienen van het formulier."""
    for key in [
        "selected_scriptures", "structured_scriptures", "scriptures_approved",
        "selected_scripture_id", "own_readings", "own_readings_count",
    ]:
        st.session_state.pop(key, None)


def _analysis_is_locked() -> bool:
    """Geeft True als er al een analyse loopt en de lock nog niet verlopen is."""
    lock_time = st.session_state.get("analysis_lock_time")
    if lock_time is None:
        return False
    if time.time() - lock_time > _ANALYSIS_LOCK_TIMEOUT_SECONDS:
        st.session_state.pop("analysis_lock_time", None)
        return False
    return True


def _release_analysis_lock() -> None:
    st.session_state.pop("analysis_lock_time", None)


########### DATA OPHALEN ###########

churches = get_data("api/churches/")
song_books = get_cached_data("api/song-books/")
bible_versions = get_cached_data("api/bible-versions/")
liturgy = get_cached_data("api/liturgy/")
render_sidebar()

########### DEFINE FUNCTIONS ###########


def get_scripture_text(
    scripture_dict: dict[str, Any],
) -> str:
    reading = ""
    for item in scripture_dict.get("verses", []):
        verse_number = item.get("verse")
        verse_text = item.get("text")
        reading += f"{verse_number}. {verse_text} \n"

    return reading


@st.dialog("Details roosterlezing", width="large")
def show_scripture_details(scripture: dict[str, Any]) -> None:

    scripture_data = scripture.get("scriptures", {})

    st.markdown(f'**Eerste lezing:\t{scripture.get("first_scripture")}**')
    st.markdown(f'{get_scripture_text(scripture_data["first_scripture"])}')
    st.markdown(f'**Tweede lezing:**\t{scripture.get("second_scripture")}')
    st.markdown(get_scripture_text(scripture_data["second_scripture"]))
    st.markdown(f'**Psalm:**\t{scripture.get("psalm")}')
    st.markdown(get_scripture_text(scripture_data["psalm"]))
    st.markdown(f'**Evangelie:**\t{scripture.get("gospel")}')
    st.markdown(get_scripture_text(scripture_data["gospel"]))


def update(options: list[str]) -> None:
    st.session_state["selected_scriptures"] = options


def clean_up_session_state() -> None:
    keys_to_remove = [
        "selected_scriptures",
        "structured_scriptures",
        "scriptures_approved",
        "selected_scripture_id",
    ]
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]


########### GET DATA ###########

churches = get_data("api/churches/")
song_books = get_cached_data("api/song-books/")
bible_versions = get_cached_data("api/bible-versions/")
liturgy = get_cached_data("api/liturgy/")
st.header("Nieuwe analyse")

# Session state initialiseren voor lezingen
if "selected_scriptures" not in st.session_state:
    st.session_state["selected_scriptures"] = []

if "structured_scriptures" not in st.session_state:
    st.session_state["structured_scriptures"] = []

if "own_readings" not in st.session_state:
    st.session_state["own_readings"] = {rt: {"book": "", "chapter_verses": ""} for rt in READING_TYPES}

if "own_readings_count" not in st.session_state:
    st.session_state["own_readings_count"] = 1

########### FORMULIER ###########

col1, col2 = st.columns([11, 1], vertical_alignment='bottom')

with col1:
    selected_church = st.selectbox(
        "Selecteer de gemeente voor deze kerkdienst",
        options=churches,
        format_func=lambda church: church["name"],
    )

with col2:
    # Knop om snel een nieuwe gemeente aan te maken en terug te keren
    if st.button(":material/Add:"):
        st.switch_page(
            f"{st.session_state['page_navigation_dir']}/churches/new_church.py",
            query_params={"from_page": "new_analysis.py"},
        )

extra_context = st.text_area("Extra context (optioneel):", height=150, max_chars=1024)

# Datum standaard op de eerstvolgende zondag instellen
_today = date.today()
_next_sunday = _today + timedelta(days=(6 - _today.weekday()) % 7)
sermon_date = st.date_input(
    "Datum van de kerkdienst", value=_next_sunday, format="DD-MM-YYYY", min_value="today"
)

# Liedboeken met "liedboek" in de naam vooraf selecteren als standaard
_default_song_books = [b for b in song_books if "liedboek" in b.get("name", "").lower()]
song_books = st.multiselect(
    "Selecteer de liedboeken die in deze kerkdienst gebruikt worden (minimaal één verplicht):",
    placeholder="Geen liedboeken geselecteerd",
    options=song_books,
    default=_default_song_books,
    format_func=lambda book: book["name"],
)

# Bijbelvertaling: NBV21 als standaard indien beschikbaar
_nbv21_index = next(
    (i for i, v in enumerate(bible_versions) if "NBV21" in v.get("version", "")), 0
)
bible_version = st.selectbox(
    "Selecteer de bijbelvertaling die in deze kerkdienst gebruikt wordt (optioneel):",
    placeholder="Geen bijbelvertaling geselecteerd",
    options=bible_versions,
    index=_nbv21_index,
    format_func=lambda version: version["version"],
)

scriptures_choice = st.radio(
    "Schriftlezingen", options=["Kerkelijk rooster volgen", "Eigen lezingen"]
)

# ── Kerkelijk rooster ──────────────────────────────────────────────────────────
if scriptures_choice == "Kerkelijk rooster volgen":
    selected_liturgy = [
        l for l in liturgy if l.get("date") == sermon_date.strftime("%Y-%m-%d")
    ]

    if not selected_liturgy:
        st.warning(
            "Er zijn geen roosterlezingen gevonden voor de geselecteerde datum. "
            "Kies een andere datum of selecteer 'Eigen lezingen' om handmatig lezingen toe te voegen."
        )
        st.session_state.pop("liturgy_viewed_date", None)
    else:
        st.session_state["selected_scripture_id"] = selected_liturgy[0].get("id")
        if st.button("Roosterlezingen tonen"):
            st.session_state["liturgy_viewed_date"] = sermon_date.isoformat()
            _show_scripture_details(selected_liturgy[0])
        if st.session_state.get("liturgy_viewed_date") == sermon_date.isoformat():
            st.session_state["scriptures_approved"] = st.checkbox(
                "Ik bevestig dat de roosterlezingen voor de geselecteerde datum correct zijn en klaar voor analyse",
                value=False,
            )

# ── Eigen lezingen ─────────────────────────────────────────────────────────────
if scriptures_choice == "Eigen lezingen":
    st.markdown("### Eigen lezingen")
    any_lezing = False
    for rt in READING_TYPES:
        data = st.session_state["own_readings"].get(rt, {})
        if data.get("book") and data.get("chapter_verses"):
            st.write(f"- **{rt}**: {data['book']} {data['chapter_verses']}")
            any_lezing = True

    if not any_lezing:
        st.info("Er zijn nog geen lezingen toegevoegd.")

    # Knop opent het dialoogvenster direct — geen session_state-vlag nodig.
    # Een vlag in session_state blijft actief bij elke rerun, waardoor de popup
    # steeds opnieuw verschijnt als de gebruiker iets op de pagina wijzigt.
    if st.button("Lezingen configureren"):
        _show_own_readings_dialog()

if scriptures_choice == "Eigen lezingen":
    collect_structured_scriptures = st.button("Lezingen ophalen", disabled=not any_lezing)

    if collect_structured_scriptures:
        with st.status(
            "Lezingen structureren (afhankelijk van het aantal lezingen kan dit even duren)..."
        ):
            st.session_state["structured_scriptures"] = get_structured_scriptures(
                scriptures=st.session_state["selected_scriptures"],
                bible_version=bible_version.get("version") if bible_version else None,
                language="nl",
            )

# Gestructureerde lezingen tonen in uitklapbare secties
for scripture in st.session_state["structured_scriptures"]:
    with st.expander(f"**{scripture.get('original_scripture')}**", expanded=False):
        for sc in scripture.get("scriptures", []):
            st.markdown(f"Hoofdstuk **{sc.get('chapter')}**")
            for verse in sc.get("verses", []):
                st.markdown(f"**{verse.get('number')}**")
                st.markdown(f"{verse.get('text')}")
            st.write("---")

if st.session_state.get("structured_scriptures"):
    st.session_state["scriptures_approved"] = st.checkbox(
        "Ik bevestig dat de data zoals hierboven vermeld correct zijn en klaar voor analyse",
        value=False,
    )

# ── Indienen ───────────────────────────────────────────────────────────────────
_readings_available = st.session_state.get("scriptures_approved", False)
_locked = _analysis_is_locked()

if _locked:
    elapsed = int(time.time() - st.session_state["analysis_lock_time"])
    remaining = _ANALYSIS_LOCK_TIMEOUT_SECONDS - elapsed
    st.info(f"Er loopt al een analyse. Nog {remaining} seconden voordat u opnieuw kunt proberen.")

submit = False
if _readings_available:
    submit = st.button("Analyse starten", type="primary", disabled=_locked)

if submit:
    if not selected_church:
        st.error("Selecteer een gemeente. Ga naar 'Gemeenten' om een gemeente aan te maken.")
        st.stop()

    if not song_books:
        st.error("Selecteer minimaal één liedbundel.")
        st.stop()

    if scriptures_choice == "Eigen lezingen":
        if not st.session_state.get("structured_scriptures"):
            st.error("Haal eerst de lezingen op via de knop 'Lezingen ophalen'.")
            st.stop()
        if not st.session_state.get("scriptures_approved"):
            st.error("Bevestig eerst dat de opgehaalde lezingen correct zijn.")
            st.stop()

    st.session_state["analysis_lock_time"] = time.time()
    try:
        # Titel automatisch genereren op basis van gemeente, datum en tijd
        church_name = selected_church["name"]
        date_str = sermon_date.strftime("%d-%m-%Y")
        time_str = datetime.now().strftime("%H:%M")
        title = f"{church_name} {date_str} {time_str}"[:64]

        sermon_analysis_model = SermonAnalysisModel(
            church=selected_church["id"],
            title=title,
            sermon_date=sermon_date,
            liturgy=st.session_state.get("selected_scripture_id"),
            scripture_json=st.session_state.get("structured_scriptures") or [],
            use_calendar=(scriptures_choice == "Kerkelijk rooster volgen"),
            song_books=[book["id"] for book in song_books],
            extra_context=extra_context,
            bible_version=bible_version["id"] if bible_version else None,
        )

        data = json.loads(sermon_analysis_model.model_dump_json())
        result = st.session_state["api_handler"].post(endpoint="api/sermon-analyses/", data=data)
        sermon_analysis_id = result.get("id")

        # Auto-start bijbelteksten-analyse via de agent (mislukken blokkeert de gebruiker niet)
        if sermon_analysis_id:
            agent_url = st.secrets["API_AGENT_URL"].rstrip("/")
            try:
                requests.post(
                    f"{agent_url}/run_single_analysis/",
                    json={"sermon_analysis_id": sermon_analysis_id, "analysis_type_name": "bijbelteksten"},
                    timeout=30,
                )
            except Exception:
                pass

        _clean_up_session_state()
        _release_analysis_lock()
        st.switch_page(f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py")

    except Exception as e:
        _release_analysis_lock()
        st.error(f"Er is een fout opgetreden bij het starten van de analyse: {e}")
        st.stop()
