from typing import Any

import streamlit as st

from src.utils.utils import render_verse_layout


def _is_hebrew(text: str) -> bool:
    return any("֐" <= ch <= "׿" for ch in text)


def _verse_int(number: Any) -> int | None:
    """Geef het versnummer als int, of None bij iets niet-numerieks.

    Versnummers zijn meestal int of decimaal-string ("13"). Sommige
    bronnen leveren een letter-suffix ("5a") of een range ("13-14");
    voor groepering moeten die als 'niet-vergelijkbaar' gezien worden
    omdat we anders 5a en 5b ten onrechte zouden samenvouwen.
    """
    if isinstance(number, int):
        return number
    if isinstance(number, str) and number.isdigit():
        return int(number)
    return None


def _format_verse_range(numbers: list[Any]) -> str:
    """Formatteer een groep versnummers als enkel nummer of bereik.

    Eén nummer → "13". Twee of meer opeenvolgende ints → "13-14".
    Niet-opeenvolgende of niet-numerieke nummers → komma-gescheiden
    ("13, 14, 15"). De groepering-logica garandeert in praktijk altijd
    een opeenvolgend bereik (we breken bij een gat), maar de format-
    helper blijft defensief zodat een toekomstige bron met afwijkende
    nummering niet een misleidende range "13-99" oplevert.
    """
    if len(numbers) == 1:
        return str(numbers[0])
    ints = [_verse_int(n) for n in numbers]
    if all(i is not None for i in ints) and ints == list(range(ints[0], ints[-1] + 1)):
        return f"{numbers[0]}-{numbers[-1]}"
    return ", ".join(str(n) for n in numbers)


def _groepeer_samengevoegde_verzen(
    verses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Vouw opeenvolgende verzen met identieke tekst samen tot één entry.

    Achtergrond: sommige vertalingen (BGT, en bij brontekst-zijde ook
    Hebreeuws/Grieks) presenteren twee opeenvolgende verzen als één
    samengevoegd tekstblok. De scraper levert in dat geval voor elk
    versnummer dezelfde tekst, omdat downstream-filteren op vers-bereik
    ("13-14") anders één van de twee zou missen. In de UI is dat
    cosmetisch fout: dezelfde regel zou twee keer onder elkaar staan.

    Deze helper detecteert dat patroon door per groep zowel `modern_text`
    als `source_text` (na trim-normalisatie identiek aan de render-laag)
    te vergelijken én te eisen dat de versnummers consecutief zijn.
    Daarmee wordt:
    - v13 + v14 met identieke vertaling én identieke brontekst → één
      blok met label "13-14".
    - v13 + v14 met identieke vertaling maar verschillende brontekst →
      twéé blokken (we mogen de brontekst niet stilletjes wegmoffelen).
    - v13 + v15 met identieke tekst → twéé blokken (geen consecutie,
      vermoedelijk toeval).

    Het terugresultaat is een lijst van groep-entries met dezelfde shape
    als de input plus een `numbers`-lijst voor labelvorming.
    """
    groepen: list[dict[str, Any]] = []
    for verse in verses:
        if not isinstance(verse, dict):
            continue
        modern = (verse.get("modern_text") or "").rstrip()
        source = (verse.get("source_text") or "").strip()
        number = verse.get("number", "")

        if groepen:
            laatste = groepen[-1]
            laatste_int = _verse_int(laatste["numbers"][-1])
            huidige_int = _verse_int(number)
            consecutief = (
                laatste_int is not None
                and huidige_int is not None
                and huidige_int == laatste_int + 1
            )
            zelfde_tekst = (
                modern == laatste["modern_text"]
                and source == laatste["source_text"]
            )
            if consecutief and zelfde_tekst and modern:
                # Lege `modern_text` mag níet samenvouwen — anders zou een
                # rij verzen zonder vertaling als één 'leeg' blok worden
                # weergegeven, wat verwarrender is dan ze los te laten.
                laatste["numbers"].append(number)
                continue

        groepen.append(
            {
                "numbers": [number],
                "modern_text": modern,
                "source_text": source,
            }
        )
    return groepen


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

        # Vouw opeenvolgende verzen met identieke tekst samen vóór het
        # renderen — voorkomt dubbele regels bij samengevoegde verzen
        # (BGT v13-14, Hebreeuws/Grieks dat over twee versnummers loopt).
        for groep in _groepeer_samengevoegde_verzen(verses):
            label = _format_verse_range(groep["numbers"])
            modern_text = groep["modern_text"]
            source_text = groep["source_text"]

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
