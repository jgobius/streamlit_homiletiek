import re
from collections import defaultdict
from typing import Any

import streamlit as st

from src.utils.utils import clean_md

MATCH_LABELS: dict[str, str] = {
    "Schriftlezing": "📖 Schriftlezing",
    "Thematisch": "🎯 Thematisch",
    "Seizoen": "📅 Seizoen",
    "Contextueel": "🔗 Contextueel",
    "Emotioneel": "💙 Emotioneel",
    "Verrassend": "✨ Verrassend",
}


def render_lied(lied: dict[str, Any]) -> None:
    nummer = lied.get("nummer", "")
    titel = lied.get("titel", "")
    eerste_regel = lied.get("eerste_regel", "")
    karakter = lied.get("karakter", "")
    toelichting = lied.get("toelichting", "")
    type_match = lied.get("type_match", "")
    suggestie_gebruik = lied.get("suggestie_gebruik", "")

    with st.container(border=True):
        col_nr, col_title = st.columns([1, 8])
        with col_nr:
            st.markdown(f"### {nummer}")
        with col_title:
            st.markdown(f"**{titel}**")
            if eerste_regel and eerste_regel != titel:
                st.caption(f"*{eerste_regel}*")

        if karakter:
            st.caption(f"🎵 {karakter}")

        if toelichting:
            st.markdown(clean_md(toelichting))

        tag_cols = st.columns(2)
        with tag_cols[0]:
            if type_match:
                labels = " · ".join(
                    MATCH_LABELS.get(t.strip(), t.strip())
                    for t in type_match.split("|")
                )
                st.caption(labels)
        with tag_cols[1]:
            if suggestie_gebruik:
                st.caption("🕐 " + " · ".join(s.strip() for s in suggestie_gebruik.split("|")))


def nummer_sort_key(n_str: str) -> tuple[int, str]:
    # Extract leading digits
    match = re.match(r"(\d+)(.*)", str(n_str))
    if match:
        return int(match.group(1)), match.group(2)
    return 99999, str(n_str)


def render_liederen_list(liederen: list[dict[str, Any]]) -> None:
    """Render a list of songs grouped by bundel."""
    # ── Group by bundel ───────────────────────────────────────────────────────
    by_bundel: dict[str, list[dict]] = defaultdict(list)
    for lied in liederen:
        bundel = lied.get("bundel", "Overig")
        by_bundel[bundel].append(lied)

    # Sort bundels alphabetically
    for bundel in sorted(by_bundel.keys()):
        liederen_in_bundel = by_bundel[bundel]
        with st.expander(f"📚 {bundel} ({len(liederen_in_bundel)})", expanded=False):
            # Sort within expander primarily by nummer
            sorted_liederen = sorted(
                liederen_in_bundel,
                key=lambda l: nummer_sort_key(l.get("nummer", "")),
            )
            for lied in sorted_liederen:
                render_lied(lied)


def liedsuggesties(analysis: dict[str, Any]) -> None:
    """Render liedsuggesties analysis result, grouped by bundel."""
    result: dict[str, Any] = analysis.get("result", {})
    sermon: dict[str, Any] = analysis.get("sermon_analysis", {})
    liederen: list[dict] = result.get("liederen", [])

    if sermon.get("sermon_date"):
        st.caption(f"**Datum kerkdienst:** {sermon['sermon_date']}")
    st.caption(f"{len(liederen)} liedsuggesties")

    st.divider()

    render_liederen_list(liederen)
