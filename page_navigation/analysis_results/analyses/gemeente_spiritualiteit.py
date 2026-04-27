"""Renderer voor de Tavily-gedreven gemeente-spiritualiteitsanalyse.

Deze renderer toont hetzelfde soort velden als de basis-`geloofsorientatie`
maar voegt twee verschillen toe: (1) een expliciete "Onderscheid van
zustergemeenten"-regel in het gemeente-geloofsprofiel en (2) een
"Bronnen"-expander met klikbare URL's + datum en citaten, plus een
meta-sectie `bronnen_kwaliteit` die de prediker inzicht geeft in hoe
betrouwbaar het profiel is. Reden voor een eigen module (en niet
hergebruik van `geloofsorientatie.py`): de Verdieping-variant heeft
extra schema-velden die de basis-renderer niet kent, en we willen
die informatie niet in het basis-scherm laten lekken.
"""

from typing import Any

import streamlit as st

from src.utils.utils import clean_md


# Labels voor de zes ervaringsgebieden — identiek aan de basis-renderer,
# zodat de prediker twee versies naast elkaar kan lezen zonder verwarring.
_ERVARINGS_LABELS: dict[str, str] = {
    "schepping_goede_leven": "Schepping en het goede leven",
    "eindigheid_zingeving": "Eindigheid en zingeving",
    "menselijk_tekort": "Menselijk tekort",
    "lijden_kwaad": "Lijden en kwaad",
    "wijsheid_volken": "Wijsheid van de volken",
    "humaniteit_gemeenschap": "Humaniteit en gemeenschap",
}


# Top-level secties uit het Tavily-schema → leesbare kopjes. Gebruikt om
# dotpaths in `bronnen_kwaliteit.onderbouwing_ontbreekt` (bv.
# "ervaringsgebieden.menselijk_tekort.taboes") om te zetten naar iets dat
# de prediker begrijpt. De rest van het pad wordt generiek geformatteerd
# via `_leesbaar_pad` zodat we geen mapping hoeven te onderhouden voor
# élk blad-veld in het schema.
_SECTIE_LABELS: dict[str, str] = {
    "ervaringsgebieden": "Ervaringsgebieden",
    "geloofstaal_analyse": "Geloofstaal",
    "spirituele_trends_regio": "Spirituele trends regio",
    "gemeente_geloofsprofiel": "Gemeente-geloofsprofiel",
    "homiletische_implicaties": "Homiletische implicaties",
    "bronnen": "Bronnen",
    "bronnen_kwaliteit": "Bronnen-kwaliteit",
}


