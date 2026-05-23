from typing import Any

import streamlit as st

from src.utils.utils import clean_md, humaniseer_tag


def _render_list(values: list) -> None:
    for item in values:
        st.markdown(f"- {clean_md(str(item))}")


def _render_bronnen(urls: list[str]) -> None:
    # Toon bronnen als klikbare links; compact onder de samenvatting.
    if not urls:
        return
    links = " · ".join(f"[bron {i + 1}]({u})" for i, u in enumerate(urls))
    st.caption(f"Bronnen: {links}")


_CATEGORIE_ICONS = {
    "conflict": "⚔️", "oorlog": "⚔️", "klimaat": "🌍", "natuur": "🌿",
    "politiek": "🏛️", "economie": "💶", "kerk": "⛪", "religie": "✝️",
    "sociaal": "🤝", "gezondheid": "🏥", "terrorisme": "💥",
    "vluchtelingen": "🧳", "humanitair": "🤲", "natuurramp": "🌋",
}

# Streamlit-badge-kleuren per categorie-trefwoord. Sluiten qua semantiek aan
# bij _CATEGORIE_ICONS: rood/oranje voor conflict en geweld, blauw voor
# politiek/economie, groen voor kerk/religie/sociaal, etc. De categorie-string
# komt vrij uit het LLM (bv. 'politieke_crisis', 'gewapend_conflict'), dus we
# matchen op substring zoals bij de iconen.
_CATEGORIE_KLEUREN = {
    "oorlog": "red", "conflict": "red", "terrorisme": "red",
    "natuurramp": "red", "humanitair": "red",
    "vluchtelingen": "orange", "klimaat": "orange",
    "politiek": "blue", "economie": "blue",
    "kerk": "green", "religie": "green", "sociaal": "green",
    "natuur": "green", "gezondheid": "violet",
}


def _categorie_icon(cat: str) -> str:
    low = cat.lower()
    for k, icon in _CATEGORIE_ICONS.items():
        if k in low:
            return icon
    return "📰"


def _categorie_badge_md(cat: str) -> str:
    """Render een rauwe categorie-string als gekleurd Streamlit-badge.

    De LLM levert categorie-waardes als snake_case (bv. 'politieke_crisis');
    via humaniseer_tag wordt dat 'Politieke crisis'. De kleur volgt
    _CATEGORIE_KLEUREN (substring-match), met grijs als neutrale fallback
    zodat onbekende categorieën niet plotseling een willekeurige kleur
    krijgen."""
    if not cat:
        return ""
    label = humaniseer_tag(cat)
    low = cat.lower()
    kleur = next(
        (v for k, v in _CATEGORIE_KLEUREN.items() if k in low),
        "gray",
    )
    return f":{kleur}-background[{label}]"


