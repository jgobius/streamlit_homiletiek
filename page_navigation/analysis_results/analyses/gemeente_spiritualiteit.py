"""Renderer voor de Tavily-gedreven gemeente-spiritualiteitsanalyse.

Deze renderer toont hetzelfde soort velden als de basis-`geloofsorientatie`
maar voegt één onderscheidende sectie toe: een expliciete "Onderscheid van
zustergemeenten"-regel in het gemeente-geloofsprofiel. Bronnen en
de meta-sectie over bronkwaliteit worden bewust niet getoond aan de eindgebruiker;
die data blijft wel in het analyse-resultaat staan voor latere inspectie.
Reden voor een eigen module (en niet hergebruik van `geloofsorientatie.py`):
de Verdieping-variant heeft extra schema-velden die de basis-renderer niet kent,
en we willen die informatie niet in het basis-scherm laten lekken.
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

    # Bronnen en bronnen-kwaliteit worden bewust niet meer gerenderd: voor
    # de prediker zijn ze ruis. Ze blijven wel in het analyse-resultaat
    # aanwezig voor diagnose en eventuele latere weergave.

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

    # --- Gemeente-profiel — standaard ingeklapt voor consistente rust. -----
    if _has_content(gemeente_profiel):
        with st.expander("Gemeente geloofsprofiel", expanded=False):
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
