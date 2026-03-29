from typing import Any

import streamlit as st

from src.utils.utils import clean_md


def postille(analysis: dict[str, Any], latest_results: dict[str, Any] | None = None) -> None:
    """Render a preekschets (postille) analysis result."""
    result: dict[str, Any] = analysis.get("result", {})
    # Pipeline B stores fields at the top level; Pipeline A wraps them in "preekschets"
    preekschets: dict[str, Any] = result.get("preekschets", result)
    sermon: dict[str, Any] = analysis.get("sermon_analysis", {})
    metadata: dict[str, Any] = preekschets.get("metadata", {})
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
            st.caption(f"**Datum kerkdienst:** {sermon['sermon_date']}")

    # ── Kerntekst ─────────────────────────────────────────────────────────────
    if metadata.get("kerntekst"):
        st.info(f"📖 {metadata['kerntekst']}")

    # ── Oneliner ──────────────────────────────────────────────────────────────
    if metadata.get("oneliner"):
        st.success(f"💡 *{metadata['oneliner']}*")

    st.divider()

    # ── Schriftlezingen ───────────────────────────────────────────────────────
    schriftlezingen: dict = preekschets.get("schriftlezingen", {})
    if schriftlezingen:
        with st.expander("📖 Schriftlezingen", expanded=False):
            if schriftlezingen.get("hoofdlezing"):
                st.markdown(f"**Hoofdlezing:** {schriftlezingen['hoofdlezing']}")
            aanvullend: list = schriftlezingen.get("aanvullend", [])
            if aanvullend:
                st.markdown("**Aanvullende lezingen:** " + ", ".join(aanvullend))

    # ── Eigene van de zondag ──────────────────────────────────────────────────
    with st.expander("🗓️ Eigene van de zondag", expanded=True):
        st.markdown(clean_md(preekschets.get("eigene_van_de_zondag", "")))

    # ── Uitleg / Exegese ──────────────────────────────────────────────────────
    with st.expander("🔍 Uitleg & exegese", expanded=True):
        st.markdown(clean_md(preekschets.get("uitleg", "")))

    # ── Aanwijzingen prediking ────────────────────────────────────────────────
    with st.expander("🎤 Aanwijzingen voor de prediking", expanded=True):
        st.markdown(clean_md(preekschets.get("aanwijzingen_prediking", "")))

    # ── Liturgische aanwijzingen ──────────────────────────────────────────────
    st.divider()
    st.header("🎵 Liturgische aanwijzingen")

    # Prefer full song suggestions from the specialized analysis if available
    liederen = None
    if latest_results and "liedsuggesties" in latest_results:
        liederen = latest_results["liedsuggesties"].get("result", {}).get("liederen")

    if liederen:
        from page_navigation.analysis_results.analyses.liedsuggesties import render_liederen_list
        render_liederen_list(liederen)
    else:
        # Fallback to internal songs if for some reason the full analysis is missing
        liedsuggesties_fallback: list[dict] = liturgische_aanwijzingen.get("liedsuggesties", [])
        if liedsuggesties_fallback:
            for lied in liedsuggesties_fallback:
                with st.container(border=True):
                    bundel = lied.get("bundel", "")
                    nummer = lied.get("nummer", "")
                    st.markdown(f"**{lied.get('titel', '')}** &mdash; {bundel} {nummer}", unsafe_allow_html=True)
                    if lied.get("motivatie"):
                        st.caption(lied["motivatie"])

    aanvullende_lezingen = liturgische_aanwijzingen.get("aanvullende_lezingen")
    if aanvullende_lezingen:
        with st.expander("📖 Aanvullende lezingen", expanded=False):
            if isinstance(aanvullende_lezingen, list):
                for lezing in aanvullende_lezingen:
                    st.markdown(f"- {clean_md(str(lezing))}")
            else:
                st.markdown(clean_md(str(aanvullende_lezingen)))