def wereldnieuws(analysis: dict[str, Any]) -> None:
    """Render wereldnieuws-analyse: wereldgebeurtenissen, Nederlands en kerkelijk nieuws."""
    result: dict[str, Any] = analysis.get("result", {})

    datum: str = result.get("nieuwsoverzicht_datum", "")
    wereld: list = result.get("wereldgebeurtenissen", [])
    nl_nieuws: list = result.get("nederlands_nieuws", [])
    kerkelijk: list = result.get("kerkelijk_nieuws", [])
    suggesties: dict = result.get("suggesties_predikant", {})
    valkuilen: list = result.get("valkuilen", [])

    if datum:
        st.subheader(f"Nieuws voor {datum}")

    st.divider()

    if wereld:
        st.subheader(f"Wereldgebeurtenissen ({len(wereld)})")
        for item in wereld:
            cat = item.get("categorie", "")
            icon = _categorie_icon(cat)
            # Categorie als gehumaniseerde badge in de body i.p.v. rauw in de
            # expander-titel: Streamlit's :kleur-background[]-syntax werkt niet
            # in expander-labels, en in de titel was 'politieke_crisis' juist
            # de visuele ruis die de gebruiker meldde.
            cat_label = humaniseer_tag(cat)
            titel_extra = f" — *{cat_label}*" if cat_label else ""
            with st.expander(f"{icon} {item.get('titel', '')}{titel_extra}", expanded=False):
                badge = _categorie_badge_md(cat)
                if badge:
                    st.markdown(badge)
                c1, c2 = st.columns([2, 1])
                with c1:
                    if item.get("samenvatting"):
                        st.markdown(clean_md(item["samenvatting"]))
                    if item.get("emotionele_impact"):
                        st.markdown(
                            f"**Emotionele impact:** {clean_md(item['emotionele_impact'])}"
                        )
                with c2:
                    if item.get("locatie"):
                        st.caption(f"Locatie: {item['locatie']}")
                    if item.get("datum_gebeurtenis"):
                        st.caption(f"Datum: {item['datum_gebeurtenis']}")
                theo_vragen: list = item.get("theologische_vragen", [])
                if theo_vragen:
                    st.markdown("**Theologische vragen:**")
                    _render_list(theo_vragen)
                relevantie: dict = item.get("relevantie_pkn", {})
                if relevantie:
                    with st.expander("Relevantie PKN", expanded=False):
                        for dim in ("pastoraal", "profetisch", "diaconaal", "liturgisch", "homiletisch"):
                            val = relevantie.get(dim)
                            if val:
                                st.markdown(f"**{dim.capitalize()}:** {clean_md(val)}")
                _render_bronnen(item.get("bronnen_urls", []))

    st.divider()

    if nl_nieuws:
        with st.expander(f"Nederlands nieuws ({len(nl_nieuws)})", expanded=False):
            for item in nl_nieuws:
                with st.container(border=True):
                    st.markdown(f"**{item.get('titel', '')}**")
                    if item.get("datum_item"):
                        st.caption(f"Datum: {item['datum_item']}")
                    if item.get("samenvatting"):
                        st.markdown(clean_md(item["samenvatting"]))
                    if item.get("lokale_relevantie"):
                        st.markdown(
                            f"*Lokale relevantie:* {clean_md(item['lokale_relevantie'])}"
                        )
                    if item.get("relevantie_preek"):
                        st.markdown(
                            f"*Relevantie voor de preek:* {clean_md(item['relevantie_preek'])}"
                        )
                    _render_bronnen(item.get("bronnen_urls", []))

    if kerkelijk:
        with st.expander(f"Kerkelijk nieuws ({len(kerkelijk)})", expanded=False):
            for item in kerkelijk:
                with st.container(border=True):
                    # Zelfde humaniseer-stap als bij de wereldgebeurtenissen
                    # zodat 'kerkelijk_nieuws'-tags niet rauw in CAPS_MET_UNDERSCORES
                    # blijven staan. Geen gekleurd badge hier — kerkelijk nieuws
                    # heeft één algemene kleurklasse en het zou op deze plek
                    # ruis toevoegen ten opzichte van de wereldgebeurtenissen.
                    cat_label = humaniseer_tag(item.get("categorie", ""))
                    titel_extra = f"  — *{cat_label}*" if cat_label else ""
                    st.markdown(
                        f"**{item.get('titel', '')}**{titel_extra}"
                    )
                    if item.get("bron"):
                        st.caption(f"Bron: {item['bron']}")
                    if item.get("datum_item"):
                        st.caption(f"Datum: {item['datum_item']}")
                    if item.get("samenvatting"):
                        st.markdown(clean_md(item["samenvatting"]))
                    if item.get("relevantie_oecumenisch"):
                        st.markdown(
                            f"*Oecumenische relevantie:* {clean_md(item['relevantie_oecumenisch'])}"
                        )
                    if item.get("relevantie_preek"):
                        st.markdown(
                            f"*Relevantie voor de preek:* {clean_md(item['relevantie_preek'])}"
                        )
                    _render_bronnen(item.get("bronnen_urls", []))

    st.divider()

    st.subheader("Suggesties voor de predikant")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**In de preek**")
        _render_list(suggesties.get("in_de_preek", []))
    with c2:
        st.markdown("**In de voorbeden**")
        _render_list(suggesties.get("in_voorbeden", []))
    with c3:
        st.markdown("**Mededelingen / collecte**")
        _render_list(suggesties.get("mededelingen_collecte", []))

    if valkuilen:
        st.divider()
        st.subheader("Valkuilen")
        for v in valkuilen:
            with st.container(border=True):
                st.warning(f"**{v.get('valkuil', '')}** — {clean_md(v.get('risico', ''))}")
                if v.get("advies"):
                    st.markdown(f"*Advies:* {clean_md(v['advies'])}")
