import json
import time
from datetime import date, timedelta
from typing import Any

import streamlit as st

from src.models.sermon_analysis_model import SermonAnalysisModel
from src.utils.utils import (
    get_data,
    get_cached_data,
    redirect_to_login,
    get_structured_scriptures,
    render_sidebar,
    save_scriptures,
    load_scriptures,
    BIBLE_BOOKS,
    READING_TYPES,
    READING_TYPE_BOOKS,
)

redirect_to_login()

render_sidebar()

ANALYSIS_LOCK_TIMEOUT_SECONDS = 120

########### DEFINE FUNCTIONS ###########


def _sanitize_cv(key: str) -> None:
    """Remove any character that is not a digit, colon, or hyphen."""
    raw = st.session_state.get(key, "")
    cleaned = "".join(c for c in raw if c.isdigit() or c in ":-")
    if cleaned != raw:
        st.session_state[key] = cleaned


@st.dialog("Eigen lezingen toevoegen", width="large")
def show_own_readings_dialog() -> None:
    st.write("Configureer hier de eigen lezingen voor de dienst (minimaal één).")
    
    if "own_readings" not in st.session_state:
        st.session_state["own_readings"] = {rt: {"book": "", "chapter_verses": ""} for rt in READING_TYPES}
        
    for rt in READING_TYPES:
        st.markdown(f"**{rt}**")
        col1, col2 = st.columns([1, 1])
        
        current_data = st.session_state["own_readings"].get(rt, {"book": "", "chapter_verses": ""})
        
        with col1:
            allowed_books = READING_TYPE_BOOKS.get(rt, BIBLE_BOOKS)
            book_options = [""] + allowed_books
            book_index = book_options.index(current_data["book"]) if current_data["book"] in book_options else 0
            st.selectbox(
                f"Bijbelboek ({rt})",
                options=book_options,
                index=book_index,
                key=f"book_select_{rt}",
                label_visibility="collapsed"
            )
        with col2:
            book_selected = bool(st.session_state.get(f"book_select_{rt}", ""))
            cv_key = f"cv_input_{rt}"
            if cv_key not in st.session_state:
                st.session_state[cv_key] = current_data["chapter_verses"]
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

    st.markdown("---")
    if st.button("Opslaan en sluiten", type="primary"):
        selected = []
        new_own_readings = {}
        incomplete = []
        for rt in READING_TYPES:
            book = st.session_state[f"book_select_{rt}"]
            cv = st.session_state[f"cv_input_{rt}"]
            new_own_readings[rt] = {"book": book, "chapter_verses": cv}
            if book and cv:
                selected.append(f"{book} {cv}")
            elif book and not cv:
                incomplete.append(rt)

        if incomplete:
            st.error(f"Vul ook de hoofdstuk/verzen in voor: {', '.join(incomplete)}.")
        elif not selected:
            st.error("Selecteer minimaal één lezing (Boek én Hoofdstuk/verzen).")
        else:
            # Clear previous structured results if selection changed
            if st.session_state.get("selected_scriptures") != selected:
                st.session_state["structured_scriptures"] = []
                st.session_state["scriptures_approved"] = False
                
            st.session_state["own_readings"] = new_own_readings
            st.session_state["selected_scriptures"] = selected
            st.rerun()


def get_scripture_text(
    scripture_dict: dict[str, Any] | None,
) -> str:
    if scripture_dict is None:
        return ""
    reading = ""
    for item in scripture_dict.get("verses", []):
        verse_number = item.get("verse")
        verse_text = item.get("text")
        reading += f"{verse_number}. {verse_text} \n"

    return reading


