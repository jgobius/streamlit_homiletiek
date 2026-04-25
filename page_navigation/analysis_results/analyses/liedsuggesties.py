import re
from collections import defaultdict
from typing import Any

import streamlit as st

# Canonieke volgorde van liturgische gebruiksmomenten — alleen nog gebruikt
# als tiebreak binnen één bundel als twee liederen hetzelfde nummer hebben
# (zeldzaam, maar niet onmogelijk bij Liedboek-suffixen als 23a/23a-bis).
_GEBRUIK_ORDER = [
    "Intocht",
    "Kyrie",
    "Gloria",
    "Schriftlied",
    "Tussenzang",
    "Voorbeden",
    "Avondmaal",
    "Slotlied",
    "Zegen",
]

_MATCH_LABELS: dict[str, str] = {
    "Schriftlezing": "📖 Schriftlezing",
    "Thematisch": "🎯 Thematisch",
    "Seizoen": "📅 Seizoen",
    "Contextueel": "🔗 Contextueel",
    "Emotioneel": "💙 Emotioneel",
    "Verrassend": "✨ Verrassend",
}

# Bundels zonder officieel liednummersysteem. Hun "nummer" is een interne
# database-index (volgorde in de bron) en komt niet overeen met enig
# extern bekend nummer — tonen werkt verwarrend, dus laten we hem weg.
_BUNDELS_ZONDER_OFFICIEEL_NUMMER: frozenset[str] = frozenset({
    "Sela",
    "Schrijvers voor Gerechtigheid",
})

# Patroon voor onbruikbare 'eerste regel'-waardes: pure couplet-markers
# ("1", "1."), losse streepjes en de '(onbekend)'-placeholder uit de
# prompt-builder. Deze ontstaan in de embed-pipeline voor multi-couplet
# bundels zonder titel-marker (Liedboek, Op Toonhoogte, Weerklank).
_BOGUS_EERSTE_REGEL_RE = re.compile(r"^\s*(?:\d+\s*\.?|-+|\(onbekend\))\s*$")

# Placeholder die de prompt-builder injecteert wanneer titel ontbreekt;
# mag nooit als zichtbare titel naar de gebruiker doorlekken.
_PLACEHOLDER_TITEL = "(geen titel beschikbaar)"


def _gebruik_sort_key(gebruik_str: str) -> int:
    """Laagste rang onder de pipe-gescheiden gebruiksmomenten — tiebreak."""
    parts = [p.strip() for p in gebruik_str.split("|")]
    ranks = [_GEBRUIK_ORDER.index(p) if p in _GEBRUIK_ORDER else 99 for p in parts]
    return min(ranks) if ranks else 99


def _nummer_sort_key(nummer: Any) -> tuple[int, str]:
    """Natuurlijke sort op liednummer: 5, 23, 23a, 23b, 100, 1006.

    Liedbundels gebruiken integers met een optionele alfabetische staart
    (Liedboek 23a, 23b, 23f). Pure `int()` zou crashen op '23a';
    string-vergelijking plaatst '100' vóór '23'. Vandaar deze tweetraps key.
    Niet-parseerbare nummers (zoals het soms door het model gehallucineerde
    '428:1-NL') belanden achteraan.
    """
    s = str(nummer or "").strip()
    m = re.match(r"^(\d+)([a-zA-Z]?)", s)
    if m:
        return int(m.group(1)), m.group(2).lower()
    return 10**9, s.lower()


def _zuiver_titel(titel: str) -> str:
    """Verwijder de prompt-placeholder; geef anders de titel ongewijzigd terug."""
    titel = (titel or "").strip()
    return "" if titel == _PLACEHOLDER_TITEL else titel


def _zuiver_eerste_regel(eerste_regel: str) -> str:
    """Filter pure couplet-markers en placeholders weg.

    De embed-pipeline schrijft voor multi-couplet bundels zonder titel-marker
    soms '1.' weg als 'eerste regel' — dat is de verse-header, geen tekst.
    Voor de gebruiker is zo'n waarde nutteloos en willen we hem niet tonen.
    """
    eerste_regel = (eerste_regel or "").strip()
    if not eerste_regel or _BOGUS_EERSTE_REGEL_RE.match(eerste_regel):
        return ""
    return eerste_regel


def _is_titel_redundant_voor_nummer(titel: str, nummer: Any) -> bool:
    """True als de titel niets meer is dan een herhaling van het liednummer.

    Sommige bundels leveren als titel niet meer dan 'Lied 10a' of 'Psalm 136';
    dat dupliceert visueel het nummer in de naast-staande kolom. In dat geval
    is de eerste regel informatiever als hoofdtitel.
    """
    if not titel or not nummer:
        return False
    nr_str = re.escape(str(nummer).strip())
    return bool(
        re.fullmatch(
            rf"(?:Lied|Psalm)\s+{nr_str}",
            titel.strip(),
            flags=re.IGNORECASE,
        )
    )


