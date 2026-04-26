"""Dialoogvenster om de schriftlezingen en liedbundels van een bestaande
analyse aan te passen.

Bij het aanmaken van een analyse worden lezingen en liedbundels in
``page_navigation/analyses/new_analysis.py`` vastgelegd; daarna was er geen
UI meer om ze te wijzigen. Deze dialog wordt geopend vanuit de
"Selectie instellen"-knop op het Basis-tabblad in
``page_navigation/analysis_results/overview.py`` en biedt dezelfde
controls (boek + hoofdstuk/verzen per lezing, multiselect-liedbundels)
zodat de voorganger de selectie achteraf nog kan corrigeren zonder een
nieuwe analyse te hoeven starten.
"""

from typing import Any

import requests
import streamlit as st

from src.api.agent_request import AgentRequest
from src.utils.utils import (
    BIBLE_BOOKS,
    READING_TYPES,
    get_structured_scriptures,
    parse_original_scripture,
    sanitize_cv,
)


# De Liturgy-tabel slaat boeknamen soms in een vorm op die niet identiek is
# aan ``BIBLE_BOOKS`` in ``src/utils/utils.py``. ``parse_original_scripture``
# valt dan terug op een leeg boek, en de dialog wist vervolgens ook het
# hoofdstuk/verzen-veld (zie ``if not book_selected`` verderop), waardoor
# de hele lezing onzichtbaar leeg opent. Normaliseer hier centraal zodat de
# parser ongewijzigd blijft. Bekende afwijking nu: 'Psalm 66' (NL singular,
# zoals het rooster opslaat) versus 'Psalmen' (NL plural, de canonieke vorm
# in BIBLE_BOOKS en scripture_json). Andere afwijkingen die we in het
# lectionary tegenkwamen (Matteüs/Mattheüs, Zacharias/Zacharia, Sirach,
# Wijsheid) komen pas via een nieuwe analyse aan de oppervlakte; voeg een
# alias toe zodra een gebruiker er last van krijgt.
_LECTIONARY_BOEK_ALIASES: dict[str, str] = {"Psalm": "Psalmen"}


def _normaliseer_lectionary_boek(s: str) -> str:
    """Vervang een lectionary-boeknaam door de variant uit BIBLE_BOOKS.

    Werkt alleen op de boek-prefix (gevolgd door een spatie) zodat een
    eventueel verschijnend hoofdstuk/verzen-deel onaangeraakt blijft.
    """
    for alias, canoniek in _LECTIONARY_BOEK_ALIASES.items():
        prefix = f"{alias} "
        if s.startswith(prefix):
            return f"{canoniek} {s[len(prefix):]}"
    return s


def _lectionary_readings(sermon_analysis: dict[str, Any]) -> list[str]:
    """Haal de roosterlezingen op uit de geneste liturgy van een
    kerkelijk-rooster-analyse.

    Bij ``use_calendar=True`` wordt ``scripture_json`` bij het aanmaken niet
    gevuld (zie ``new_analysis.py``: alleen ``selected_scripture_id`` wordt
    meegestuurd), waardoor de selectie-dialog zonder fallback met lege velden
    opende. De read-serializer geeft ``liturgy`` met depth=2 terug, dus we
    kunnen ``first_scripture``/``second_scripture``/``psalm``/``gospel``
    rechtstreeks uitlezen. Lege/None-velden filteren we eruit zodat de
    overgebleven lezingen netjes in de eerste N slots terechtkomen — en niet
    een lege "Tweede lezing"-slot doorschuift naar de derde positie.
    """
    liturgy = sermon_analysis.get("liturgy")
    # Defensief: als een toekomstige serializer-aanpassing alleen het ID
    # retourneert (int) i.p.v. een nested dict, kunnen we niets uitlezen.
    if not isinstance(liturgy, dict):
        return []
    velden = ("first_scripture", "second_scripture", "psalm", "gospel")
    return [
        _normaliseer_lectionary_boek(str(liturgy[v]).strip())
        for v in velden if liturgy.get(v)
    ]