@st.dialog("Details roosterlezing", width="large")
def show_scripture_details(scripture: dict[str, Any]) -> None:

    scripture_data = scripture.get("scriptures") or {}

    st.markdown(f'**Eerste lezing:\t{scripture.get("first_scripture")}**')
    st.markdown(f'{get_scripture_text(scripture_data.get("first_scripture"))}')
    st.markdown(f'**Tweede lezing:**\t{scripture.get("second_scripture")}')
    st.markdown(get_scripture_text(scripture_data.get("second_scripture")))
    st.markdown(f'**Psalm:**\t{scripture.get("psalm")}')
    st.markdown(get_scripture_text(scripture_data.get("psalm")))
    st.markdown(f'**Evangelie:**\t{scripture.get("gospel")}')
    st.markdown(get_scripture_text(scripture_data.get("gospel")))


def update(options: list[str]) -> None:
    st.session_state["selected_scriptures"] = options


def clean_up_session_state() -> None:
    keys_to_remove = [
        "selected_scriptures",
        "structured_scriptures",
        "scriptures_approved",
        "selected_scripture_id",
        "own_readings",
    ]
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]


def _analysis_is_locked() -> bool:
    """Return True if an analysis is in progress and the lock has not expired."""
    lock_time = st.session_state.get("analysis_lock_time")
    if lock_time is None:
        return False
    if time.time() - lock_time > ANALYSIS_LOCK_TIMEOUT_SECONDS:
        del st.session_state["analysis_lock_time"]
        return False
    return True


def _release_analysis_lock() -> None:
    st.session_state.pop("analysis_lock_time", None)


########### GET DATA ###########

churches = get_data("api/churches/")
song_books = get_cached_data("api/song-books/")
bible_versions = get_cached_data("api/bible-versions/")
liturgy = get_cached_data("api/liturgy/")
st.header("Nieuwe analyse")

if "selected_scriptures" not in st.session_state:
    st.session_state["selected_scriptures"] = []

if "structured_scriptures" not in st.session_state:
    st.session_state["structured_scriptures"] = []

if "own_readings" not in st.session_state:
    st.session_state["own_readings"] = {rt: {"book": "", "chapter_verses": ""} for rt in READING_TYPES}

### FORM ###

selected_church = st.selectbox(
    "Selecteer de gemeente voor deze kerkdienst",
    options=churches,
    format_func=lambda church: church["name"],
)

title = st.text_input("Thema (optioneel)", max_chars=64)
_today = date.today()
_next_sunday = _today + timedelta(days=(6 - _today.weekday()) % 7)
sermon_date = st.date_input(
    "Datum van de kerkdienst", value=_next_sunday, format="DD-MM-YYYY", min_value="today"
)
song_books = st.multiselect(
    "Selecteer de liedboeken die in deze kerkdienst gebruikt worden (optioneel):",
    placeholder="Geen liedboeken geselecteerd",
    options=song_books,
    format_func=lambda book: book["name"],
)

bible_version = st.selectbox(
    "Selecteer de bijbelvertaling die in deze kerkdienst gebruikt wordt (optioneel):",
    placeholder="Geen bijbelvertaling geselecteerd",
    options=bible_versions,
    format_func=lambda version: version["version"],
)

core_scripture = st.text_input(
    "Voeg een kernlezing toe (optioneel)",
    max_chars=64,
    value="",
    placeholder="Geen kernlezing toegevoegd",
)


scriptures_choice = st.radio(
    "Schriftlezingen", options=["Kerkelijk rooster volgen", "Eigen lezingen"]
)

if scriptures_choice == "Kerkelijk rooster volgen":

    selected_liturgy = [
        l for l in liturgy if l.get("date") == sermon_date.strftime("%Y-%m-%d")
    ]

    if len(selected_liturgy) == 0:
        st.warning(
            "Er zijn geen roosterlezingen gevonden voor de geselecteerde datum. Kies een andere datum of selecteer 'Eigen lezingen' om handmatig lezingen toe te voegen."
        )
    else:
        st.session_state["selected_scripture_id"] = selected_liturgy[0].get("id")
        show_scriptures = st.button("Roosterlezingen tonen")
        if show_scriptures:
            show_scripture_details(selected_liturgy[0])


