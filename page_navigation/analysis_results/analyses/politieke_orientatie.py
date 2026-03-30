from typing import Any

import streamlit as st

from src.utils.utils import clean_md


def _render_list(values: list) -> None:
    for item in values:
        st.markdown(f"- {clean_md(str(item))}")


def _as_dict(value: Any) -> dict:
    """Normalise a field that may be a plain string date or a proper dict."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value:
        return {"datum": value}
    return {}


def politieke_orientatie(analysis: dict[str, Any]) -> None:
    """Render politieke orientatie analysis result."""
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

    # ── Verkiezingsdata ───────────────────────────────────────────────────────
    with st.expander("Verkiezingsdata", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        tk = _as_dict(verkiezingsdata.get("tweede_kamer", {}))
        ep = _as_dict(verkiezingsdata.get("europees_parlement", {}))
        ps = _as_dict(verkiezingsdata.get("provinciale_staten", {}))
        gr = _as_dict(verkiezingsdata.get("gemeenteraad", {}))
        with c1:
            st.markdown("**Tweede Kamer**")
            if tk.get("datum"):
                st.caption(tk["datum"])
            if tk.get("opmerking"):
                st.caption(clean_md(tk["opmerking"]))
        with c2:
            st.markdown("**Europees Parlement**")
            if ep.get("datum"):
                st.caption(ep["datum"])
        with c3:
            st.markdown("**Provinciale Staten**")
            if ps.get("datum"):
                st.caption(ps["datum"])
        with c4:
            st.markdown("**Gemeenteraad**")
            if gr.get("datum"):
                st.caption(gr["datum"])

    st.divider()

    # ── Landelijk stemgedrag ──────────────────────────────────────────────────
    with st.expander(f"Landelijk stemgedrag — {landelijk.get('verkiezingsdatum', '')}", expanded=True):
        top_partijen: list = landelijk.get("top_partijen", [])
        if top_partijen:
            sorted_partijen = sorted(top_partijen, key=lambda p: p.get("percentage_lokaal", 0), reverse=True)
            cols_header = st.columns([3, 2, 2, 2])
            cols_header[0].caption("Partij")
            cols_header[1].caption("% Lokaal")
            cols_header[2].caption("% Landelijk")
            cols_header[3].caption("Verschil t.o.v. 2023")
            for p in sorted_partijen:
                c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                c1.markdown(f"**{p.get('partij', '')}**")
                c2.markdown(str(p.get("percentage_lokaal", "")))
                c3.markdown(str(p.get("percentage_landelijk", "")))
                verschil = p.get("verschil_tov_2023", "")
                c4.markdown(verschil)

        if landelijk.get("opkomst"):
            st.metric("Opkomst", landelijk["opkomst"])
        verschuivingen: list = landelijk.get("verschuivingen", [])
        if verschuivingen:
            st.markdown("**Verschuivingen:**")
            _render_list(verschuivingen)
        if landelijk.get("analyse"):
            st.markdown(f"**Analyse:** {clean_md(landelijk['analyse'])}")

    st.divider()

    # ── Europees / Provinciaal / Gemeentelijk ─────────────────────────────────
    c1, c2, c3 = st.columns(3)

    with c1:
        with st.expander(f"Europees — {europees.get('verkiezingsdatum', '')}", expanded=False):
            ep_partijen: list = europees.get("top_partijen", [])
            if ep_partijen:
                for p in sorted(ep_partijen, key=lambda x: x.get("percentage_lokaal", 0), reverse=True):
                    st.markdown(f"- **{p.get('partij', '')}** — {p.get('percentage_lokaal', '')}%")

    with c2:
        with st.expander(f"Provinciaal — {provinciaal.get('verkiezingsdatum', '')}", expanded=False):
            dom: list = provinciaal.get("dominante_partijen", [])
            reg: list = provinciaal.get("regionale_partijen", [])
            if dom:
                st.markdown("*Dominant:*")
                _render_list(dom)
            if reg:
                st.markdown("*Regionaal:*")
                _render_list(reg)

    with c3:
        with st.expander(f"Gemeentelijk — {gemeentelijk.get('verkiezingsdatum', '')}", expanded=False):
            coalitie: list = gemeentelijk.get("coalitie", [])
            themas: list = gemeentelijk.get("belangrijke_themas", [])
            if coalitie:
                st.markdown("*Coalitie:*")
                _render_list(coalitie)
            if themas:
                st.markdown("*Themas:*")
                _render_list(themas)

    st.divider()

    # ── Politieke cultuur ─────────────────────────────────────────────────────
    with st.expander("Politieke cultuur", expanded=False):
        if cultuur.get("progressief_conservatief"):
            st.markdown(f"**Progressief–conservatief:** {clean_md(cultuur['progressief_conservatief'])}")
        if cultuur.get("vertrouwen_overheid"):
            st.markdown(f"**Vertrouwen overheid:** {clean_md(cultuur['vertrouwen_overheid'])}")
        if cultuur.get("anti_establishment"):
            st.markdown(f"**Anti-establishment:** {clean_md(cultuur['anti_establishment'])}")

    st.divider()

    # ── Spanningsvelden ───────────────────────────────────────────────────────
    if spanningsvelden:
        with st.expander(f"Spanningsvelden ({len(spanningsvelden)})", expanded=False):
            for sv in spanningsvelden:
                with st.container(border=True):
                    st.markdown(f"**{sv.get('onderwerp', '')}**  — *{sv.get('type', '')}*")
                    if sv.get("standpunten"):
                        st.markdown(clean_md(sv["standpunten"]))

    st.divider()

    # ── Relevantie prediking ───────────────────────────────────────────────────
    st.subheader("Relevantie voor prediking")
    c1, c2 = st.columns(2)
    with c1:
        gevoeligheden: list = relevantie.get("gevoeligheden", [])
        if gevoeligheden:
            st.markdown("**Gevoeligheden:**")
            _render_list(gevoeligheden)
    with c2:
        aansluitingen: list = relevantie.get("aansluiting_mogelijkheden", [])
        if aansluitingen:
            st.markdown("**Aansluitingsmogelijkheden:**")
            _render_list(aansluitingen)
