import re
from typing import Any

import streamlit as st

from src.utils.utils import clean_md


# Leestekens die het einde van een zin markeren. Een regel die hierop eindigt
# beschouwen we niet als kopje — kopjes bestaan uit losse korte regels zonder
# afsluitend leesteken.
_ZIN_EINDE: tuple[str, ...] = (".", "!", "?", ":", ";", ",", ")", "”", "’")


def _structureer_postille_tekst(tekst: str) -> str:
    """Voeg basisstructuur toe aan platte LLM-output van de postille.

    De LLM levert vaak markdown-loze tekst voor `eigene_van_de_zondag`,
    `uitleg` en `aanwijzingen_prediking`: korte regels fungeren als sectie-
    kopjes en genummerde items hebben een titel-stuk vóór de eerste dubbele
    punt, maar zonder vetgedrukt of `###`-prefix. Zonder hulp rendert
    Streamlit dit als één lange paragraaf.

    Twee transformaties:
    1. Genummerde items "1. Titel — context: uitleg" worden "1. **Titel — context:** uitleg".
    2. Een korte alleenstaande regel (na blank-line of aan begin) zonder
       afsluitend leesteken wordt een `### kopje`.
    """
    if not tekst:
        return tekst

    tekst = tekst.replace("\r\n", "\n").replace("\r", "\n")
    regels: list[str] = tekst.split("\n")

    nieuw: list[str] = []
    for idx, ruwe_regel in enumerate(regels):
        regel = ruwe_regel.rstrip()
        gestript = regel.strip()

        if not gestript:
            nieuw.append("")
            continue

        # Genummerd item: "1. Titel ... : body" of "1. Titel ... :"
        m = re.match(r"^(\s*)(\d+)\.\s+([^:\n]+?)\s*:\s*(.*)$", regel)
        if m:
            inspring, num, titel, body = m.group(1), m.group(2), m.group(3), m.group(4)
            if body:
                nieuw.append(f"{inspring}{num}. **{titel}:** {body}")
            else:
                nieuw.append(f"{inspring}{num}. **{titel}:**")
            continue

        # Kopje: korte alleenstaande regel zonder afsluitend leesteken,
        # voorafgegaan door een blanco regel (of het begin van de tekst).
        vorige_blanco = idx == 0 or not regels[idx - 1].strip()
        is_kort = len(gestript) <= 80
        geen_eindleesteken = not gestript.endswith(_ZIN_EINDE)
        begint_met_hoofdletter = gestript[:1].isupper() or gestript[:1] in {"“", "‘", "\""}
        if vorige_blanco and is_kort and geen_eindleesteken and begint_met_hoofdletter:
            nieuw.append(f"### {gestript}")
            continue

        nieuw.append(regel)

    return "\n".join(nieuw)


def _render_markdown(tekst: str) -> None:
    """Render een postille-tekstveld met clean_md + postille-structurering."""
    st.markdown(_structureer_postille_tekst(clean_md(tekst)))


def postille(analysis: dict[str, Any]) -> None:
    """Render a preekschets (postille) analysis result."""
    preekschets: dict[str, Any] = analysis.get("result", {}).get("preekschets", {})
    sermon: dict[str, Any] = analysis.get("sermon_analysis", {})
    metadata: dict[str, Any] = preekschets.get("metadata", {})
    schriftlezingen: dict[str, Any] = preekschets.get("schriftlezingen", {})
    liturgische_aanwijzingen: dict[str, Any] = preekschets.get("liturgische_aanwijzingen", {})

    # ── Header ────────────────────────────────────────────────────────────────
    col_left, col_right = st.columns([2, 1])
    with col_left:
        if metadata.get("perikoop"):
            st.caption(f"**Perikoop:** {metadata['perikoop']}")
        if metadata.get("liturgische_dag"):
            st.caption(f"**Liturgische dag:** {metadata['liturgische_dag']}")
    with col_right:
        if sermon.get("sermon_date"):
            st.caption(f"**Preekdatum:** {sermon['sermon_date']}")

    # ── Kerntekst ─────────────────────────────────────────────────────────────
    if metadata.get("kerntekst"):
        st.info(f"📖 {metadata['kerntekst']}")

    # ── Oneliner ──────────────────────────────────────────────────────────────
    if metadata.get("oneliner"):
        st.success(f"💡 *{metadata['oneliner']}*")

    st.divider()

    # ── Schriftlezingen ───────────────────────────────────────────────────────
    # Alleen de referenties tonen; de volledige bijbeltekst staat al in de
    # Bijbelteksten-analyse (zelfde Basis-tab) en hoeft hier niet herhaald.
    with st.expander("📚 Schriftlezingen", expanded=False):
        if schriftlezingen.get("hoofdlezing"):
            st.markdown(f"**Hoofdlezing:** {schriftlezingen['hoofdlezing']}")
        aanvullend: list = schriftlezingen.get("aanvullend", [])
        if aanvullend:
            st.markdown(f"**Aanvullend:** {', '.join(aanvullend)}")

    # ── Eigene van de zondag ──────────────────────────────────────────────────
    # clean_md herstelt letterlijke "\n" en spaties in bold-markers,
    # _structureer_postille_tekst voegt kopjes en vetgedrukte titels toe
    # aan de platte LLM-output zodat de structuur leesbaar wordt.
    with st.expander("🗓️ Eigene van de zondag", expanded=False):
        _render_markdown(preekschets.get("eigene_van_de_zondag", ""))

    # ── Uitleg / Exegese ──────────────────────────────────────────────────────
    with st.expander("🔍 Uitleg & exegese", expanded=False):
        _render_markdown(preekschets.get("uitleg", ""))

    # ── Aanwijzingen prediking ────────────────────────────────────────────────
    with st.expander("🎤 Aanwijzingen voor de prediking", expanded=False):
        _render_markdown(preekschets.get("aanwijzingen_prediking", ""))

    # ── Liturgische aanwijzingen ──────────────────────────────────────────────
    with st.expander("🎵 Liturgische aanwijzingen", expanded=False):
        liedsuggesties: list[dict] = liturgische_aanwijzingen.get("liedsuggesties", [])
        if liedsuggesties:
            st.markdown("**Liedsuggesties**")
            for lied in liedsuggesties:
                with st.container(border=True):
                    bundel = lied.get("bundel", "")
                    nummer = lied.get("nummer", "")
                    st.markdown(f"**{lied.get('titel', '')}** &mdash; {bundel} {nummer}", unsafe_allow_html=True)
                    if lied.get("motivatie"):
                        st.caption(lied["motivatie"])

        aanvullende_lezingen: str = liturgische_aanwijzingen.get("aanvullende_lezingen", "")
        if aanvullende_lezingen:
            st.markdown("**Aanvullende lezingen**")
            st.write(aanvullende_lezingen)
