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
            st.caption(f"**Datum kerkdienst:** {sermon['sermon_date']}")

    # ── Kerntekst ─────────────────────────────────────────────────────────────
    if metadata.get("kerntekst"):
        st.info(f"📖 {metadata['kerntekst']}")

    # ── Oneliner ──────────────────────────────────────────────────────────────
    if metadata.get("oneliner"):
        st.success(f"💡 *{metadata['oneliner']}*")

    st.divider()

    # ── Schriftlezingen ───────────────────────────────────────────────────────
    with st.expander("📚 Schriftlezingen", expanded=True):
        if schriftlezingen.get("hoofdlezing"):
            st.markdown(f"**Hoofdlezing:** {schriftlezingen['hoofdlezing']}")
        aanvullend: list = schriftlezingen.get("aanvullend", [])
        if aanvullend:
            st.markdown(f"**Aanvullend:** {', '.join(aanvullend)}")

        scripture_json: list = sermon.get("scripture_json", [])
        if scripture_json:
            st.markdown("---")
            for reading in scripture_json:
                st.markdown(f"*{reading.get('original_scripture', '')}*")
                for scripture in reading.get("scriptures", []):
                    book = scripture.get("book", "")
                    chapter = scripture.get("chapter", "")
                    for verse in scripture.get("verses", []):
                        st.markdown(
                            f"<span style='color:grey;font-size:0.85em;'>"
                            f"{book} {chapter}:{verse['number']}</span>&nbsp;&nbsp;"
                            f"{verse['text']}",
                            unsafe_allow_html=True,
                        )
                st.write("")

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
    with st.expander("🎵 Liturgische aanwijzingen", expanded=True):
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
            st.markdown(clean_md(aanvullende_lezingen))
