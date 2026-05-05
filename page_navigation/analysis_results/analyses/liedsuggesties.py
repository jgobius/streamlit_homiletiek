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
# Oke4Kids zit hier ook in: de bundel kent in de praktijk geen vaste
# nummering die voorgangers gebruiken — titel + eerste regel zijn de
# enige informatieve identifier.
_BUNDELS_ZONDER_OFFICIEEL_NUMMER: frozenset[str] = frozenset({
    "Sela",
    "Schrijvers voor Gerechtigheid",
    "Oke4Kids",
})

# Patroon voor onbruikbare 'eerste regel'-waardes: pure couplet-markers
# ("1", "1."), refrein-aanduidingen ('Refrein', 'Refr.', 'refr.', 'ref.'),
# losse streepjes en de '(onbekend)'-placeholder uit de prompt-builder.
# Deze ontstaan in de embed-pipeline en lekken anders 1-op-1 naar de UI.
_BOGUS_EERSTE_REGEL_RE = re.compile(
    r"^\s*(?:\d+\s*\.?|refrein|refr\.?|ref\.|-+|\(onbekend\)):?\s*$",
    re.IGNORECASE,
)

# Inline couplet-prefix die in oudere analyse-resultaten in eerste_regel
# blijft staan ('1. <tekst>', '1 <tekst>'). Bij nieuwe re-embeddings is
# deze prefix al weggehaald, maar oude AnalysisResult-rijen bevatten hem
# nog — daarom strippen we hem ook hier in de renderer voor consistente
# weergave. Eis dat wat ná de prefix komt met een letter begint, zodat
# we cijferreeksen in echte teksten (telversjes als '1 2 3 4 5 6 7 8'
# in Oke4Kids 14) niet ten onrechte ontmantelen.
_LEADING_COUPLET_PREFIX_RE = re.compile(
    r"^\s*\d+\s*\.?\s+([A-Za-zÀ-ÖØ-öø-ÿ].*)$"
)

# Placeholder die de prompt-builder injecteert wanneer titel ontbreekt;
# mag nooit als zichtbare titel naar de gebruiker doorlekken.
_PLACEHOLDER_TITEL = "(geen titel beschikbaar)"

# Trailing leestekens en witruimte die LLMs soms aan een bundelnaam
# plakken ('Opwekking,' i.p.v. 'Opwekking'). Zonder normaliseren
# verschijnen 'Opwekking (14)' en 'Opwekking, (1)' als aparte
# expanders in het bundeloverzicht — we strippen daarom alle trailing
# komma's, puntkomma's en punten plus omliggende spaties zodat één
# logische bundel ook één groep wordt.
_TRAILING_LEESTEKENS_RE = re.compile(r"[\s,;.]+$")


def _normaliseer_bundelnaam(bundel: Any) -> str:
    """Strip trailing leestekens/whitespace uit een bundelnaam.

    Voorkomt dat varianten als 'Opwekking' en 'Opwekking,' als twee
    verschillende bundels in het overzicht verschijnen. We raken alleen
    achterliggende leestekens aan — interne spaties en hoofdletters
    blijven behouden, omdat 'Op Toonhoogte' en 'Op Toonhoogte
    inspiratiebundel' wél bewust aparte bundels zijn.
    """
    s = str(bundel or "").strip()
    return _TRAILING_LEESTEKENS_RE.sub("", s)


# Sinds de schema-wijziging (gemini-3-flash-preview compatibility) leveren
# `type_match` en `suggestie_gebruik` arrays in plaats van `|`-gescheiden
# strings. Oudere AnalysisResult-rijen bevatten nog wél de string-vorm,
# dus normaliseren we beide naar list[str] zodat de renderer-logica één
# pad heeft.
def _normaliseer_meervoud(waarde: Any) -> list[str]:
    """Geef een waarde altijd terug als list[str] — accepteert array én pipe-string."""
    if isinstance(waarde, list):
        return [str(v).strip() for v in waarde if str(v).strip()]
    if isinstance(waarde, str) and waarde:
        return [p.strip() for p in waarde.split("|") if p.strip()]
    return []


