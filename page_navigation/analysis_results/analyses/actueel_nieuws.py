from typing import Any

import streamlit as st

from src.utils.utils import clean_md


def _render_list(values: list) -> None:
    for item in values:
        st.markdown(f"- {clean_md(str(item))}")


_CATEGORIE_ICONS = {
    "conflict": "⚔️", "oorlog": "⚔️", "klimaat": "🌍", "natuur": "🌿",
    "politiek": "🏛️", "economie": "💶", "kerk": "⛪", "religie": "✝️",
    "sociaal": "🤝", "gezondheid": "🏥",
}


def _categorie_icon(cat: str) -> str:
    low = cat.lower()
    for k, icon in _CATEGORIE_ICONS.items():
        if k in low:
            return icon
    return "📰"


def actueel_nieuws(analysis: dict[str, Any]) -> None:
    """Render actueel nieuws analysis result."""
    result: dict[str, Any] = analysis.get("result", {})

    place: str = st.session_state.get("church_place", "")
    if place:
        st.caption(f"**Plaats:** {place}")

    datum: str = result.get("nieuwsoverzicht_datum", "")
    zoek_verificatie: str = result.get("zoek_verificatie", "")
    wereld: list = result.get("wereldgebeurtenissen", [])
    nl_nieuws: list = result.get("nederlands_nieuws", [])
    kerkelijk: list = result.get("kerkelijk_nieuws", [])
    suggesties: dict = result.get("suggesties_predikant", {})
    valkuilen: list = result.get("valkuilen", [])

    if datum:
        st.subheader(f"Nieuws voor {datum}")
    if zoek_verificatie:
        st.caption(clean_md(zoek_verificatie))

    st.divider()

    if wereld:
        st.subheader(f"Wereldgebeurtenissen ({len(wereld)})")
        for item in wereld:
            cat = item.get("categorie", "")
            icon = _categorie_icon(cat)
            with st.expander(f"{icon} {item.get('titel', '')}  — *{cat}*", expanded=False):
                c1, c2 = st.columns([2, 1])
                with c1:
                    if item.get("samenvatting"):
                        st.markdown(clean_md(item["samenvatting"]))
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

    st.divider()

    if nl_nieuws:
        with st.expander(f"Nederlands nieuws ({len(nl_nieuws)})", expanded=False):
            for item in nl_nieuws:
                with st.container(border=True):
                    st.markdown(f"**{item.get('titel', '')}**")
                    if item.get("samenvatting"):
                        st.markdown(clean_md(item["samenvatting"]))

    if kerkelijk:
        with st.expander(f"Kerkelijk nieuws ({len(kerkelijk)})", expanded=False):
            for item in kerkelijk:
                with st.container(border=True):
                    st.markdown(f"**{item.get('titel', '')}**  — *{item.get('categorie', '')}*")
                    st.caption(f"Bron: {item.get('bron', '')}")
                    if item.get("samenvatting"):
                        st.markdown(clean_md(item["samenvatting"]))

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