def _hydrate_state(analysis_id: int, sermon_analysis: dict[str, Any]) -> None:
    """Vul de session-state van de dialog vanuit de huidige sermon_analysis.

    We gebruiken een per-analyse-prefix (``sel_dlg_<id>_…``) zodat de keys
    niet botsen met de eigen-lezingen-dialog in new_analysis.py, die
    dezelfde widget-namen (``book_select_<rt>`` etc.) gebruikt maar op
    pagina-niveau session-state deelt.
    """
    prefix = f"sel_dlg_{analysis_id}_"

    # Idempotent: alleen de eerste opening hydrateert; daarna bewaart de
    # widget-state zelf de gebruikerswijzigingen tot het dialog gesloten wordt.
    if st.session_state.get(f"{prefix}hydrated"):
        return

    # ── Schriftlezingen vanuit scripture_json terugparsen ─────────────────
    own_readings: dict[str, dict[str, str]] = {
        rt: {"book": "", "chapter_verses": ""} for rt in READING_TYPES
    }
    scripture_json = sermon_analysis.get("scripture_json") or []
    # Lijst van originele leesstrings ("Genesis 1:1-3", …) die we als basis
    # voor de hydratatie gebruiken. Voor "Eigen lezingen"-analyses komt deze
    # uit scripture_json; voor "Kerkelijk rooster volgen"-analyses is
    # scripture_json bij het aanmaken leeg en vallen we terug op de geneste
    # liturgy zodat de roosterlezingen alsnog vooringevuld verschijnen.
    bronlezingen: list[str] = [
        item.get("original_scripture") or "" for item in scripture_json
    ]
    if not any(bronlezingen):
        bronlezingen = _lectionary_readings(sermon_analysis)

    for i, original in enumerate(bronlezingen[: len(READING_TYPES)]):
        boek, cv = parse_original_scripture(original)
        own_readings[READING_TYPES[i]] = {"book": boek, "chapter_verses": cv}

    st.session_state[f"{prefix}own_readings"] = own_readings
    # Aantal lezingen: minimaal 1, maximaal len(READING_TYPES). We tellen op
    # basis van de gevulde bronlezingen — een lege bron levert 1 op zodat de
    # gebruiker direct een eerste lezing kan invullen.
    aantal = max(
        1,
        min(len(bronlezingen) or 1, len(READING_TYPES)),
    )
    st.session_state[f"{prefix}count"] = aantal

    # Pre-vul widget-keys zodat de selectbox/text_input direct de juiste
    # default tonen bij de eerste render binnen het dialog.
    for rt in READING_TYPES:
        data = own_readings[rt]
        st.session_state[f"{prefix}book_{rt}"] = data["book"]
        st.session_state[f"{prefix}cv_{rt}"] = data["chapter_verses"]

    # ── Liedbundels: read-serializer levert nested dicts (depth=2) ─────────
    huidige_song_books = sermon_analysis.get("song_books") or []
    if huidige_song_books and isinstance(huidige_song_books[0], dict):
        st.session_state[f"{prefix}song_book_ids"] = [
            sb["id"] for sb in huidige_song_books
        ]
    else:
        # Defensief: als een toekomstige serializer-aanpassing IDs i.p.v.
        # nested objects retourneert, accepteren we die ook zonder crash.
        st.session_state[f"{prefix}song_book_ids"] = list(huidige_song_books)

    st.session_state[f"{prefix}hydrated"] = True


def _wis_state(analysis_id: int) -> None:
    """Verwijder alle session-state-keys van deze dialog-instantie.

    Wordt na een succesvolle PATCH aangeroepen zodat een volgende opening
    de dialog opnieuw vanuit de (bijgewerkte) backend-data hydrateert in
    plaats van met verouderde widget-waardes.
    """
    prefix = f"sel_dlg_{analysis_id}_"
    for key in list(st.session_state.keys()):
        if key.startswith(prefix):
            del st.session_state[key]


