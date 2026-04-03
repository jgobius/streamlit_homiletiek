from typing import Any

import streamlit as st

from src.utils.utils import clean_md

_NUMMER_BADGES = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]


def _render_list(values: list) -> None:
    for item in values:
        st.markdown(f"- {clean_md(str(item))}")


def focus_en_functie(analysis: dict[str, Any]) -> None:
    """Render focus en functie analysis result."""
    result: dict[str, Any] = analysis.get("result", {})

    opties: list = result.get("opties", [])

    if not opties:
        st.info("Geen opties gevonden.")
        return

    for optie in opties:
        nummer: int = optie.get("nummer", 0)
        badge = _NUMMER_BADGES[nummer - 1] if 1 <= nummer <= len(_NUMMER_BADGES) else str(nummer)
        korte_titel: str = optie.get("korte_titel", "")
        type_insteek: str = optie.get("type_insteek", "")

        with st.container(border=True):
            header_c1, header_c2 = st.columns([1, 6])
            with header_c1:
                st.markdown(f"# {badge}")
            with header_c2:
                st.subheader(korte_titel)
                if type_insteek:
                    st.caption(f"Type insteek: *{type_insteek}*")

            st.divider()

            c1, c2, c3 = st.columns(3)
            with c1:
                focus: str = optie.get("focus", "")
                if focus:
                    st.markdown("**1. Focus**")
                    st.markdown(clean_md(focus))
            with c2:
                anticipatie: str = optie.get("anticipatie", "")
                if anticipatie:
                    st.markdown("**2. Anticipatie**")
                    st.markdown(clean_md(anticipatie))
            with c3:
                functie: str = optie.get("functie", "")
                if functie:
                    st.markdown("**3. Functie**")
                    st.markdown(clean_md(functie))

            ant_analyse: dict = optie.get("anticipatie_analyse", {})
            if ant_analyse:
                with st.expander("Anticipatie-analyse", expanded=False):
                    if ant_analyse.get("herkenning"):
                        st.markdown(f"**Herkenning:** {clean_md(ant_analyse['herkenning'])}")
                    if ant_analyse.get("weerstand"):
                        st.markdown(f"**Weerstand:** {clean_md(ant_analyse['weerstand'])}")
                    vragen: list = ant_analyse.get("vragen", [])
                    if vragen:
                        st.markdown("**Vragen die dit oproept:**")
                        _render_list(vragen)

            toelichting: str = optie.get("toelichting", "")
            if toelichting:
                st.caption(clean_md(toelichting))

        st.divider()
