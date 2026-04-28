"""Renderer voor de Tavily-gedreven politieke oriëntatie-analyse.

Toont de verkiezingsblokken (TK, EP, PS, gemeenteraad), de wijk-/kern-context,
politieke cultuur, spanningsvelden en de homiletische vertaling. Bronnen en
de meta-sectie over bronkwaliteit worden bewust niet getoond aan de eindgebruiker;
die data blijft wel in het analyse-resultaat staan voor latere inspectie.
"""

from typing import Any

import streamlit as st

from src.utils.utils import clean_md


def _render_list(values: list) -> None:
    # Bullet-helper met clean_md; de caller is verantwoordelijk voor
    # leeg-checks zodat we geen lege bullet-blokken renderen.
    for item in values:
        st.markdown(f"- {clean_md(str(item))}")


def _as_dict(value: Any) -> dict:
    # Verkiezingsdatum kan als losse string of als object met `datum`-key
    # komen; normaliseer naar dict zodat de rest van de renderer één vorm
    # ziet.
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value:
        return {"datum": value}
    return {}


def politieke_orientatie(analysis: dict[str, Any]) -> None:
    """Render politieke oriëntatie-resultaat."""
    result: dict[str, Any] = analysis.get("result", {})

    place: str = st.session_state.get("church_place", "")
    if place:
        st.caption(f"**Plaats:** {place}")

    lokale_context: dict = result.get("lokale_context", {}) or {}
    verkiezingsdata: dict = result.get("verkiezingsdata", {}) or {}
    landelijk: dict = result.get("landelijk_stemgedrag", {}) or {}
    europees: dict = result.get("europees_stemgedrag", {}) or {}
    provinciaal: dict = result.get("provinciaal_stemgedrag", {}) or {}
    gemeentelijk: dict = result.get("gemeentelijk_stemgedrag", {}) or {}
    cultuur: dict = result.get("politieke_cultuur", {}) or {}
    spanningsvelden: list = result.get("spanningsvelden", []) or []
    relevantie: dict = result.get("relevantie_prediking", {}) or {}

    # Lokale context bovenaan — welk wijk/kern-profiel ligt onder deze
    # uitslagen? In grote steden is dit het verschil tussen een bruikbaar
    # en een misleidend beeld. Bronnen en bronnen-kwaliteit worden bewust
    # niet getoond: voor de prediker zijn ze ruis; ze blijven wel in het
    # analyse-resultaat aanwezig voor diagnose.
    _render_lokale_context(lokale_context)

    # ── Verkiezingsdata ─────────────────────────────────────────────────────
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

    # ── Landelijk stemgedrag ────────────────────────────────────────────────
    # Standaard ingeklapt zodat alle blokken consistent dichtgevouwen openen
    # en de prediker zelf bepaalt welk blok hij uitvouwt.
    with st.expander(
        f"Landelijk stemgedrag — {landelijk.get('verkiezingsdatum', '')}",
        expanded=False,
    ):
        top_partijen: list = landelijk.get("top_partijen", [])
        if top_partijen:
            sorted_partijen = sorted(
                top_partijen,
                key=lambda p: p.get("percentage_lokaal", 0),
                reverse=True,
            )
            cols_header = st.columns([3, 2, 2, 2])
            cols_header[0].caption("Partij")
            cols_header[1].caption("% Lokaal")
            cols_header[2].caption("% Landelijk")
            cols_header[3].caption("Verschil t.o.v. vorige TK")
            for p in sorted_partijen:
                c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                c1.markdown(f"**{p.get('partij', '')}**")
                c2.markdown(str(p.get("percentage_lokaal", "")))
                c3.markdown(str(p.get("percentage_landelijk", "")))
                c4.markdown(p.get("verschil_tov_2023", ""))

        if landelijk.get("opkomst"):
            st.markdown(f"**Opkomst:** {clean_md(landelijk['opkomst'])}")
        verschuivingen: list = landelijk.get("verschuivingen", [])
        if verschuivingen:
            st.markdown("**Verschuivingen:**")
            _render_list(verschuivingen)
        if landelijk.get("analyse"):
            st.markdown(f"**Analyse:** {clean_md(landelijk['analyse'])}")

    st.divider()

    # ── Europees / Provinciaal / Gemeentelijk ───────────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1:
        with st.expander(
            f"Europees — {europees.get('verkiezingsdatum', '')}",
            expanded=False,
        ):
            for p in sorted(
                europees.get("top_partijen", []),
                key=lambda x: x.get("percentage_lokaal", 0),
                reverse=True,
            ):
                st.markdown(
                    f"- **{p.get('partij', '')}** — {p.get('percentage_lokaal', '')}%"
                )
    with c2:
        with st.expander(
            f"Provinciaal — {provinciaal.get('verkiezingsdatum', '')}",
            expanded=False,
        ):
            dom: list = provinciaal.get("dominante_partijen", [])
            reg: list = provinciaal.get("regionale_partijen", [])
            if dom:
                st.markdown("*Dominant:*")
                _render_list(dom)
            if reg:
                st.markdown("*Regionaal:*")
                _render_list(reg)
    with c3:
        with st.expander(
            f"Gemeentelijk — {gemeentelijk.get('verkiezingsdatum', '')}",
            expanded=False,
        ):
            coalitie: list = gemeentelijk.get("coalitie", [])
            themas: list = gemeentelijk.get("belangrijke_themas", [])
            if coalitie:
                st.markdown("*Coalitie:*")
                _render_list(coalitie)
            if themas:
                st.markdown("*Lokale thema's:*")
                _render_list(themas)

    st.divider()

    # ── Politieke cultuur ───────────────────────────────────────────────────
    with st.expander("Politieke cultuur", expanded=False):
        if cultuur.get("progressief_conservatief"):
            st.markdown(
                f"**Progressief–conservatief:** {clean_md(cultuur['progressief_conservatief'])}"
            )
        if cultuur.get("vertrouwen_overheid"):
            st.markdown(
                f"**Vertrouwen overheid:** {clean_md(cultuur['vertrouwen_overheid'])}"
            )
        if cultuur.get("anti_establishment"):
            st.markdown(
                f"**Anti-establishment:** {clean_md(cultuur['anti_establishment'])}"
            )

    st.divider()

    # ── Spanningsvelden ─────────────────────────────────────────────────────
    if spanningsvelden:
        with st.expander(
            f"Spanningsvelden ({len(spanningsvelden)})", expanded=False
        ):
            for sv in spanningsvelden:
                with st.container(border=True):
                    st.markdown(
                        f"**{sv.get('onderwerp', '')}** — *{sv.get('type', '')}*"
                    )
                    if sv.get("standpunten"):
                        st.markdown(clean_md(sv["standpunten"]))
        st.divider()

    # ── Relevantie prediking ────────────────────────────────────────────────
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


