"""Renderer voor de Verdieping-analyse 'poezie_meertalig'.

Toont zes gedichten — drie klassiek en drie modern — verdeeld over twee
sub-tabs (Klassiek / Modern). Per gedicht een rustig kaartje
(`st.container(border=True)`) met de originele tekst in cursief, een
gekleurde taal-badge, een uitklapbare Nederlandse vertaling of parafrase,
de motivatie als caption en een bron-link onderaan. Stijl is bewust
ingetogen — vergelijkbaar met de Kunst & Cultuur-renderer in
`verdieping.py` — om de gedichten zelf te laten ademen.
"""

from typing import Any

import streamlit as st

from src.utils.utils import clean_md


# Per taal een vaste Streamlit-badge-kleur. De kleuren zijn ingetogen
# gespreid (blauw/groen/violet/oranje/grijs) zodat geen taal visueel
# domineert. Onbekende talen vallen terug op grijs via _taal_badge().
_TAAL_KLEUREN: dict[str, str] = {
    "nl": "blue",
    "en": "violet",
    "de": "orange",
    "fr": "green",
    "pt": "red",
    "es": "gray",
}

# Volledige taalnamen voor de badge. Een ISO-code als 'nl' is voor de
# prediker minder direct leesbaar dan 'Nederlands'.
_TAAL_NAMEN: dict[str, str] = {
    "nl": "Nederlands",
    "en": "Engels",
    "de": "Duits",
    "fr": "Frans",
    "pt": "Portugees",
    "es": "Spaans",
}


def _taal_badge(taal: str) -> str:
    # Geef een Streamlit-markdown-badge terug voor een ISO-taalcode.
    # Onbekende codes vallen terug op een grijze badge met de raw waarde,
    # zodat de UI niet leeg blijft als er ooit een nieuwe taal bijkomt.
    naam = _TAAL_NAMEN.get(taal, taal.upper() if taal else "")
    kleur = _TAAL_KLEUREN.get(taal, "gray")
    return f":{kleur}-background[{naam}]"


def _format_origineel(tekst: str) -> str:
    # Behoud de regelafbreking van het gedicht bij rendering. Het LLM
    # levert regelafbrekingen als '\n'; voor markdown moeten dat twee
    # spaties + nieuwe regel worden om als zachte regelafbreking te
    # renderen i.p.v. samengevoegd tot een lopende paragraaf. Cursief
    # markeren we via één laag asterisken rond de tekst.
    if not tekst:
        return ""
    regels = clean_md(tekst).split("\n")
    # Lege regels tussen strofen behouden we als visuele witregel.
    return "  \n".join(regels)


def _render_gedicht_kaart(gedicht: dict[str, Any], nummer: int) -> None:
    # Eén kaartje per gedicht. Lay-out:
    #   header  : titel — dichter (jaar)  · taal-badge
    #   tekst   : originele cursieve regels
    #   expander: NL-vertaling of parafrase
    #   caption : motivatie
    #   bottom  : bron-link
    titel: str = gedicht.get("titel", "Onbekend")
    dichter: str = gedicht.get("dichter", "")
    jaartal: str = gedicht.get("jaartal_of_periode", "")
    taal: str = gedicht.get("taal", "")
    origineel: str = gedicht.get("originele_tekst", "")
    vertaling: str = gedicht.get("vertaling_of_parafrase", "")
    motivatie: str = gedicht.get("motivatie", "")
    bron: str = gedicht.get("bron_url", "")

    with st.container(border=True):
        # Header op één regel: nummering + titel + dichter + jaartal links,
        # taal-badge rechts. Twee kolommen geven visuele rust en houden
        # de badge consistent op dezelfde plek per kaartje.
        kop_links, kop_rechts = st.columns([5, 2])
        with kop_links:
            kop = f"**{nummer}. {clean_md(titel)}**"
            if dichter:
                kop += f" — {clean_md(dichter)}"
            if jaartal:
                kop += f" ({clean_md(jaartal)})"
            st.markdown(kop)
        with kop_rechts:
            if taal:
                st.markdown(_taal_badge(taal))

        # Originele tekst in cursief markdown, met regelafbreking behouden.
        # Voor een NL-gedicht is de "originele tekst" gewoon de tekst zelf.
        if origineel:
            st.markdown(f"*{_format_origineel(origineel)}*")

        # Vertaling of parafrase. Voor NL-gedichten labelen we het als
        # 'Parafrase' (kort, snel scanbaar voor de prediker), voor
        # anderstaligen als 'Nederlandse vertaling'. Alle expanders
        # default dicht — de gebruiker bepaalt zelf welke kaartjes hij
        # uitklapt; dat houdt het overzicht rustig en consistent.
        if vertaling:
            label = "Parafrase" if taal == "nl" else "Nederlandse vertaling"
            with st.expander(label, expanded=False):
                st.markdown(clean_md(vertaling))

        # Motivatie als caption — bewust niet als st.info, om het rustige
        # ritme van de kaart niet te doorbreken met een gekleurd blok.
        if motivatie:
            st.caption(clean_md(motivatie))

        # Bron-link onderaan. Markdown-link is klikbaar in Streamlit.
        if bron:
            st.markdown(f"[Bron]({bron})")


def _render_categorie(gedichten: list[dict[str, Any]], categorie: str) -> None:
    # Filter de zes gedichten op categorie en render ze als genummerde
    # kaartjes. Wanneer een categorie leeg is (bv. door een mislukte
    # generatie) tonen we een korte info-tekst i.p.v. niets, zodat de
    # gebruiker ziet dat het tabblad niet kapot is.
    items = [g for g in gedichten if g.get("categorie") == categorie]
    if not items:
        st.info(f"Geen {categorie}e gedichten beschikbaar.")
        return
    for i, gedicht in enumerate(items, start=1):
        _render_gedicht_kaart(gedicht, i)


def poezie_meertalig(analysis: dict[str, Any]) -> None:
    """Renderer voor `poezie_meertalig` — twee tabs Klassiek / Modern.

    Verwacht in `analysis['result']` een dict met sleutels `gedichten`
    (lijst van zes items) en `selectie_overwegingen` (paragraaf).
    """
    result: dict[str, Any] = analysis.get("result", {}) or {}
    gedichten: list[dict[str, Any]] = result.get("gedichten", []) or []
    overwegingen: str = result.get("selectie_overwegingen", "") or ""

    if not gedichten:
        st.info("Geen gedichten beschikbaar.")
        return

    tab_klassiek, tab_modern = st.tabs(["Klassiek", "Modern"])
    with tab_klassiek:
        _render_categorie(gedichten, "klassiek")
    with tab_modern:
        _render_categorie(gedichten, "modern")

    # Selectie-overwegingen onderaan in een dichte expander — eerst de
    # gedichten zelf, en pas daarna de strategie/uitkomstkader voor
    # wie er bewust naar wil kijken.
    if overwegingen:
        with st.expander("Selectie-overwegingen", expanded=False):
            st.markdown(clean_md(overwegingen))
