import json
import time
from datetime import date, datetime, timedelta
from typing import Any

import streamlit as st

from src.models.sermon_analysis_model import SermonAnalysisModel
from src.api.agent_request import AgentRequest
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
    sanitize_cv,
    valideer_tekstinvoer,
)

# Woorden-limiet voor het vrije 'Extra context'-veld. 500 woorden is ruim
# genoeg voor een beschrijving van bijzondere omstandigheden van de dienst
# (bv. rouwdienst, thema, doelgroep) maar voorkomt dat het een complete preek
# wordt — wat de prompt onbedoeld zou doen aanzwellen.
_MAX_WOORDEN_EXTRA_CONTEXT = 500

redirect_to_login()

# Na het starten van een analyse wordt een lock ingesteld om dubbele inzendingen te voorkomen.
_ANALYSIS_LOCK_TIMEOUT_SECONDS = 120


########### HULPFUNCTIES ###########

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
                on_change=sanitize_cv,
                args=(cv_key,),
            )

    btn_col1, btn_col2 = st.columns([1, 1])
    with btn_col1:
        if count < len(READING_TYPES):
            if st.button("+ Lezing toevoegen"):
                st.session_state["own_readings_count"] = count + 1
                # scope="fragment" herstart alleen het dialoogvenster, zodat het open blijft
                st.rerun(scope="fragment")
    with btn_col2:
        if count > 1:
            if st.button("- Lezing verwijderen"):
                last_rt = READING_TYPES[count - 1]
                st.session_state["own_readings"][last_rt] = {"book": "", "chapter_verses": ""}
                st.session_state.pop(f"book_select_{last_rt}", None)
                st.session_state.pop(f"cv_input_{last_rt}", None)
                st.session_state["own_readings_count"] = count - 1
                # scope="fragment" herstart alleen het dialoogvenster, zodat het open blijft
                st.rerun(scope="fragment")

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

