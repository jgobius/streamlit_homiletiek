"""Renderer voor de Tavily-gedreven sociaal-maatschappelijke contextanalyse.

Deze renderer toont een feitelijk profiel van de leefomgeving van de hoorders
(demografie, economie, sociale structuur, lokale gebeurtenissen, kerkelijke
kaart) en voegt — net als bij `gemeente_spiritualiteit` — twee transparantie-
secties toe: bovenaan de wijk-context + bronnen-kwaliteit (zodat de prediker
meteen weet op welke schaal de analyse is uitgevoerd en hoe betrouwbaar het
profiel is) en onderaan een klikbare bronnen-expander met citaten en URL's.

Reden voor een eigen module en niet hergebruik van een generieke renderer:
het schema bevat zowel de oude inhoudelijke secties (demografisch, economisch,
sociale_structuur, recente_gebeurtenissen, kerkelijke_context) als nieuwe
Tavily-secties (wijk_context, bronnen, bronnen_kwaliteit). Een generieke
renderer zou de Tavily-secties moeten kennen en dat zou doorlekken naar
analyses die geen Tavily gebruiken.
"""

from typing import Any

import streamlit as st

from src.utils.utils import clean_md


# Top-level secties uit het schema → leesbare kopjes. Gebruikt om dotpaths
# in `bronnen_kwaliteit.onderbouwing_ontbreekt` (bv. "demografisch.opleidings
# niveaus.hoog") om te zetten naar iets dat de prediker begrijpt. De rest van
# het pad wordt generiek geformatteerd via `_leesbaar_pad` zodat we geen
# mapping hoeven te onderhouden voor élk blad-veld in het schema.
_SECTIE_LABELS: dict[str, str] = {
    "wijk_context": "Wijk-context",
    "demografisch": "Demografisch",
    "economisch": "Economisch",
    "sociale_structuur": "Sociale structuur",
    "recente_gebeurtenissen": "Recente gebeurtenissen",
    "kerkelijke_context": "Kerkelijke context",
    "bronnen": "Bronnen",
    "bronnen_kwaliteit": "Bronnen-kwaliteit",
}


def _leesbaar_pad(dotpad: str) -> str:
    """Zet een schema-dotpad om naar een leesbaar label.

    Voorbeeld: "demografisch.opleidingsniveaus.hoog"
    → "Demografisch → Opleidingsniveaus → Hoog".

    We gebruiken " → " als scheider i.p.v. een punt, omdat dat visueel
    duidelijker de hiërarchie weergeeft. Onderstrepen worden vervangen
    door spaties zodat de uiteindelijke tekst natuurlijk leesbaar is.
    De eerste segment krijgt (indien aanwezig) een rijkere label uit
    `_SECTIE_LABELS`; diepere segmenten worden generiek geformatteerd.
    """
    if not dotpad:
        return ""
    segments = dotpad.split(".")
    delen: list[str] = []
    for idx, seg in enumerate(segments):
        if idx == 0 and seg in _SECTIE_LABELS:
            delen.append(_SECTIE_LABELS[seg])
        else:
            delen.append(seg.replace("_", " ").capitalize())
    return " → ".join(delen)


def _render_list(values: list) -> None:
    # Helper voor bullet-lijsten met clean_md-afhandeling. Leeg-checks
    # gebeuren door de caller zodat we hier niet per ongeluk een lege
    # lijst met "geen items" kopjes renderen.
    for item in values:
        st.markdown(f"- {clean_md(str(item))}")


