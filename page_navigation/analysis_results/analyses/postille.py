from typing import Any

import streamlit as st

from src.utils.utils import clean_md


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
    # clean_md herstelt letterlijke "\n" en spaties in bold-markers (** tekst **),
    # zodat LLM-output met kopjes en vetgedrukte termen correct rendert.
    with st.expander("🗓️ Eigene van de zondag", expanded=False):
        st.markdown(clean_md(preekschets.get("eigene_van_de_zondag", "")))

    # ── Uitleg / Exegese ──────────────────────────────────────────────────────
    with st.expander("🔍 Uitleg & exegese", expanded=False):
        st.markdown(clean_md(preekschets.get("uitleg", "")))

    # ── Aanwijzingen prediking ────────────────────────────────────────────────
    with st.expander("🎤 Aanwijzingen voor de prediking", expanded=False):
        st.markdown(clean_md(preekschets.get("aanwijzingen_prediking", "")))

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