def _leesbaar_pad(dotpad: str) -> str:
    """Zet een schema-dotpad om naar een leesbaar label.

    Voorbeeld: "ervaringsgebieden.menselijk_tekort.taboes"
    → "Ervaringsgebieden → Menselijk tekort → Taboes".

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


def _has_content(node: Any) -> bool:
    """Recursief controleren of een sectie überhaupt iets bevat.

    De LLM-output bevat regelmatig dicts/lists vol met lege strings
    en lege arrays — bv. `{"trend": "", "percentage": null,
    "toelichting": ""}`. Een naïeve `if dict:`-check geeft dan True en
    laat de renderer een lege expander/kop bouwen. Deze helper kijkt
    of er ergens in de boomstructuur een betekenisvolle waarde staat,
    zodat we secties zonder inhoud volledig kunnen overslaan.
    """
    if node is None:
        return False
    if isinstance(node, str):
        return bool(node.strip())
    if isinstance(node, (list, tuple)):
        return any(_has_content(x) for x in node)
    if isinstance(node, dict):
        return any(_has_content(v) for v in node.values())
    # Numeriek of bool: tellen we als content (een 0 of False kan zinvol zijn).
    return True


def gemeente_spiritualiteit(analysis: dict[str, Any]) -> None:
    """Render gemeente-spiritualiteitsanalyse resultaat.

    Deze functie wordt aangeroepen door `verdieping.py:_RENDERERS` op basis
    van de AnalysisType.name. De analyse is optioneel (`depends_on: []`),
    dus alle velden kunnen in principe ontbreken — we renderen alleen wat
    daadwerkelijk aanwezig is.
    """
    result: dict[str, Any] = analysis.get("result", {})

    # Church-context bovenaan als geheugensteun voor de prediker: deze
    # analyse draait om déze specifieke gemeente, niet om de plaats.
    church_name: str = st.session_state.get("church_name", "")
    if church_name:
        st.caption(f"**Gemeente:** {church_name}")

    ervaringsgebieden: dict = result.get("ervaringsgebieden", {})
    geloofstaal: dict = result.get("geloofstaal_analyse", {})
    spirituele_trends: dict = result.get("spirituele_trends_regio", {})
    gemeente_profiel: dict = result.get("gemeente_geloofsprofiel", {})
    homiletisch: dict = result.get("homiletische_implicaties", {})
    bronnen: list = result.get("bronnen", []) or []
    bronnen_kwaliteit: dict = result.get("bronnen_kwaliteit", {}) or {}

    # --- Bronnen-kwaliteit meteen bovenaan: transparantie eerst. -----------
    # De prediker moet weten hoe betrouwbaar het profiel is vóórdat hij de
    # inhoud leest. Daarom staat deze sectie bovenaan, niet als een
    # voetnoot onderaan.
    _render_bronnen_kwaliteit(bronnen_kwaliteit, aantal_bronnen=len(bronnen))

    # --- Ervaringsgebieden --------------------------------------------------
    # Subheader pas tonen als minstens één van de zes ervaringsgebieden inhoud
    # heeft — anders verschijnt er een lege kop. `_has_content` filtert ook
    # dicts vol met lege strings/lege arrays die `bool({...})` als True ziet.
    if _has_content(ervaringsgebieden):
        st.subheader("Ervaringsgebieden")
        for key, label in _ERVARINGS_LABELS.items():
            eb: dict = ervaringsgebieden.get(key, {})
            if not _has_content(eb):
                continue
            with st.expander(label, expanded=False):
                for field, val in eb.items():
                    if isinstance(val, list):
                        if val:
                            st.markdown(f"*{field.replace('_', ' ').capitalize()}:*")
                            _render_list(val)
                    elif val:
                        st.markdown(f"**{field.replace('_', ' ').capitalize()}:** {clean_md(val)}")

    # Volgende drie secties (geloofstaal, spirituele trends, gemeente-profiel)
    # alleen tonen als er daadwerkelijk inhoud is. Anders zet je de prediker
    # voor lege expanders/koppen en lege labels — een veel voorkomende klacht
    # bij Tavily-output die regelmatig met lege strings of lege arrays komt.
    if _has_content(geloofstaal):
        st.divider()
        # --- Geloofstaal ----------------------------------------------------
        with st.expander("Geloofstaal analyse", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                if geloofstaal.get("gangbaarheid_christelijke_taal_gemeente"):
                    st.markdown(f"**Gangbaarheid gemeente:** {clean_md(geloofstaal['gangbaarheid_christelijke_taal_gemeente'])}")
            with c2:
                if geloofstaal.get("gangbaarheid_christelijke_taal_regio"):
                    st.markdown(f"**Gangbaarheid regio:** {clean_md(geloofstaal['gangbaarheid_christelijke_taal_regio'])}")
            if geloofstaal.get("vertrouwdheid_liturgie"):
                st.markdown(f"**Vertrouwdheid liturgie:** {clean_md(geloofstaal['vertrouwdheid_liturgie'])}")
            c1, c2 = st.columns(2)
            with c1:
                versleten: list = geloofstaal.get("versleten_woorden", [])
                if versleten:
                    st.markdown("**Versleten woorden:**")
                    _render_list(versleten)
            with c2:
                onbekend: list = geloofstaal.get("onbekende_concepten", [])
                if onbekend:
                    st.markdown("**Onbekende concepten:**")
                    _render_list(onbekend)
            equivalenten: list = geloofstaal.get("seculiere_equivalenten", [])
            if equivalenten:
                st.markdown("**Seculiere equivalenten**")
                cols = st.columns([2, 3])
                cols[0].caption("Religieus concept")
                cols[1].caption("Seculiere taal")
                for eq in equivalenten:
                    c1, c2 = st.columns([2, 3])
                    c1.markdown(f"*{eq.get('religieus_concept', '')}*")
                    c2.markdown(clean_md(eq.get("seculiere_taal", "")))

    # --- Regionale trends ---------------------------------------------------
    if _has_content(spirituele_trends):
        st.divider()
        with st.expander("Spirituele trends regio", expanded=False):
            kerkbezoek: dict = spirituele_trends.get("kerkbezoek", {})
            # Pas de kolom-rij rendreren als minstens één van de drie kerkbezoek-velden
            # inhoud heeft; anders ontstaat er een lege drie-kolomsstrook.
            if _has_content(kerkbezoek):
                c1, c2, c3 = st.columns(3)
                with c1:
                    if kerkbezoek.get("trend"):
                        st.metric("Trend", kerkbezoek["trend"])
                with c2:
                    if kerkbezoek.get("percentage"):
                        st.metric("Percentage", kerkbezoek["percentage"])
                with c3:
                    if kerkbezoek.get("toelichting"):
                        st.markdown(clean_md(kerkbezoek["toelichting"]))
            kerkverlating: dict = spirituele_trends.get("kerkverlating", {})
            # Eerst guard: alleen het 'omvang'-label tonen als omvang non-empty is.
            # Was eerder onvoorwaardelijk waardoor "Kerkverlating — omvang:" zonder
            # waarde verscheen bij ontbrekende data.
            omvang = (kerkverlating.get("omvang") or "").strip()
            if omvang:
                st.markdown(f"**Kerkverlating — omvang:** {clean_md(omvang)}")
            redenen: list = kerkverlating.get("redenen", [])
            if redenen:
                st.markdown("*Redenen:*")
                _render_list(redenen)
            nieuwe_vormen: list = spirituele_trends.get("nieuwe_vormen", [])
            if nieuwe_vormen:
                st.markdown("**Nieuwe vormen van kerk-zijn**")
                for vorm in nieuwe_vormen:
                    with st.container(border=True):
                        st.markdown(f"**{vorm.get('naam', '')}** — *{vorm.get('doelgroep', '')}*")
                        if vorm.get("beschrijving"):
                            st.markdown(clean_md(vorm["beschrijving"]))
            oecumenisch: list = spirituele_trends.get("oecumenische_initiatieven", [])
            if oecumenisch:
                st.markdown("**Oecumenische initiatieven**")
                _render_list(oecumenisch)

    # --- Gemeente-profiel — standaard uitgeklapt, want dit is de kern. -----
    if _has_content(gemeente_profiel):
        st.divider()
        with st.expander("Gemeente geloofsprofiel", expanded=True):
            if gemeente_profiel.get("theologische_positie"):
                st.info(clean_md(gemeente_profiel["theologische_positie"]))
            # Nieuwe sectie t.o.v. basis-renderer: expliciete differentiatie
            # van zustergemeenten. Dit is de hoofdwinst van het Tavily-onderzoek
            # en verdient daarom een eigen callout.
            if gemeente_profiel.get("onderscheid_van_zustergemeenten"):
                st.markdown("**Onderscheid van zustergemeenten in dezelfde plaats**")
                st.warning(clean_md(gemeente_profiel["onderscheid_van_zustergemeenten"]))
            if gemeente_profiel.get("verhouding_tot_plaatscultuur"):
                st.markdown(f"**Verhouding tot plaatscultuur:** {clean_md(gemeente_profiel['verhouding_tot_plaatscultuur'])}")
            if gemeente_profiel.get("verwachte_liturgische_stijl"):
                st.markdown(f"**Liturgische stijl:** {clean_md(gemeente_profiel['verwachte_liturgische_stijl'])}")
            kenmerken: list = gemeente_profiel.get("distinctieve_kenmerken", [])
            if kenmerken:
                st.markdown("**Distinctieve kenmerken:**")
                _render_list(kenmerken)

    # --- Homiletische implicaties ------------------------------------------
    if _has_content(homiletisch):
        st.divider()
        st.subheader("Homiletische implicaties")
        if homiletisch.get("geloofstaal_advies"):
            st.success(clean_md(homiletisch["geloofstaal_advies"]))
        c1, c2 = st.columns(2)
        with c1:
            aanknopingspunten: list = homiletisch.get("aanknopingspunten", [])
            if aanknopingspunten:
                st.markdown("**Aanknopingspunten:**")
                _render_list(aanknopingspunten)
        with c2:
            te_vermijden: list = homiletisch.get("te_vermijden_aannames", [])
            if te_vermijden:
                st.markdown("**Te vermijden aannames:**")
                _render_list(te_vermijden)

    # --- Bronnen — klikbaar, per claim. ------------------------------------
    if bronnen:
        st.divider()
        _render_bronnen(bronnen)


def _render_bronnen_kwaliteit(bronnen_kwaliteit: dict, *, aantal_bronnen: int) -> None:
    """Toon een compacte meta-indicatie van bronbetrouwbaarheid bovenaan.

    Argument `aantal_bronnen` komt uit de lengte van `result["bronnen"]`;
    we vertrouwen niet blind op het `aantal_bronnen`-veld uit het schema
    want een LLM kan dat veld vergeten bijwerken (daarom tellen we zelf).
    """
    if not bronnen_kwaliteit:
        return

    # Kort samenvattingsregel als caption: snel te scannen.
    differentiatie = bronnen_kwaliteit.get("differentiatie_geslaagd", "")
    website_ok = bronnen_kwaliteit.get("website_beschikbaar")
    # Icoon voor website-beschikbaarheid — visueel direct duidelijk of
    # de gemeente-website gebruikt kon worden als primaire bron.
    website_label = "✓ website beschikbaar" if website_ok else "✗ geen website"
    # Alleen "Bronnen" is een echte numerieke metric die `st.metric` verdient.
    # "Differentiatie" bevat vrije tekst ("ja, zeer goed — …") en wordt in
    # het grote metric-lettertype visueel onleesbaar; daarom als kop+tekst.
    c1, c2, c3 = st.columns([1, 3, 2])
    with c1:
        st.metric("Bronnen", aantal_bronnen)
    with c2:
        st.markdown("**Differentiatie**")
        st.markdown(clean_md(differentiatie) if differentiatie else "_onbekend_")
    with c3:
        st.caption(website_label)

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