if scriptures_choice == "Eigen lezingen":
    st.markdown("### Eigen lezingen")
    any_lezing = False
    for rt in READING_TYPES:
        data = st.session_state.own_readings.get(rt, {})
        if data.get("book") and data.get("chapter_verses"):
            st.write(f"- **{rt}**: {data['book']} {data['chapter_verses']}")
            any_lezing = True
    
    if not any_lezing:
        st.info("Er zijn nog geen lezingen toegevoegd.")
        
    if st.button("Lezingen configureren"):
        show_own_readings_dialog()

extra_context = st.text_area("Extra context (optioneel):", height=150, max_chars=1024)

if scriptures_choice == "Eigen lezingen":
    collect_structured_scriptures = st.button("Lezingen ophalen", disabled=not any_lezing)

if scriptures_choice == "Eigen lezingen" and collect_structured_scriptures:

    with st.status(
        "Lezingen structureren (afhankelijk van het aantal lezingen kan dit even duren)..."
    ):

        st.session_state["structured_scriptures"] = get_structured_scriptures(
            scriptures=st.session_state["selected_scriptures"],
            bible_version=bible_version.get("version") if bible_version else None,
            language="nl",
        )

        # st.session_state['structured_scriptures'] = load_scriptures()

    # save_scriptures(structured_scriptures)

for scripture in st.session_state["structured_scriptures"]:

    with st.expander(f"**{scripture.get('original_scripture')}**", expanded=False):

        for sc in scripture.get("scriptures", []):
            st.markdown(f"Hoofdstuk **{sc.get('chapter')}**")
            for verse in sc.get("verses", []):
                st.markdown(f"**{verse.get('number')}**")
                st.markdown(f"{verse.get('text')}")

            st.write("---")

if (
    "structured_scriptures" in st.session_state
    and len(st.session_state["structured_scriptures"]) > 0
):

    st.session_state["scriptures_approved"] = st.checkbox(
        "Ik bevestig dat de data zoals hierboven vermeldt, correct zijn en klaar voor analyse",
        value=False,
    )

_locked = _analysis_is_locked()

if _locked:
    elapsed = int(time.time() - st.session_state["analysis_lock_time"])
    remaining = ANALYSIS_LOCK_TIMEOUT_SECONDS - elapsed
    st.info(f"Er loopt al een analyse. Nog {remaining} seconden voordat u opnieuw kunt proberen.")

submit = st.button("Analyse starten", type="primary", disabled=_locked)

if submit:
    # Validation for Eigen lezingen
    if scriptures_choice == "Eigen lezingen":
        if not st.session_state.get("structured_scriptures"):
            st.error("Haal eerst de lezingen op via de knop 'Lezingen ophalen'.")
            st.stop()
        if not st.session_state.get("scriptures_approved"):
            st.error("Bevestig eerst dat de opgehaalde lezingen correct zijn.")
            st.stop()

    st.session_state["analysis_lock_time"] = time.time()
    try:
        sermon_analysis_model = SermonAnalysisModel(
            church=selected_church["id"],
            title=title,
            sermon_date=sermon_date,
            liturgy=st.session_state.get("selected_scripture_id"),
            core_scriptures=core_scripture,
            scripture_json=st.session_state.get("structured_scriptures") or [],
            use_calendar=(scriptures_choice == "Kerkelijk rooster volgen"),
            song_books=[book["id"] for book in song_books],
            extra_context=extra_context,
            bible_version=bible_version["id"] if bible_version else None,
        )

        data = json.loads(sermon_analysis_model.model_dump_json())

        st.session_state["api_handler"].post(endpoint="api/sermon-analyses/", data=data)

        clean_up_session_state()
        _release_analysis_lock()
        st.switch_page(f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py")
    except Exception as e:
        _release_analysis_lock()
        st.error(f"Er is een fout opgetreden bij het starten van de analyse: {e}")
        st.stop()
