from typing import Any

import streamlit as st

from src.utils.utils import clean_md


def _render_list(values: list) -> None:
    for item in values:
        st.markdown(f"- {clean_md(str(item))}")


def interpretatieve_synthese(analysis: dict[str, Any]) -> None:
    """Render interpretatieve synthese analysis result."""
    result: dict[str, Any] = analysis.get("result", {})

    congruentie: dict = result.get("congruentie_analyse", {})
    verbindingspunten: dict = result.get("verbindingspunten", {})
    confrontatie: dict = result.get("confrontatiepunten", {})
    hoorders: dict = result.get("hoordersanalyse", {})
    specifiek: dict = result.get("specifiek_voor_datum", {})
    aanbevelingen: dict = result.get("homiletische_aanbevelingen", {})

    with st.expander("Congruentie-analyse: norm vs. praktijk", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            if congruentie.get("officiele_geloofsopvatting"):
                st.markdown("**Officiele geloofsopvatting**")
                st.markdown(clean_md(congruentie["officiele_geloofsopvatting"]))
        with c2:
            if congruentie.get("geleefde_praktijk"):
                st.markdown("**Geleefde praktijk**")
                st.markdown(clean_md(congruentie["geleefde_praktijk"]))
        spanningen: list = congruentie.get("spanningen_norm_praktijk", [])
        if spanningen:
            st.markdown("**Spanningen norm–praktijk:**")
            _render_list(spanningen)
        aannames: list = congruentie.get("onbewuste_aannames", [])
        if aannames:
            st.markdown("**Onbewuste aannames:**")
            _render_list(aannames)

    st.divider()

    with st.expander("Verbindingspunten", expanded=False):
        aansluiting: list = verbindingspunten.get("aansluiting_geleefde_ervaring", [])
        if aansluiting:
            st.markdown("**Aansluiting geleefde ervaring:**")
            _render_list(aansluiting)
        resonerende: list = verbindingspunten.get("resonerende_beelden", [])
        if resonerende:
            st.markdown("**Resonerende beelden**")
            for beeld in resonerende:
                with st.container(border=True):
                    c1, c2 = st.columns([2, 2])
                    with c1:
                        st.markdown(f"**{beeld.get('beeld', '')}**")
                        if beeld.get("waarom_resoneert"):
                            st.markdown(clean_md(beeld["waarom_resoneert"]))
                    with c2:
                        if beeld.get("bijbelse_parallel"):
                            st.caption(f"Bijbelse parallel: {clean_md(beeld['bijbelse_parallel'])}")

    st.divider()

    with st.expander("Confrontatiepunten", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            bijbel_conf: list = confrontatie.get("bijbeltekst_confronteert", [])
            if bijbel_conf:
                st.markdown("**Bijbeltekst confronteert:**")
                _render_list(bijbel_conf)
        with c2:
            profetisch: list = confrontatie.get("profetische_kritiek", [])
            if profetisch:
                st.markdown("**Profetische kritiek:**")
                _render_list(profetisch)
        with c3:
            blind: list = confrontatie.get("blinde_vlekken", [])
            if blind:
                st.markdown("**Blinde vlekken:**")
                _render_list(blind)

    st.divider()

    with st.expander("Hoordersanalyse", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            los_te_laten: list = hoorders.get("los_te_laten_aannames", [])
            if los_te_laten:
                st.markdown("**Los te laten aannames:**")
                _render_list(los_te_laten)
        with c2:
            diversiteit: list = hoorders.get("diversiteit_binnen_gemeente", [])
            if diversiteit:
                st.markdown("**Diversiteit gemeente:**")
                _render_list(diversiteit)
        with c3:
            onzichtbaar: list = hoorders.get("onzichtbare_hoorders", [])
            if onzichtbaar:
                st.markdown("**Onzichtbare hoorders:**")
                _render_list(onzichtbaar)

    st.divider()

    st.subheader("Homiletische aanbevelingen")
    toon: dict = aanbevelingen.get("toon", {})
    if toon:
        c1, c2 = st.columns(2)
        with c1:
            if toon.get("aanbevolen"):
                st.success(f"**Toon aanbevolen:** {clean_md(toon['aanbevolen'])}")
        with c2:
            if toon.get("te_vermijden"):
                st.warning(f"**Toon te vermijden:** {clean_md(toon['te_vermijden'])}")

    taal: dict = aanbevelingen.get("taal", {})
    beelden: dict = aanbevelingen.get("beelden", {})
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        toegankelijk: list = taal.get("toegankelijk", [])
        if toegankelijk:
            st.markdown("**Toegankelijke taal:**")
            _render_list(toegankelijk)
    with c2:
        uit_te_leggen: list = taal.get("uit_te_leggen", [])
        if uit_te_leggen:
            st.markdown("**Uit te leggen:**")
            _render_list(uit_te_leggen)
    with c3:
        werkend: list = beelden.get("werkend", [])
        if werkend:
            st.markdown("**Beelden die werken:**")
            _render_list(werkend)
    with c4:
        niet_werkend: list = beelden.get("niet_werkend", [])
        if niet_werkend:
            st.markdown("**Beelden die niet werken:**")
            _render_list(niet_werkend)