@st.dialog("Selectie instellen", width="large")
def selectie_instellen_dialog(
    analysis_id: int,
    sermon_analysis: dict[str, Any],
    song_books_options: list[dict[str, Any]],
) -> None:
    """Pop-up om schriftlezingen (1-4) en liedbundels achteraf aan te passen."""
    _hydrate_state(analysis_id, sermon_analysis)
    prefix = f"sel_dlg_{analysis_id}_"

    st.write(
        "Pas hieronder de schriftlezingen en de geselecteerde liedbundels aan. "
        "Na opslaan worden de bijbelteksten automatisch opnieuw opgehaald."
    )

    # ── Schriftlezingen ────────────────────────────────────────────────────
    st.subheader("Schriftlezingen")
    count = st.session_state[f"{prefix}count"]
    active_types = READING_TYPES[:count]

    book_options = [""] + BIBLE_BOOKS
    for rt in active_types:
        st.markdown(f"**{rt}**")
        col1, col2 = st.columns([1, 1])

        # We zetten de defaults al in _hydrate_state via session_state, dus
        # geven hier géén `index=` mee — Streamlit waarschuwt anders dat een
        # widget zowel een default als een session_state-waarde heeft. Als de
        # gehydrateerde waarde toevallig niet in BIBLE_BOOKS staat (bv. een
        # boeknaam die later hernoemd is), valt de selectbox terug op "".
        with col1:
            if st.session_state.get(f"{prefix}book_{rt}", "") not in book_options:
                st.session_state[f"{prefix}book_{rt}"] = ""
            st.selectbox(
                f"Bijbelboek ({rt})",
                options=book_options,
                key=f"{prefix}book_{rt}",
                label_visibility="collapsed",
            )
        with col2:
            book_selected = bool(st.session_state.get(f"{prefix}book_{rt}", ""))
            cv_key = f"{prefix}cv_{rt}"
            # Leegmaken als er geen boek geselecteerd is — voorkomt dat een
            # weggeklikt boek toch een dangling chapter/verses-string achterlaat.
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

    # + / − knoppen identiek aan de eigen-lezingen-dialog in new_analysis.py.
    btn_col1, btn_col2 = st.columns([1, 1])
    with btn_col1:
        if count < len(READING_TYPES):
            if st.button("+ Lezing toevoegen", key=f"{prefix}add"):
                st.session_state[f"{prefix}count"] = count + 1
                # scope="fragment" herstart alleen het dialoogvenster zodat het
                # open blijft na de rerun.
                st.rerun(scope="fragment")
    with btn_col2:
        if count > 1:
            if st.button("- Lezing verwijderen", key=f"{prefix}remove"):
                last_rt = READING_TYPES[count - 1]
                st.session_state[f"{prefix}book_{last_rt}"] = ""
                st.session_state[f"{prefix}cv_{last_rt}"] = ""
                st.session_state[f"{prefix}count"] = count - 1
                st.rerun(scope="fragment")

    st.divider()

    # ── Liedbundels ────────────────────────────────────────────────────────
    st.subheader("Liedbundels")
    huidige_ids = st.session_state.get(f"{prefix}song_book_ids", [])
    default_books = [b for b in song_books_options if b.get("id") in huidige_ids]
    geselecteerde_bundels = st.multiselect(
        "Selecteer de liedbundels (minimaal één verplicht):",
        options=song_books_options,
        default=default_books,
        format_func=lambda book: book["name"],
        key=f"{prefix}song_books_widget",
        placeholder="Geen liedbundels geselecteerd",
    )

    st.markdown("---")

    if not st.button("Opslaan en sluiten", type="primary", key=f"{prefix}save"):
        return

    # ── Validatie ─────────────────────────────────────────────────────────
    nieuwe_lezingen: list[str] = []
    onvolledig: list[str] = []
    for rt in active_types:
        boek = st.session_state.get(f"{prefix}book_{rt}", "")
        cv = st.session_state.get(f"{prefix}cv_{rt}", "")
        if boek and cv:
            nieuwe_lezingen.append(f"{boek} {cv}")
        elif boek and not cv:
            onvolledig.append(rt)

    if onvolledig:
        st.error(
            f"Vul ook de hoofdstuk/verzen in voor: {', '.join(onvolledig)}."
        )
        return
    if not nieuwe_lezingen:
        st.error("Selecteer minimaal één lezing (Boek én Hoofdstuk/verzen).")
        return
    if not geselecteerde_bundels:
        st.error("Selecteer minimaal één liedbundel.")
        return

    # ── Wijzigingen detecteren ────────────────────────────────────────────
    # Vergelijk de nieuwe selectie met de oorspronkelijke uit sermon_analysis.
    # Geen wijziging → niets doen (dialog sluiten zonder API-/LLM-calls).
    # Alleen liedbundels gewijzigd → PATCH zonder de structured-scripture-LLM
    # opnieuw te draaien. Alleen lezingen gewijzigd, of beide → volledig pad.
    oorspronkelijke_lezingen = [
        item.get("original_scripture", "") or ""
        for item in (sermon_analysis.get("scripture_json") or [])
    ]
    # Bij rooster-analyses is scripture_json leeg bij het aanmaken; zonder
    # deze fallback zou een ongewijzigde roosterselectie als 'gewijzigd'
    # gelden en een onnodige structured-scripture-LLM-call triggeren.
    if not any(oorspronkelijke_lezingen):
        oorspronkelijke_lezingen = _lectionary_readings(sermon_analysis)
    nieuwe_song_book_ids = sorted(b["id"] for b in geselecteerde_bundels)
    oorspronkelijke_song_books = sermon_analysis.get("song_books") or []
    oorspronkelijke_song_book_ids = sorted(
        sb["id"] if isinstance(sb, dict) else sb for sb in oorspronkelijke_song_books
    )

    lezingen_gewijzigd = nieuwe_lezingen != oorspronkelijke_lezingen
    bundels_gewijzigd = nieuwe_song_book_ids != oorspronkelijke_song_book_ids

    if not lezingen_gewijzigd and not bundels_gewijzigd:
        # Geen verschil — dialog gewoon sluiten zonder netwerkverkeer.
        _wis_state(analysis_id)
        st.rerun()

    handler = st.session_state["api_handler"]

    if lezingen_gewijzigd:
        # ── Verzen synchroon ophalen via de structured-scripture-agent ─────
        # Zelfde flow als bij het aanmaken van een analyse (new_analysis.py:384):
        # de gebruiker krijgt direct een fout als een lezing niet gestructureerd
        # kan worden, in plaats van pas een asynchrone fout in een latere rerun.
        bible_version_obj = sermon_analysis.get("bible_version") or {}
        bible_version_str = (
            bible_version_obj.get("version")
            if isinstance(bible_version_obj, dict)
            else None
        )
        with st.status("Lezingen structureren (kan even duren)..."):
            nieuwe_scripture_json = get_structured_scriptures(
                scriptures=nieuwe_lezingen,
                bible_version=bible_version_str,
                language="nl",
            )

        # Lege lezingen (geen verzen gevonden) blokkeren de PATCH — anders zou de
        # Bijbelteksten-tab na opslaan stilletjes leeg blijven en moest de
        # voorganger zelf raden waarom.
        lege: list[str] = [
            sc.get("original_scripture") or "(onbekende lezing)"
            for sc in nieuwe_scripture_json
            if not any((s.get("verses") or []) for s in (sc.get("scriptures") or []))
        ]
        if lege:
            st.error(
                "Geen bijbeltekst gevonden voor: "
                + ", ".join(f"'{t}'" for t in lege)
                + ". Controleer de spelling van het bijbelboek en probeer het opnieuw."
            )
            return

        payload: dict[str, Any] = {
            "scripture_json": nieuwe_scripture_json,
            "song_books": nieuwe_song_book_ids,
        }
    else:
        # Alleen liedbundels zijn gewijzigd — geen LLM-call nodig.
        payload = {"song_books": nieuwe_song_book_ids}

    try:
        handler.patch(f"api/sermon-analyses/{analysis_id}/", data=payload)
    except requests.exceptions.HTTPError as exc:
        st.error(f"Opslaan mislukt: {exc}. Probeer het opnieuw.")
        return

    # ── Bijbelteksten-renderer opnieuw triggeren (alleen bij lezing-wijziging) ─
    # /original_scriptures/ koppelt de verzen aan een AnalysisResult van het
    # type 'bijbelteksten'. Faalt deze stap, dan blijft scripture_json wél
    # bijgewerkt — de gebruiker kan dan zelf via de "Opnieuw"-knop op de
    # Bijbelteksten-analyse de renderer alsnog herstarten.
    if lezingen_gewijzigd:
        try:
            AgentRequest().post(
                "original_scriptures/",
                payload={"sermon_analysis_id": analysis_id},
            )
        except requests.exceptions.RequestException as exc:
            st.warning(
                "Selectie is opgeslagen, maar de bijbelteksten konden niet "
                f"automatisch ververst worden ({exc}). Klik op 'Opnieuw' bij de "
                "Bijbelteksten-analyse om ze handmatig op te halen."
            )

    # ── Cache invalideren + dialog-state opruimen ─────────────────────────
    # Zelfde key als overview.py:1369 gebruikt — zo haalt de eerstvolgende
    # rerun de bijgewerkte sermon_analysis (incl. scripture_json en
    # song_books) opnieuw uit de backend.
    st.session_state.pop(f"overview_data_{analysis_id}", None)
    _wis_state(analysis_id)
    st.rerun()