def _bepaal_kop_en_caption(
    titel: str, eerste_regel: str, nummer: Any
) -> tuple[str, str]:
    """Bepaal welke regel als hoofdtitel en welke als caption verschijnt.

    Returnt `(hoofdtitel, caption)`. Caption is leeg als hij geen meerwaarde
    heeft naast de hoofdtitel (identiek of bogus). Strategie: altijd zoveel
    mogelijk informatieve tekst tonen, want het nummer alleen is voor de
    gebruiker meestal niet voldoende om een lied te herkennen.
    """
    titel = _zuiver_titel(titel)
    eerste_regel = _zuiver_eerste_regel(eerste_regel)

    # 'Lied 10a' / 'Psalm 136' herhaalt enkel het nummer — promoveer dan
    # de eerste regel naar hoofdtitel.
    if _is_titel_redundant_voor_nummer(titel, nummer) and eerste_regel:
        return eerste_regel, ""

    # Zonder zinvolle titel: gebruik de eerste regel als hoofdtitel.
    if not titel and eerste_regel:
        return eerste_regel, ""

    # Beide zinvol en verschillend: titel boven, eerste regel als caption.
    if titel and eerste_regel and titel != eerste_regel:
        return titel, eerste_regel

    # Verder: alleen titel (eventueel zelf leeg).
    return titel, ""


def _render_lied(lied: dict[str, Any]) -> None:
    nummer = str(lied.get("nummer", "") or "").strip()
    bundel = lied.get("bundel", "")
    titel = lied.get("titel", "")
    eerste_regel = lied.get("eerste_regel", "")
    karakter = lied.get("karakter", "")
    toelichting = lied.get("toelichting", "")
    type_match = lied.get("type_match", "")
    suggestie_gebruik = lied.get("suggestie_gebruik", "")

    hoofdtitel, caption_regel = _bepaal_kop_en_caption(titel, eerste_regel, nummer)

    # Bundels zonder officieel nummersysteem (Sela, Schrijvers vG) krijgen
    # geen aparte nummer-kolom — hun nummer is alleen interne db-volgorde.
    toon_nummer = bool(nummer) and bundel not in _BUNDELS_ZONDER_OFFICIEEL_NUMMER

    with st.container(border=True):
        if toon_nummer:
            col_nr, col_title = st.columns([1, 8])
            with col_nr:
                st.markdown(f"### {nummer}")
            with col_title:
                if hoofdtitel:
                    st.markdown(f"**{hoofdtitel}**")
                if caption_regel:
                    st.caption(f"*{caption_regel}*")
        else:
            if hoofdtitel:
                st.markdown(f"**{hoofdtitel}**")
            if caption_regel:
                st.caption(f"*{caption_regel}*")

        if karakter:
            st.caption(f"🎵 {karakter}")

        if toelichting:
            st.write(toelichting)

        tag_cols = st.columns(2)
        with tag_cols[0]:
            if type_match:
                labels = " · ".join(
                    _MATCH_LABELS.get(t.strip(), t.strip())
                    for t in type_match.split("|")
                )
                st.caption(labels)
        with tag_cols[1]:
            if suggestie_gebruik:
                st.caption("🕐 " + " · ".join(s.strip() for s in suggestie_gebruik.split("|")))


def liedsuggesties(analysis: dict[str, Any]) -> None:
    """Render liedsuggesties analysis result, gegroepeerd per bundel."""
    result: dict[str, Any] = analysis.get("result", {})
    liederen: list[dict] = result.get("liederen", [])

    st.caption(f"{len(liederen)} liedsuggesties")

    st.divider()

    # ── Groeperen per bundel ──────────────────────────────────────────────────
    by_bundel: dict[str, list[dict]] = defaultdict(list)
    for lied in liederen:
        bundel = lied.get("bundel", "Overig")
        by_bundel[bundel].append(lied)

    # Bundels alfabetisch
    for bundel in sorted(by_bundel.keys()):
        liederen_in_bundel = by_bundel[bundel]
        with st.expander(f"📚 {bundel} ({len(liederen_in_bundel)})", expanded=False):
            # Primair op nummer (natuurlijke sort: 5, 23, 23a, 100). Bij
            # gelijke nummers gebruiken we het liturgisch moment als
            # tiebreak — anders zou de oude (ongesorteerde) volgorde
            # binnenglippen via Python's stable sort.
            sorted_liederen = sorted(
                liederen_in_bundel,
                key=lambda l: (
                    _nummer_sort_key(l.get("nummer", "")),
                    _gebruik_sort_key(l.get("suggestie_gebruik", "")),
                ),
            )
            for lied in sorted_liederen:
                _render_lied(lied)
