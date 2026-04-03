from typing import Any
import streamlit as st
from src.utils.utils import clean_md

def _render_list(values: list) -> None:
    for item in values:
        st.markdown(f"- {clean_md(str(item))}")

def _as_dict(value: Any) -> dict:
    if isinstance(value, dict): return value
    if isinstance(value, str) and value: return {"datum": value}
    return {}

def politieke_orientatie(analysis: dict[str, Any]) -> None:
    result: dict[str, Any] = analysis.get("result", {})
    place: str = st.session_state.get("church_place", "")
    if place:
        st.caption(f"**Plaats:** {place}")

    verkiezingsdata: dict = result.get("verkiezingsdata", {})
    landelijk: dict = result.get("landelijk_stemgedrag", {})
    europees: dict = result.get("europees_stemgedrag", {})
    provinciaal: dict = result.get("provinciaal_stemgedrag", {})
    gemeentelijk: dict = result.get("gemeentelijk_stemgedrag", {})
    cultuur: dict = result.get("politieke_cultuur", {})
    spanningsvelden: list = result.get("spanningsvelden", [])
    relevantie: dict = result.get("relevantie_prediking", {})

    with st.expander("Verkiezingsdata", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        tk = _as_dict(verkiezingsdata.get("tweede_kamer", {}))
        ep = _as_dict(verkiezingsdata.get("europees_parlement", {}))
        ps = _as_dict(verkiezingsdata.get("provinciale_staten", {}))
        gr = _as_dict(verkiezingsdata.get("gemeenteraad", {}))
        with c1:
            st.markdown("**Tweede Kamer**")
            if tk.get("datum"): st.caption(tk["datum"])
        with c2:
            st.markdown("**Europees Parlement**")
            if ep.get("datum"): st.caption(ep["datum"])
        with c3:
            st.markdown("**Provinciale Staten**")
            if ps.get("datum"): st.caption(ps["datum"])
        with c4:
            st.markdown("**Gemeenteraad**")
            if gr.get("datum"): st.caption(gr["datum"])

    st.divider()

    with st.expander(f"Landelijk stemgedrag — {landelijk.get('verkiezingsdatum','')}", expanded=True):
        top_partijen: list = landelijk.get("top_partijen", [])
        if top_partijen:
            sorted_partijen = sorted(top_partijen, key=lambda p: p.get("percentage_lokaal", 0), reverse=True)
            cols_header = st.columns([3, 2, 2, 2])
            cols_header[0].caption("Partij"); cols_header[1].caption("% Lokaal"); cols_header[2].caption("% Landelijk"); cols_header[3].caption("Verschil t.o.v. 2023")
            for p in sorted_partijen:
                c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                c1.markdown(f"**{p.get('partij','')}**"); c2.markdown(str(p.get("percentage_lokaal",""))); c3.markdown(str(p.get("percentage_landelijk",""))); c4.markdown(p.get("verschil_tov_2023",""))
        if landelijk.get("opkomst"): st.metric("Opkomst", landelijk["opkomst"])

    st.divider()

    c1, c2, c3 = st.columns(3)
    with c1:
        with st.expander(f"Europees — {europees.get('verkiezingsdatum','')}", expanded=False):
            for p in sorted(europees.get("top_partijen",[]), key=lambda x: x.get("percentage_lokaal",0), reverse=True):
                st.markdown(f"- **{p.get('partij','')}** — {p.get('percentage_lokaal','')}%")
    with c2:
        with st.expander(f"Provinciaal — {provinciaal.get('verkiezingsdatum','')}", expanded=False):
            if provinciaal.get("dominante_partijen"): _render_list(provinciaal["dominante_partijen"])
    with c3:
        with st.expander(f"Gemeentelijk — {gemeentelijk.get('verkiezingsdatum','')}", expanded=False):
            if gemeentelijk.get("coalitie"): _render_list(gemeentelijk["coalitie"])

    st.divider()

    with st.expander("Politieke cultuur", expanded=False):
        if cultuur.get("progressief_conservatief"): st.markdown(f"**Progressief–conservatief:** {clean_md(cultuur['progressief_conservatief'])}")
        if cultuur.get("vertrouwen_overheid"): st.markdown(f"**Vertrouwen overheid:** {clean_md(cultuur['vertrouwen_overheid'])}")

    st.divider()

    st.subheader("Relevantie voor prediking")
    c1, c2 = st.columns(2)
    with c1:
        if relevantie.get("gevoeligheden"):
            st.markdown("**Gevoeligheden:**")
            _render_list(relevantie["gevoeligheden"])
    with c2:
        if relevantie.get("aansluiting_mogelijkheden"):
            st.markdown("**Aansluitingsmogelijkheden:**")
            _render_list(relevantie["aansluiting_mogelijkheden"])
