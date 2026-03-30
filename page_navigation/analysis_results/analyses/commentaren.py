from typing import Any

import streamlit as st

from src.utils.utils import clean_md


def _render_exegese(exegese: dict) -> None:
    titel = exegese.get("titel", "")
    schriftgedeelte = exegese.get("schriftgedeelte", "")
    korte_samenvatting = exegese.get("korte_samenvatting", "")
    tekst = exegese.get("tekst", "")

    st.subheader(f"{schriftgedeelte}" + (f" — {titel}" if titel else ""))

    if korte_samenvatting:
        st.info(korte_samenvatting)

    if tekst:
        with st.expander("📖 Volledige exegese", expanded=False):
            st.markdown(clean_md(tekst))


def commentaren(analysis: dict[str, Any]) -> None:
    """Render commentaries (commentaren) analysis result."""
    result: dict[str, Any] = analysis.get("result", {})
    sermon: dict[str, Any] = analysis.get("sermon_analysis", {})

    st.divider()

    # ── Eerste lezing ─────────────────────────────────────────────────────────
    eerste = result.get("exegese_eerste_lezing")
    if eerste:
        _render_exegese(eerste)
        st.divider()

    # ── Evangelielezing ───────────────────────────────────────────────────────
    evangelie = result.get("exegese_evangelielezing")
    if evangelie:
        _render_exegese(evangelie)
        st.divider()

    # ── Reflectie ─────────────────────────────────────────────────────────────
    reflectie: dict = result.get("reflectie", {})
    if reflectie:
        st.subheader("💡 Reflectie")

        theologische_lijnen: list = reflectie.get("theologische_lijnen", [])
        if theologische_lijnen:
            st.markdown("**Theologische lijnen**")
            for lijn in theologische_lijnen:
                st.markdown(f"- {lijn}")

        homiletische_potentie = reflectie.get("homiletische_potentie", "")
        if homiletische_potentie:
            st.markdown("**Homiletische potentie**")
            st.success(homiletische_potentie)
