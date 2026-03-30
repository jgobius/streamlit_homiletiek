from typing import Any

import streamlit as st

from src.utils.utils import clean_md

_TYPE_BADGE = {
    "Kernachtig/Klassiek": "🔵",
    "Experimenteel/Creatief": "🟣",
}


def _render_notie(notie: dict) -> None:
    naam = notie.get("naam", "")
    type_ = notie.get("type", "")
    badge = _TYPE_BADGE.get(type_, "⚪")
    definitie = notie.get("definitie_context", "")
    samenvatting = notie.get("korte_samenvatting", "")
    uitwerking = notie.get("systematische_uitwerking", "")
    zoektermen: list = notie.get("engelse_zoektermen", [])

    with st.expander(f"{badge} {naam}  —  *{type_}*", expanded=False):
        if definitie:
            st.info(definitie)

        if samenvatting:
            st.markdown(f"**Korte samenvatting**")
            st.markdown(clean_md(samenvatting))

        if zoektermen:
            st.caption("🔎 **Zoektermen voor verdere verkenning:** " + " · ".join(zoektermen))

        if uitwerking:
            st.markdown("**Systematische uitwerking**")
            st.markdown(clean_md(uitwerking))


def theologie(analysis: dict[str, Any]) -> None:
    """Render theologie analysis result."""
    result: dict[str, Any] = analysis.get("result", {})
    sermon: dict[str, Any] = analysis.get("sermon_analysis", {})

    st.divider()

    # ── Synthese ──────────────────────────────────────────────────────────────
    synthese: dict = result.get("synthese", {})
    if synthese:
        st.subheader("💡 Synthese")
        if synthese.get("verbanden"):
            st.markdown("**Verbanden**")
            st.markdown(clean_md(synthese["verbanden"]))
        if synthese.get("homiletische_focus"):
            st.markdown("**Homiletische focus**")
            st.success(synthese["homiletische_focus"])

    st.divider()

    # ── Theologische noties ───────────────────────────────────────────────────
    # Pipeline B stores noties at the top level; Pipeline A wraps them in "theologische_analyse"
    noties: list[dict] = result.get("noties") or result.get("theologische_analyse", {}).get("noties", [])
    if noties:
        st.subheader(f"📚 Theologische noties ({len(noties)})")
        for notie in noties:
            _render_notie(notie)