# Als er nog geen gemeenten zijn, is de selectbox hierboven leeg ("No options
# to select") en kan een analyse sowieso niet gestart worden. De rest van het
# formulier blijft zichtbaar zodat de lay-out niet verspringt, maar we
# informeren de gebruiker expliciet dat er eerst een gemeente toegevoegd moet
# worden. `st.info` gebruikt dezelfde blauwe stijl als andere lege-staatmeldingen.
if not churches:
    st.info(
        "⛪ Er zijn nog geen gemeenten. Voeg eerst een gemeente toe via de "
        "'+'-knop hierboven of via **Gemeenten** in het menu; pas daarna kan "
        "een analyse gestart worden."
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

# Gestructureerde lezingen tonen in uitklapbare secties. Per lezing houden we
# bij of hij bruikbaar is (d.w.z. minstens één vers). Een lezing zónder verzen
# betekent dat de scripture-agent geen bijbeltekst heeft kunnen koppelen (bv.
# boeknaam niet herkend, Tavily gaf geen match voor de gekozen vertaling) —
# dan zou de gebruiker anders een lege expander zien en een analyse starten
# die gegarandeerd faalt op de bijbeltekst-stap.
_lege_lezingen: list[str] = []
for scripture in st.session_state["structured_scriptures"]:
    # /structured_scripture/ levert sinds de fix het inner scripture_json-dict
    # direct ({original_scripture, scriptures}); geen extra unwrap nodig. Voor
    # de Celery-refactor gaf de endpoint hetzelfde contract; tijdens de Celery-
    # tussenstand werd de volledige State-dump teruggegeven en moest hier nog
    # een `.get("scripture_json")`-unwrap staan.
    _heeft_verzen = any(
        (sc.get("verses") or []) for sc in (scripture.get('scriptures') or [])
    )
    _titel = scripture.get("original_scripture") or "(onbekende lezing)"
    with st.expander(f"**{_titel}**", expanded=not _heeft_verzen):
        if not _heeft_verzen:
            st.error(
                f"Geen bijbeltekst gevonden voor **{_titel}**. Controleer de "
                "spelling van het bijbelboek en probeer het opnieuw via de knop "
                "'Lezingen ophalen'. Zolang deze lezing leeg is kun je de "
                "analyse niet starten."
            )
            _lege_lezingen.append(_titel)
            continue
        for sc in scripture.get("scriptures", []):
            st.markdown(f"Hoofdstuk **{sc.get('chapter')}**")
            for verse in sc.get("verses", []):
                st.markdown(f"**{verse.get('number')}**")
                st.markdown(f"{verse.get('text')}")
            st.write("---")

if st.session_state.get("structured_scriptures"):
    # Bevestig-checkbox blokkeren zolang er nog lege lezingen zijn. Anders kan
    # de gebruiker 'Analyse starten' indrukken met een half-gevulde set, wat
    # downstream (bijbelteksten-agent, /original_scriptures/) faalt.
    if _lege_lezingen:
        st.warning(
            "Eén of meer lezingen zijn niet opgehaald: "
            + ", ".join(f"'{t}'" for t in _lege_lezingen)
            + ". Los dit eerst op voordat je de analyse start."
        )
        # We zetten scriptures_approved expliciet op False zodat een eerdere
        # (bij een geslaagde poging gezette) True-waarde niet blijft hangen en
        # de analyse-knop per ongeluk actief wordt.
        st.session_state["scriptures_approved"] = False
    else:
        st.session_state["scriptures_approved"] = st.checkbox(
            "Ik bevestig dat de lezingen zoals hierboven vermeld correct zijn en klaar voor analyse",
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

    # Valideer het vrije 'Extra context'-veld: maximaal aantal woorden +
    # detectie van SQL-injectie-patronen. Gebeurt alleen hier bij submit,
    # niet live, zodat de gebruiker ongestoord kan typen. De cv_input- en
    # boek-selectvelden krijgen geen aparte check omdat _sanitize_cv en de
    # selectbox-whitelist al een veilige vorm afdwingen.
    ok_ctx, fout_ctx = valideer_tekstinvoer(
        extra_context or "",
        max_woorden=_MAX_WOORDEN_EXTRA_CONTEXT,
        veldnaam="Extra context",
    )
    if not ok_ctx:
        st.error(fout_ctx)
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
            bible_version=bible_version.get("id", None),
            extra_context=extra_context
        )
        data = json.loads(sermon_analysis_model.model_dump_json())
        result = st.session_state["api_handler"].post(endpoint="api/sermon-analyses/", data=data)
        sermon_analysis_id = result.get("id")

        # Auto-start het ophalen en koppelen van de bijbelteksten. Dit is een
        # mechanische stap (verzen uit de DB matchen aan de geselecteerde lezingen),
        # dus we gebruiken /original_scriptures/ in plaats van een AI-agent.
        # Zo worden alle lezingen (rooster of eigen) consistent verwerkt.
        # Een fout hier mag de gebruiker niet blokkeren; de tab 'Bijbelteksten'
        # toont dan simpelweg geen resultaat tot de analyse opnieuw gestart wordt.
        # AgentRequest zorgt voor de Bearer-header; /original_scriptures/ heeft
        # verify_jwt op de agent, dus zonder token zou de call stilletjes 401'en.
        if sermon_analysis_id:
            try:
                AgentRequest().post(
                    endpoint="original_scriptures/",
                    payload={"sermon_analysis_id": sermon_analysis_id},
                )
                # /original_scriptures/ retourneert direct; de agent schrijft het
                # resultaat in een FastAPI background_task (zie homiletiek_agent
                # api.py:139). Zonder hier te wachten haalt overview.py een lege
                # resultatenlijst op en ziet de gebruiker 'nog geen bijbeltekst
                # beschikbaar' tot hij handmatig op Ververs klikt. Een korte poll
                # (max 10s, stap 0.5s) dekt het normale geval; bij timeout blijft
                # de bestaande Ververs-knop in overview.py het vangnet.
                _bijbelteksten_deadline = time.monotonic() + 10.0
                with st.spinner("Bijbelteksten worden opgehaald..."):
                    while time.monotonic() < _bijbelteksten_deadline:
                        _resultaten = st.session_state["api_handler"].get(
                            f"api/analysis-results?sermon_analysis_id={sermon_analysis_id}"
                        ) or []
                        if any(
                            (r.get("analysis_type") or {}).get("name") == "bijbelteksten"
                            for r in _resultaten
                        ):
                            break
                        time.sleep(0.5)
            except Exception:
                pass

        _clean_up_session_state()
        _release_analysis_lock()
        # Markeer de dashboard-cache als vervuild zodat de nieuwe analyse zichtbaar is
        # als de gebruiker later terugkeert naar het dashboard.
        st.session_state["dashboard_data_dirty"] = True

        # Direct naar de overview-pagina van de zojuist aangemaakte analyse navigeren.
        # Bij gebrek aan een id (edge case: POST gaf geen id terug) valt de navigatie
        # terug op het dashboard zodat de gebruiker nooit op een lege pagina blijft.
        if sermon_analysis_id:
            st.session_state["current_analysis_id"] = sermon_analysis_id
            st.switch_page(
                f"{st.session_state['page_navigation_dir']}/analysis_results/overview.py",
                query_params={"analysis_id": sermon_analysis_id},
            )
        else:
            st.switch_page(f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py")

    except Exception as e:
        _release_analysis_lock()
        st.error(f"Er is een fout opgetreden bij het starten van de analyse: {e}")
        st.stop()
