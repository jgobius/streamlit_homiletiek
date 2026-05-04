from typing import Any

import streamlit as st

from src.utils.utils import clean_md


def _render_list(values: list) -> None:
    for item in values:
        st.markdown(f"- {clean_md(str(item))}")


def _format_bevolkingsomvang(waarde: Any) -> str:
    """Zet een bevolkingsomvang om naar een string met punten als duizendtalscheiding.

    De agent levert `bevolkingsomvang` soms als int (bv. 43310), soms als
    reeds geformatteerde string (bv. "43.310" of "43,310"), en soms als
    vrije-tekst-omschrijving (bv. "Ongeveer 21.120 inwoners (totaal Leerdam,
    geëxtrapoleerd naar 2026)."). In het laatste geval mogen we niet zomaar
    alle cijfers concatten — dan wordt "21.120 ... 2026" tot "211.202.026"
    en verschijnt 211 miljoen op het scherm. We herformatteren daarom alleen
    wanneer de waarde *puur* numeriek is (alleen cijfers, eventueel met
    duizendtalscheiding via `.`, `,` of spatie). Anders tonen we de
    oorspronkelijke tekst onveranderd, zodat de duiding van de agent intact
    blijft.
    """
    if isinstance(waarde, (int, float)):
        return f"{int(waarde):,}".replace(",", ".")
    tekst = str(waarde).strip()
    # Strip duizendtalscheidingen en whitespace; wat overblijft moet puur cijfer zijn
    # om hem als getal te durven herformatteren.
    cijfers = tekst.replace(".", "").replace(",", "").replace(" ", "")
    if cijfers.isdigit() and cijfers:
        return f"{int(cijfers):,}".replace(",", ".")
    return tekst