def _render_lokale_context(lokale_context: dict) -> None:
    """Toon wijk-/kern-context bovenaan zodat het analyse-niveau duidelijk is.

    In grote steden (Den Haag, Rotterdam, Amsterdam, maar ook Katwijk) is
    het verschil tussen wijken vaak groter dan het verschil tussen plaatsen
    onderling. De prediker moet direct zien op welke schaal hij naar de
    uitslagen kijkt — gemeente-totalen kunnen anders misleidend zijn.
    """
    if not lokale_context:
        return

    niveau = lokale_context.get("analyse_niveau", "")
    wijk = lokale_context.get("wijk_of_kern", "")
    postcode = lokale_context.get("postcodegebied", "")
    profiel = lokale_context.get("wijkprofiel", "")
    waarom = lokale_context.get("waarom_deze_schaal", "")

    # Kopregel met badge-achtige labels — in één oogopslag zie je het niveau
    # en de locatie waarop de rest van het rapport gebaseerd is.
    labelparts: list[str] = []
    if niveau:
        labelparts.append(f"**Niveau:** {clean_md(niveau)}")
    if wijk:
        labelparts.append(f"**Wijk / kern:** {clean_md(wijk)}")
    if postcode:
        labelparts.append(f"**Postcode:** {clean_md(postcode)}")
    if labelparts:
        st.markdown(" · ".join(labelparts))

    if profiel:
        st.info(clean_md(profiel))
    if waarom:
        st.caption(f"*Waarom dit niveau:* {clean_md(waarom)}")

    st.divider()
