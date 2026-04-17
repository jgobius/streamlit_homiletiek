from typing import Any

import streamlit as st

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
            st.write(samenvatting)

        if zoektermen:
            st.caption("🔎 " + " · ".join(zoektermen))

        if uitwerking:
            st.markdown("**Systematische uitwerking**")
            st.markdown(uitwerking)


def theologie(analysis: dict[str, Any]) -> None:
    """Render theologie analysis result."""
    result: dict[str, Any] = analysis.get("result", {})

    # Toon de analysenaam als paginatitel.
    st.title(analysis.get("analysis_type", {}).get("front_end_name", "Theologie"))
    st.divider()

    # ── Synthese ──────────────────────────────────────────────────────────────
    synthese: dict = result.get("synthese", {})
    if synthese:
        st.subheader("💡 Synthese")
        if synthese.get("verbanden"):
            st.markdown("**Verbanden**")
            st.write(synthese["verbanden"])
        if synthese.get("homiletische_focus"):
            st.markdown("**Homiletische focus**")
            st.success(synthese["homiletische_focus"])

    st.divider()

    # ── Theologische noties ───────────────────────────────────────────────────
    noties: list[dict] = result.get("theologische_analyse", {}).get("noties", [])
    if noties:
        st.subheader(f"📚 Theologische noties ({len(noties)})")
        for notie in noties:
            _render_notie(notie)
