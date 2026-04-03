from collections import defaultdict
from typing import Any

import streamlit as st

# Canonical display order for liturgical use-moments
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


def _gebruik_sort_key(gebruik_str: str) -> int:
    """Return lowest rank among the pipe-separated use-moment values."""
    parts = [p.strip() for p in gebruik_str.split("|")]
    ranks = [_GEBRUIK_ORDER.index(p) if p in _GEBRUIK_ORDER else 99 for p in parts]
    return min(ranks)


def _render_lied(lied: dict[str, Any]) -> None:
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
    """Render liedsuggesties analysis result, grouped by bundel."""
    result: dict[str, Any] = analysis.get("result", {})
    sermon: dict[str, Any] = analysis.get("sermon_analysis", {})
    liederen: list[dict] = result.get("liederen", [])

    st.title(sermon.get("title", "Liedsuggesties"))
    if sermon.get("sermon_date"):
        st.caption(f"**Preekdatum:** {sermon['sermon_date']}")
    st.caption(f"{len(liederen)} liedsuggesties")

    st.divider()

    # ── Group by bundel ───────────────────────────────────────────────────────
    by_bundel: dict[str, list[dict]] = defaultdict(list)
    for lied in liederen:
        bundel = lied.get("bundel", "Overig")
        by_bundel[bundel].append(lied)

    # Sort liederen within each bundel by nummer
    for bundel in by_bundel:
        by_bundel[bundel].sort(key=lambda l: (
            int(l["nummer"]) if str(l.get("nummer", "")).isdigit() else 9999
        ))

    # Sort bundels alphabetically
    for bundel in sorted(by_bundel.keys()):
        liederen_in_bundel = by_bundel[bundel]
        with st.expander(f"📚 {bundel} ({len(liederen_in_bundel)})", expanded=False):
            # Secondary sort within expander: by liturgical use-moment
            sorted_liederen = sorted(
                liederen_in_bundel,
                key=lambda l: _gebruik_sort_key(l.get("suggestie_gebruik", "")),
            )
            for lied in sorted_liederen:
                _render_lied(lied)
