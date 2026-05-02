from typing import Any

import streamlit as st

from src.utils.utils import (
    format_verse_range,
    groepeer_samengevoegde_verzen,
    render_verse_layout,
)


def _is_hebrew(text: str) -> bool:
    return any("֐" <= ch <= "׿" for ch in text)


def _spreid_source_text(verses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Geef lege source_text-verzen de brontekst van een buur met identieke
    modern_text. Bedoeld als UI-vangnet voor samengevoegde verzen.

    De agent doet deze spreid al in `_match_verses` (homiletiek_agent), maar
    bestaande `scripture_json`-records die vóór die fix zijn opgeslagen
    hebben de oude shape (één van de twee samengevoegde verzen heeft een
    lege source_text). Zonder deze stap zou `groepeer_samengevoegde_verzen`
    v13 (gevuld) en v14 (leeg) als 'verschillend' beschouwen en niet
    samenvouwen, en zou de prediker dezelfde modern_text twee keer onder
    elkaar zien.

    Spreid alleen wanneer:
    - opeenvolgende verzen identieke modern_text hebben, én
    - één van de bronteksten leeg is en de andere gevuld.

    De spread loopt zowel voor- als achterwaarts zodat het niet uitmaakt
    of het gevulde vers links of rechts van het lege staat. We muteren
    een kopie van de input zodat downstream-data niet wijzigt.
    """
    schoon = [dict(v) if isinstance(v, dict) else v for v in verses]

    def _bron(v: dict[str, Any]) -> str:
        return (v.get("source_text") or "").strip()

    def _modern(v: dict[str, Any]) -> str:
        return (v.get("modern_text") or "").rstrip()

    # Forward: vul een leeg vers met de brontekst van de vorige.
    for i in range(1, len(schoon)):
        cur, prev = schoon[i], schoon[i - 1]
        if (
            isinstance(cur, dict) and isinstance(prev, dict)
            and _modern(cur) and _modern(cur) == _modern(prev)
            and not _bron(cur) and _bron(prev)
        ):
            cur["source_text"] = prev["source_text"]
    # Backward: vul een leeg vers met de brontekst van de volgende.
    for i in range(len(schoon) - 2, -1, -1):
        cur, nxt = schoon[i], schoon[i + 1]
        if (
            isinstance(cur, dict) and isinstance(nxt, dict)
            and _modern(cur) and _modern(cur) == _modern(nxt)
            and not _bron(cur) and _bron(nxt)
        ):
            cur["source_text"] = nxt["source_text"]
    return schoon


def bijbelteksten(analysis: dict[str, Any]) -> None:
    """Render bijbelteksten analysis result."""
    result: Any = analysis.get("result")

    # Titel, actieknoppen én de afsluitende scheidingslijn worden centraal in
    # overview.py getoond, zodat alle tabs dezelfde kop hebben
    # (titel → actieknoppen → lijn → inhoud). Deze renderer begint daarom
    # direct met de eigen inhoud.

    # `result` is een lijst van lezing-entries in liturgische leesvolgorde
    # (eerste lezing → psalm → tweede lezing → evangelie). Elke entry heeft
    # een 'reference'-veld met de originele referentie. We gebruiken een
    # lijst in plaats van een dict-op-referentie omdat Postgres jsonb
    # object-key-volgorde niet bewaart, maar list-volgorde wél.
    if not isinstance(result, list):
        st.info("Nog geen bijbeltekst beschikbaar.")
        return

    for scripture in result:
        if not isinstance(scripture, dict):
            continue
        scripture_ref = (scripture.get("reference") or "").rstrip(".").strip()
        st.subheader(scripture_ref)
        verses: list[dict] = scripture.get("verses", [])

        # Eerst lege bronteksten over consecutieve identieke modern_text-
        # verzen heen aanvullen (UI-vangnet voor scripture_json-records
        # die vóór de agent-spread-fix zijn opgeslagen). Daarna pas
        # samenvouwen — anders zou de groepering nog steeds een lege
        # vs. gevulde source_text als 'verschillend' zien.
        verses = _spreid_source_text(verses)

        # Vouw opeenvolgende verzen met identieke tekst samen vóór het
        # renderen — voorkomt dubbele regels bij samengevoegde verzen
        # (BGT v13-14, Hebreeuws/Grieks dat over twee versnummers loopt).
        # text_fields=("modern_text", "source_text") eist dat *beide*
        # velden gelijk zijn; alleen-NL-gelijk maar verschillende brontekst
        # blijft dan apart staan zodat de Hebreeuws/Grieks-nuances
        # zichtbaar blijven.
        groepen = groepeer_samengevoegde_verzen(
            verses, text_fields=("modern_text", "source_text")
        )
        for groep in groepen:
            label = format_verse_range(groep["numbers"])
            # `modern_text` voor weergave: rstrip houdt leading whitespace
            # intact — de Naardense Bijbel gebruikt dat als poëtische
            # inspringing. De helper deed hierboven `.strip()` alleen voor
            # de identiteits-vergelijking, niet voor de waarde zelf.
            modern_text = (groep["modern_text"] or "").rstrip()
            source_text = (groep["source_text"] or "").strip()

            st.markdown(
                f"<span style='color:grey;font-size:0.85em;font-weight:bold;'>{label}</span>"
                f"&nbsp;&nbsp;{render_verse_layout(modern_text)}",
                unsafe_allow_html=True,
            )
            if source_text:
                is_heb = _is_hebrew(source_text)
                direction = "rtl" if is_heb else "ltr"
                align = "right" if is_heb else "left"
                st.markdown(
                    f"<p style='color:#888;font-size:0.8em;font-style:italic;"
                    f"direction:{direction};text-align:{align};margin-top:2px;'>"
                    f"{source_text}</p>",
                    unsafe_allow_html=True,
                )

        st.write("")