def sociaal_maatschappelijk(analysis: dict[str, Any]) -> None:
    """Render sociaal-maatschappelijk analysis result."""
    result: dict[str, Any] = analysis.get("result", {})

    # Plaatsnaam staat al in de context-regel onder de tabbladen, dus
    # niet meer hier herhalen.

    demografisch: dict = result.get("demografisch", {})
    economisch: dict = result.get("economisch", {})
    sociale_structuur: dict = result.get("sociale_structuur", {})
    recente_gebeurtenissen: list = result.get("recente_gebeurtenissen", [])
    kerkelijke_context: dict = result.get("kerkelijke_context", {})
    bronnen: list = result.get("bronnen_gebruikt", [])

    # ── Demografisch ─────────────────────────────────────────────────────────
    with st.expander("Demografisch profiel", expanded=False):
        omvang = demografisch.get("bevolkingsomvang")
        dichtheid = demografisch.get("bevolkingsdichtheid", "")
        if omvang is not None:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Bevolkingsomvang:** {_format_bevolkingsomvang(omvang)}")
            with col2:
                if dichtheid:
                    st.markdown(f"**Dichtheid:** {clean_md(dichtheid)}")

        leeftijd: dict = demografisch.get("leeftijdsopbouw", {})
        if leeftijd:
            st.markdown("**Leeftijdsopbouw**")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"**Jongeren (0-18):** {leeftijd.get('jongeren_0_18', '-')}")
            with c2:
                st.markdown(f"**Werkenden (18-65):** {leeftijd.get('werkenden_18_65', '-')}")
            with c3:
                st.markdown(f"**Ouderen (65+):** {leeftijd.get('ouderen_65_plus', '-')}")
            if leeftijd.get("vergrijzingsgraad"):
                st.caption(f"Vergrijzing: {leeftijd['vergrijzingsgraad']}")
            if leeftijd.get("toelichting"):
                st.markdown(clean_md(leeftijd["toelichting"]))

        huishoudens: dict = demografisch.get("huishoudens", {})
        if huishoudens:
            st.markdown("**Huishoudens**")
            c1, c2 = st.columns(2)
            with c1:
                if huishoudens.get("eenpersoonshuishoudens"):
                    st.markdown(f"**Eenpersoonshuishoudens:** {huishoudens['eenpersoonshuishoudens']}")
            with c2:
                if huishoudens.get("gezinnen_met_kinderen"):
                    st.markdown(f"**Gezinnen met kinderen:** {huishoudens['gezinnen_met_kinderen']}")
            if huishoudens.get("samenstelling_toelichting"):
                st.markdown(clean_md(huishoudens["samenstelling_toelichting"]))

        opleiding: dict = demografisch.get("opleidingsniveaus", {})
        if opleiding:
            st.markdown("**Opleidingsniveaus**")
            c1, c2, c3 = st.columns(3)
            with c1:
                if opleiding.get("laag"):
                    st.markdown(f"**Laag:** {opleiding['laag']}")
            with c2:
                if opleiding.get("midden"):
                    st.markdown(f"**Midden:** {opleiding['midden']}")
            with c3:
                if opleiding.get("hoog"):
                    st.markdown(f"**Hoog:** {opleiding['hoog']}")
            if opleiding.get("vergelijking_landelijk"):
                st.caption(clean_md(opleiding["vergelijking_landelijk"]))

        herkomst: dict = demografisch.get("herkomst_diversiteit", {})
        if herkomst:
            st.markdown("**Herkomst en diversiteit**")
            c1, c2 = st.columns(2)
            with c1:
                if herkomst.get("nederlandse_achtergrond"):
                    st.markdown(f"**Nederlandse achtergrond:** {herkomst['nederlandse_achtergrond']}")
            with c2:
                migr = herkomst.get("migratieachtergrond")
                if isinstance(migr, dict):
                    if migr.get("totaal"):
                        st.markdown(f"**Migratieachtergrond:** {migr['totaal']}")
                elif migr:
                    st.markdown(f"**Migratieachtergrond:** {migr}")
            if herkomst.get("grootste_groepen"):
                st.markdown("Grootste groepen:")
                _render_list(herkomst["grootste_groepen"])
            if herkomst.get("toelichting"):
                st.markdown(clean_md(herkomst["toelichting"]))

    # ── Economisch ───────────────────────────────────────────────────────────
    with st.expander("Economisch profiel", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            if economisch.get("werkloosheidspercentage"):
                st.markdown(f"**Werkloosheid:** {economisch['werkloosheidspercentage']}")
        with c2:
            if economisch.get("gemiddeld_inkomen"):
                st.markdown(f"**Gemiddeld inkomen:** {economisch['gemiddeld_inkomen']}")
        with c3:
            if economisch.get("vergelijking_landelijk"):
                st.caption(clean_md(economisch["vergelijking_landelijk"]))

        if economisch.get("belangrijkste_sectoren"):
            st.markdown("**Belangrijkste sectoren:**")
            _render_list(economisch["belangrijkste_sectoren"])

        if economisch.get("grote_werkgevers"):
            st.markdown("**Grote werkgevers:**")
            _render_list(economisch["grote_werkgevers"])

        if economisch.get("economische_vooruitzichten"):
            st.markdown(f"**Vooruitzichten:** {clean_md(economisch['economische_vooruitzichten'])}")

        if economisch.get("recente_ontwikkelingen"):
            st.markdown("**Recente ontwikkelingen:**")
            _render_list(economisch["recente_ontwikkelingen"])

    # ── Sociale structuur ────────────────────────────────────────────────────
    with st.expander("Sociale structuur", expanded=False):
        if sociale_structuur.get("sociale_cohesie"):
            st.info(clean_md(sociale_structuur["sociale_cohesie"]))

        vereniging: dict = sociale_structuur.get("verenigingsleven", {})
        if vereniging:
            actief = vereniging.get("actief", False)
            st.markdown(f"**Verenigingsleven:** {'actief' if actief else 'beperkt'}")
            if vereniging.get("toelichting"):
                st.markdown(clean_md(vereniging["toelichting"]))
            if vereniging.get("belangrijke_verenigingen"):
                st.markdown("Belangrijke verenigingen:")
                _render_list(vereniging["belangrijke_verenigingen"])

        voorzieningen: dict = sociale_structuur.get("voorzieningen", {})
        if voorzieningen:
            st.markdown("**Voorzieningen**")
            if voorzieningen.get("scholen"):
                st.markdown("*Scholen:*")
                _render_list(voorzieningen["scholen"])
            if voorzieningen.get("zorg"):
                st.markdown("*Zorg:*")
                _render_list(voorzieningen["zorg"])
            if voorzieningen.get("winkels"):
                st.markdown(f"*Winkels:* {clean_md(voorzieningen['winkels'])}")
            if voorzieningen.get("krimp_of_groei"):
                st.markdown(f"*Krimp/groei:* {clean_md(voorzieningen['krimp_of_groei'])}")

        woning: dict = sociale_structuur.get("woningmarkt", {})
        if woning:
            st.markdown("**Woningmarkt**")
            c1, c2, c3 = st.columns(3)
            with c1:
                if woning.get("type_woningen"):
                    st.markdown(f"*Type:* {clean_md(woning['type_woningen'])}")
            with c2:
                if woning.get("prijsniveau"):
                    st.markdown(f"*Prijs:* {clean_md(woning['prijsniveau'])}")
            with c3:
                if woning.get("beschikbaarheid"):
                    st.markdown(f"*Beschikbaarheid:* {clean_md(woning['beschikbaarheid'])}")

    # ── Recente gebeurtenissen ───────────────────────────────────────────────
    if recente_gebeurtenissen:
        with st.expander(f"Recente gebeurtenissen ({len(recente_gebeurtenissen)})", expanded=False):
            for geb in recente_gebeurtenissen:
                with st.container(border=True):
                    c1, c2 = st.columns([1, 3])
                    with c1:
                        st.caption(geb.get("datum", ""))
                        st.markdown(f"*{geb.get('type', '')}*")
                    with c2:
                        st.markdown(f"**{geb.get('gebeurtenis', '')}**")
                        if geb.get("impact"):
                            st.markdown(clean_md(geb["impact"]))

    # ── Kerkelijke context ───────────────────────────────────────────────────
    with st.expander("Kerkelijke context", expanded=False):
        positie: dict = kerkelijke_context.get("positie_gemeente", {})
        if positie:
            st.subheader(positie.get("naam", "Gemeente"))
            c1, c2, c3 = st.columns(3)
            with c1:
                if positie.get("type"):
                    st.markdown(f"**Type:** {positie['type']}")
                if positie.get("geschatte_leden"):
                    st.markdown(f"**Leden (schatting):** {positie['geschatte_leden']}")
            with c2:
                if positie.get("karakter"):
                    st.markdown(f"**Karakter:** {clean_md(positie['karakter'])}")
                if positie.get("opgegeven_modaliteit"):
                    st.markdown(f"**Modaliteit:** {positie['opgegeven_modaliteit']}")
            with c3:
                if positie.get("afwijking_plaatscultuur"):
                    st.markdown(f"**Verhouding plaatscultuur:** {clean_md(positie['afwijking_plaatscultuur'])}")

        denominaties: list = kerkelijke_context.get("denominaties_aanwezig", [])
        if denominaties:
            st.markdown("**Andere denominaties in de plaats**")
            cols_header = st.columns([2, 2, 2])
            cols_header[0].caption("Naam")
            cols_header[1].caption("Type")
            cols_header[2].caption("Omvang")
            for d in denominaties:
                c1, c2, c3 = st.columns([2, 2, 2])
                # `dict.get(key, default)` valt alleen terug op de default als
                # de sleutel ontbreekt; een aanwezige None-waarde wordt door
                # st.markdown letterlijk als "None" gerenderd. Coerce daarom
                # alle drie de velden naar een nette string (em-dash bij leeg).
                c1.markdown(d.get("naam") or "—")
                c2.markdown(d.get("type") or "—")
                c3.markdown(d.get("geschatte_omvang") or "—")

        ontwikkelingen: list = kerkelijke_context.get("recente_kerkelijke_ontwikkelingen", [])
        if ontwikkelingen:
            st.markdown("**Recente kerkelijke ontwikkelingen:**")
            _render_list(ontwikkelingen)

        samenwerking = kerkelijke_context.get("oecumenische_samenwerking")
        if samenwerking:
            st.markdown(f"**Oecumenische samenwerking:** {clean_md(samenwerking)}")

    # ── Bronnen ──────────────────────────────────────────────────────────────
    if bronnen:
        st.caption("**Bronnen gebruikt:** " + " · ".join(bronnen))
