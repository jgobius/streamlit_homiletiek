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


def _publieke_datum(datum: Any) -> str:
    # Sanitiseer een verkiezingsdatum voor weergave aan de eindgebruiker:
    # interne tooling-verwijzingen (Tavily, "geen recente bron") horen niet
    # op het scherm; bij een onbekende datum tonen we een korte neutrale
    # tekst zodat de kop ("Europees — datum onbekend") leesbaar blijft.
    if not datum:
        return ""
    s = str(datum).strip()
    laag = s.lower()
    if "onbekend" in laag or "tavily" in laag or "geen bron" in laag:
        return "datum onbekend"
    return s


def _titel_met_datum(label: str, datum: Any) -> str:
    # Gemeenschappelijke titel-helper voor de blok-expanders. Zonder publieke
    # datum tonen we alleen het label, anders met streepje. Dit voorkomt
    # rare lege staarten als "Europees — ".
    schoon = _publieke_datum(datum)
    return f"{label} — {schoon}" if schoon else label


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
        # Datums via _publieke_datum: interne tooling-meldingen ("Tavily",
        # "geen bron") mogen nooit naar de gebruiker lekken.
        tk_datum = _publieke_datum(tk.get("datum"))
        ep_datum = _publieke_datum(ep.get("datum"))
        ps_datum = _publieke_datum(ps.get("datum"))
        gr_datum = _publieke_datum(gr.get("datum"))
        with c1:
            st.markdown("**Tweede Kamer**")
            if tk_datum:
                st.caption(tk_datum)
            if tk.get("opmerking"):
                st.caption(clean_md(tk["opmerking"]))
        with c2:
            st.markdown("**Europees Parlement**")
            if ep_datum:
                st.caption(ep_datum)
        with c3:
            st.markdown("**Provinciale Staten**")
            if ps_datum:
                st.caption(ps_datum)
        with c4:
            st.markdown("**Gemeenteraad**")
            if gr_datum:
                st.caption(gr_datum)

    # ── Landelijk stemgedrag ────────────────────────────────────────────────
    # Standaard ingeklapt zodat alle blokken consistent dichtgevouwen openen
    # en de prediker zelf bepaalt welk blok hij uitvouwt. Als het blok geen
    # bruikbare inhoud heeft (geen partijen, geen analyse, geen verschuivingen)
    # tonen we het hele expander niet — anders krijgt de gebruiker een leeg
    # blok met "datum onbekend" als kop.
    landelijk_top: list = landelijk.get("top_partijen", []) or []
    landelijk_versch: list = landelijk.get("verschuivingen", []) or []
    if (
        landelijk_top
        or landelijk.get("opkomst")
        or landelijk_versch
        or landelijk.get("analyse")
    ):
        with st.expander(
            _titel_met_datum(
                "Landelijk stemgedrag", landelijk.get("verkiezingsdatum")
            ),
            expanded=False,
        ):
            if landelijk_top:
                sorted_partijen = sorted(
                    landelijk_top,
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
            if landelijk_versch:
                st.markdown("**Verschuivingen:**")
                _render_list(landelijk_versch)
            if landelijk.get("analyse"):
                st.markdown(f"**Analyse:** {clean_md(landelijk['analyse'])}")

    # ── Europees / Provinciaal / Gemeentelijk ───────────────────────────────
    # Bouw eerst per blok de inhoud-renderer + content-check. We renderen
    # alleen kolommen voor blokken die daadwerkelijk iets te tonen hebben.
    europees_top: list = europees.get("top_partijen", []) or []
    prov_dom: list = provinciaal.get("dominante_partijen", []) or []
    prov_reg: list = provinciaal.get("regionale_partijen", []) or []
    gem_coal: list = gemeentelijk.get("coalitie", []) or []
    gem_themas: list = gemeentelijk.get("belangrijke_themas", []) or []

    blokken: list[tuple[str, Any, Any]] = []
    if europees_top:
        blokken.append(
            (
                _titel_met_datum("Europees", europees.get("verkiezingsdatum")),
                europees_top,
                "europees",
            )
        )
    if prov_dom or prov_reg:
        blokken.append(
            (
                _titel_met_datum(
                    "Provinciaal", provinciaal.get("verkiezingsdatum")
                ),
                (prov_dom, prov_reg),
                "provinciaal",
            )
        )
    if gem_coal or gem_themas:
        blokken.append(
            (
                _titel_met_datum(
                    "Gemeentelijk", gemeentelijk.get("verkiezingsdatum")
                ),
                (gem_coal, gem_themas),
                "gemeentelijk",
            )
        )

    if blokken:
        kolommen = st.columns(len(blokken))
        for kol, (titel, payload, soort) in zip(kolommen, blokken):
            with kol:
                with st.expander(titel, expanded=False):
                    if soort == "europees":
                        for p in sorted(
                            payload,
                            key=lambda x: x.get("percentage_lokaal", 0),
                            reverse=True,
                        ):
                            st.markdown(
                                f"- **{p.get('partij', '')}** — "
                                f"{p.get('percentage_lokaal', '')}%"
                            )
                    elif soort == "provinciaal":
                        dom, reg = payload
                        if dom:
                            st.markdown("*Dominant:*")
                            _render_list(dom)
                        if reg:
                            st.markdown("*Regionaal:*")
                            _render_list(reg)
                    elif soort == "gemeentelijk":
                        coalitie, themas = payload
                        if coalitie:
                            st.markdown("*Coalitie:*")
                            _render_list(coalitie)
                        if themas:
                            st.markdown("*Lokale thema's:*")
                            _render_list(themas)

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