def _gebruik_sort_key(gebruik: Any) -> int:
    """Laagste rang onder de gebruiksmomenten — tiebreak."""
    parts = _normaliseer_meervoud(gebruik)
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
    """Filter bogus markers weg en strip inline couplet-prefixes.

    Drie soorten waardes komen vanuit de embed-pipeline of oude analyse-
    resultaten binnen waar we niets aan hebben:

    1. Pure couplet-markers ('1', '1.') uit multi-couplet bundels.
    2. Refrein-aanduidingen ('Refrein', 'Refr.', 'refrein:').
    3. Echte regels met inline couplet-prefix ('1. <tekst>') uit NPB en
       JdH waar de coupletten als losse regels in één DB-verse staan.

    Categorie 1 en 2 leveren niets op en worden volledig weggefilterd.
    Bij categorie 3 knippen we alleen de prefix eraf zodat de gebruiker
    de echte tekst overhoudt.
    """
    eerste_regel = (eerste_regel or "").strip()
    if not eerste_regel or _BOGUS_EERSTE_REGEL_RE.match(eerste_regel):
        return ""
    m_prefix = _LEADING_COUPLET_PREFIX_RE.match(eerste_regel)
    if m_prefix:
        return m_prefix.group(1).strip()
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
    # Ook hier normaliseren — anders ontsnapt 'Schrijvers voor
    # Gerechtigheid,' aan de _BUNDELS_ZONDER_OFFICIEEL_NUMMER-check
    # en zou er alsnog een (interne) nummer-kolom verschijnen.
    bundel = _normaliseer_bundelnaam(lied.get("bundel", ""))
    titel = lied.get("titel", "")
    eerste_regel = lied.get("eerste_regel", "")
    karakter = lied.get("karakter", "")
    toelichting = lied.get("toelichting", "")
    # Normaliseer naar list[str] — accepteert zowel de nieuwe array-vorm
    # als oudere `|`-gescheiden strings uit historische analyses.
    type_match = _normaliseer_meervoud(lied.get("type_match", ""))
    suggestie_gebruik = _normaliseer_meervoud(lied.get("suggestie_gebruik", ""))

    hoofdtitel, caption_regel = _bepaal_kop_en_caption(titel, eerste_regel, nummer)

    # Bundels zonder officieel nummersysteem (Sela, Schrijvers vG) krijgen
    # geen aparte nummer-kolom — hun nummer is alleen interne db-volgorde.
    toon_nummer = bool(nummer) and bundel not in _BUNDELS_ZONDER_OFFICIEEL_NUMMER

    with st.container(border=True):
        # Nummer + titel renderen we als één markdown-regel zodat ze op
        # exact dezelfde baseline staan en even groot zijn. De oude opzet
        # met `st.columns` + `### {nummer}` zette het nummer als h3-kop
        # naast bold body-tekst, wat zowel verticaal scheef als visueel
        # te groot uitviel.
        if toon_nummer and hoofdtitel:
            st.markdown(f"**{nummer}** &nbsp;·&nbsp; **{hoofdtitel}**")
        elif toon_nummer:
            st.markdown(f"**{nummer}**")
        elif hoofdtitel:
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
                    _MATCH_LABELS.get(t, t) for t in type_match
                )
                st.caption(labels)
        with tag_cols[1]:
            if suggestie_gebruik:
                st.caption("🕐 " + " · ".join(suggestie_gebruik))


def liedsuggesties(analysis: dict[str, Any]) -> None:
    """Render liedsuggesties analysis result, gegroepeerd per bundel."""
    result: dict[str, Any] = analysis.get("result", {})
    liederen: list[dict] = result.get("liederen", [])

    st.caption(f"{len(liederen)} liedsuggesties")

    st.divider()

    # ── Groeperen per bundel ──────────────────────────────────────────────────
    # Normaliseer de bundelnaam zodat 'Opwekking' en 'Opwekking,' als één
    # groep verschijnen; lege of alleen-uit-leestekens-bestaande namen
    # vallen terug op 'Overig'.
    by_bundel: dict[str, list[dict]] = defaultdict(list)
    for lied in liederen:
        bundel = _normaliseer_bundelnaam(lied.get("bundel", "")) or "Overig"
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