def sociaal_maatschappelijk(analysis: dict[str, Any]) -> None:
    """Render sociaal-maatschappelijk analysis result.

    Deze functie wordt aangeroepen door `verdieping.py:_RENDERERS` op basis
    van de AnalysisType.name. De analyse is optioneel (`depends_on: []`),
    dus alle velden kunnen in principe ontbreken — we renderen alleen wat
    daadwerkelijk aanwezig is.
    """
    result: dict[str, Any] = analysis.get("result", {})

    place: str = st.session_state.get("church_place", "")
    if place:
        st.caption(f"**Plaats:** {place}")

    wijk_context: dict = result.get("wijk_context", {}) or {}
    demografisch: dict = result.get("demografisch", {})
    economisch: dict = result.get("economisch", {})
    sociale_structuur: dict = result.get("sociale_structuur", {})
    recente_gebeurtenissen: list = result.get("recente_gebeurtenissen", [])
    kerkelijke_context: dict = result.get("kerkelijke_context", {})
    bronnen: list = result.get("bronnen", []) or []
    bronnen_kwaliteit: dict = result.get("bronnen_kwaliteit", {}) or {}

    # ── Wijk-context + bronnen-kwaliteit bovenaan: transparantie eerst. ─────
    # De prediker moet eerst zien op welke schaal de analyse is gedaan en
    # hoe betrouwbaar het profiel is, vóórdat hij de inhoud leest. Daarom
    # staan deze meta-secties bovenaan, niet als voetnoot onderaan.
    _render_wijk_context(wijk_context)
    _render_bronnen_kwaliteit(bronnen_kwaliteit, aantal_bronnen=len(bronnen))

    # ── Demografisch ─────────────────────────────────────────────────────────
    with st.expander("Demografisch profiel", expanded=True):
        omvang = demografisch.get("bevolkingsomvang")
        dichtheid = demografisch.get("bevolkingsdichtheid", "")
        if omvang is not None:
            col1, col2 = st.columns(2)
            with col1:
                # Omvang kan zowel int als string zijn ("52.341" met punt).
                # Probeer numeriek te formatteren; fallback naar plain string
                # als de bron al opmaak meeleverde of het type een string is.
                try:
                    omvang_num = int(str(omvang).replace(".", "").replace(",", ""))
                    st.metric("Bevolkingsomvang", f"{omvang_num:,}".replace(",", "."))
                except (ValueError, TypeError):
                    st.metric("Bevolkingsomvang", str(omvang))
            with col2:
                if dichtheid:
                    st.markdown(f"**Dichtheid:** {clean_md(dichtheid)}")

        leeftijd: dict = demografisch.get("leeftijdsopbouw", {})
        if leeftijd:
            st.markdown("**Leeftijdsopbouw**")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Jongeren (0-18)", leeftijd.get("jongeren_0_18", "-"))
            with c2:
                st.metric("Werkenden (18-65)", leeftijd.get("werkenden_18_65", "-"))
            with c3:
                st.metric("Ouderen (65+)", leeftijd.get("ouderen_65_plus", "-"))
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
                    st.metric("Eenpersoonshuishoudens", huishoudens["eenpersoonshuishoudens"])
            with c2:
                if huishoudens.get("gezinnen_met_kinderen"):
                    st.metric("Gezinnen met kinderen", huishoudens["gezinnen_met_kinderen"])
            if huishoudens.get("samenstelling_toelichting"):
                st.markdown(clean_md(huishoudens["samenstelling_toelichting"]))

        opleiding: dict = demografisch.get("opleidingsniveaus", {})
        if opleiding:
            st.markdown("**Opleidingsniveaus**")
            c1, c2, c3 = st.columns(3)
            with c1:
                if opleiding.get("laag"):
                    st.metric("Laag", opleiding["laag"])
            with c2:
                if opleiding.get("midden"):
                    st.metric("Midden", opleiding["midden"])
            with c3:
                if opleiding.get("hoog"):
                    st.metric("Hoog", opleiding["hoog"])
            if opleiding.get("vergelijking_landelijk"):
                st.caption(clean_md(opleiding["vergelijking_landelijk"]))

        herkomst: dict = demografisch.get("herkomst_diversiteit", {})
        if herkomst:
            st.markdown("**Herkomst en diversiteit**")
            c1, c2 = st.columns(2)
            with c1:
                if herkomst.get("nederlandse_achtergrond"):
                    st.metric("Nederlandse achtergrond", herkomst["nederlandse_achtergrond"])
            with c2:
                migr = herkomst.get("migratieachtergrond")
                if isinstance(migr, dict):
                    if migr.get("totaal"):
                        st.metric("Migratieachtergrond", migr["totaal"])
                elif migr:
                    st.metric("Migratieachtergrond", migr)
            if herkomst.get("grootste_groepen"):
                st.markdown("Grootste groepen:")
                _render_list(herkomst["grootste_groepen"])
            if herkomst.get("toelichting"):
                st.markdown(clean_md(herkomst["toelichting"]))

    st.divider()

    # ── Economisch ───────────────────────────────────────────────────────────
    with st.expander("Economisch profiel", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            if economisch.get("werkloosheidspercentage"):
                st.metric("Werkloosheid", economisch["werkloosheidspercentage"])
        with c2:
            if economisch.get("gemiddeld_inkomen"):
                st.metric("Gemiddeld inkomen", economisch["gemiddeld_inkomen"])
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

    st.divider()

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

    st.divider()

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

    st.divider()

    # ── Kerkelijke context ───────────────────────────────────────────────────
    with st.expander("Kerkelijke context", expanded=True):
        positie: dict = kerkelijke_context.get("positie_gemeente", {})
        if positie:
            st.subheader(positie.get("naam", "Gemeente"))
            c1, c2, c3 = st.columns(3)
            with c1:
                if positie.get("type"):
                    st.markdown(f"**Type:** {positie['type']}")
                if positie.get("geschatte_leden"):
                    st.metric("Leden (schatting)", positie["geschatte_leden"])
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
                c1.markdown(d.get("naam", ""))
                c2.markdown(d.get("type", ""))
                c3.markdown(d.get("geschatte_omvang", "") or "")

        ontwikkelingen: list = kerkelijke_context.get("recente_kerkelijke_ontwikkelingen", [])
        if ontwikkelingen:
            st.markdown("**Recente kerkelijke ontwikkelingen:**")
            _render_list(ontwikkelingen)

        samenwerking = kerkelijke_context.get("oecumenische_samenwerking")
        if samenwerking:
            st.markdown(f"**Oecumenische samenwerking:** {clean_md(samenwerking)}")

    st.divider()

    # ── Bronnen — klikbaar, per claim. ───────────────────────────────────────
    _render_bronnen(bronnen)


def _render_wijk_context(wijk_context: dict) -> None:
    """Toon op welke schaal (wijk vs. plaats) de analyse is uitgevoerd.

    Belangrijk voor gemeentes in grote steden: een Den Haag-brede analyse is
    vaak nutteloos voor een gemeente in Bezuidenhout omdat de wijken qua
    demografie en opleidingsniveau dramatisch verschillen. Door wijk-context
    bovenaan te tonen ziet de prediker meteen of het profiel werkelijk de
    eigen wijk beschrijft of slechts een stad-breed gemiddelde.
    """
    if not wijk_context:
        return

    geidentificeerd: bool = bool(wijk_context.get("wijk_geidentificeerd"))
    wijk_naam: str = wijk_context.get("wijk_naam") or ""
    niveau: str = wijk_context.get("analyse_niveau") or ""
    toelichting: str = wijk_context.get("toelichting") or ""

    if geidentificeerd and wijk_naam:
        # Sterke positieve signaalbox als wijk-data daadwerkelijk is gebruikt.
        st.success(f"**Wijk-niveau analyse:** {wijk_naam} (niveau: {niveau})")
    elif niveau == "plaats":
        # Neutrale info — bij dorpen/kleine plaatsen is dit het gewenste niveau.
        st.caption(f"Analyse-niveau: plaats-breed")
    else:
        # Gemengd of onduidelijk — waarschuwing zodat de prediker de scope kent.
        st.info(f"Analyse-niveau: {niveau or 'onbekend'}")
    if toelichting:
        st.caption(clean_md(toelichting))


def _render_bronnen_kwaliteit(bronnen_kwaliteit: dict, *, aantal_bronnen: int) -> None:
    """Toon een compacte meta-indicatie van bronbetrouwbaarheid bovenaan.

    Argument `aantal_bronnen` komt uit de lengte van `result["bronnen"]`;
    we vertrouwen niet blind op het `aantal_bronnen`-veld uit het schema
    want een LLM kan dat veld vergeten bijwerken (daarom tellen we zelf).
    """
    if not bronnen_kwaliteit:
        return

    wijk_data: bool = bool(bronnen_kwaliteit.get("wijk_data_gebruikt"))
    kerk_verif: str = bronnen_kwaliteit.get("kerkelijke_verificatie_geslaagd", "") or ""
    # Iconen voor snelle visuele beoordeling — de prediker scant deze regel
    # in seconden en weet dan waar de zwakke plekken zitten.
    wijk_label = "✓ wijk-data gebruikt" if wijk_data else "✗ alleen plaats-data"
    c1, c2, c3 = st.columns([1, 3, 2])
    with c1:
        st.metric("Bronnen", aantal_bronnen)
    with c2:
        st.markdown("**Kerkelijke verificatie**")
        st.markdown(clean_md(kerk_verif) if kerk_verif else "_onbekend_")
    with c3:
        st.caption(wijk_label)

    ontbreekt: list = bronnen_kwaliteit.get("onderbouwing_ontbreekt", []) or []
    if ontbreekt:
        with st.expander(
            f"⚠ Onderbouwing ontbreekt voor {len(ontbreekt)} veld(en)",
            expanded=False,
        ):
            # Uitleg vóór de lijst: zonder deze context is het label "Onderbouwing
            # ontbreekt" voor de prediker onduidelijk (moet ik actie ondernemen?
            # is dit een fout?). Het antwoord is: geen actie vereist, maar wees
            # voorzichtiger met deze specifieke claims in de preek.
            st.caption(
                "Voor deze onderdelen vond de analyse geen expliciete bron in het "
                "web-onderzoek. De inhoud kan nog steeds bruikbaar zijn, maar is "
                "speculatiever — gebruik deze claims niet als harde feiten."
            )
            for dotpad in ontbreekt:
                st.markdown(f"- {clean_md(_leesbaar_pad(str(dotpad)))}")


def _render_bronnen(bronnen: list) -> None:
    """Toon klikbare bronnen met citaat en claim-verwijzing.

    Sortering op claim_id zodat bronnen die hetzelfde veld onderbouwen
    bij elkaar blijven staan — dat helpt de prediker snel te zien hoeveel
    bronnen er voor een specifieke claim zijn.
    """
    if not bronnen:
        st.caption("Geen bronnen geleverd door de analyse — inhoudelijke claims zijn dan speculatiever.")
        return

    with st.expander(f"Bronnen ({len(bronnen)})", expanded=False):
        sorted_bronnen = sorted(bronnen, key=lambda b: b.get("claim_id", ""))
        for bron in sorted_bronnen:
            claim_id = bron.get("claim_id", "")
            citaat = bron.get("uitspraak_citaat", "")
            url = bron.get("url", "")
            datum = bron.get("datum_bron")
            with st.container(border=True):
                if claim_id:
                    st.caption(f"Onderbouwt: `{claim_id}`")
                if citaat:
                    st.markdown(f"> {clean_md(citaat)}")
                footer_parts: list[str] = []
                if url:
                    footer_parts.append(f"[bron]({url})")
                if datum:
                    footer_parts.append(f"*{clean_md(datum)}*")
                if footer_parts:
                    st.markdown(" · ".join(footer_parts))
