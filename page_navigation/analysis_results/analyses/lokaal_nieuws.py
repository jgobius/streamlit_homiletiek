from typing import Any

import streamlit as st

from src.utils.utils import clean_md


def _render_list(values: list) -> None:
    for item in values:
        st.markdown(f"- {clean_md(str(item))}")


def _render_bronnen(urls: list[str]) -> None:
    # Toon bronnen als klikbare links onder het item.
    if not urls:
        return
    links = " · ".join(f"[bron {i + 1}]({u})" for i, u in enumerate(urls))
    st.caption(f"Bronnen: {links}")


def _render_homiletische_duiding(duiding: dict[str, Any]) -> None:
    # Vijf dimensies zoals in wereldnieuws: pastoraal, profetisch, diaconaal,
    # liturgisch, homiletisch. Compact gestapeld om de lezer niet te overladen.
    if not duiding:
        return
    with st.expander("Homiletische duiding", expanded=False):
        for dim in ("pastoraal", "profetisch", "diaconaal", "liturgisch", "homiletisch"):
            val = duiding.get(dim)
            if val:
                st.markdown(f"**{dim.capitalize()}:** {clean_md(val)}")


def lokaal_nieuws(analysis: dict[str, Any]) -> None:
    """Render lokaal_nieuws: actueel nieuws dat aantoonbaar binnen de gemeente speelt."""
    result: dict[str, Any] = analysis.get("result", {})

    context: dict = result.get("context", {})
    rapport_datum: str = result.get("rapport_datum", "")
    items: list = result.get("lokaal_actueel_nieuws", [])
    suggesties: dict = result.get("suggesties_predikant", {})
    valkuilen: list = result.get("valkuilen", [])

    # Context bovenaan: plaats, gemeente, jaar — dit zijn de invoervariabelen
    # waarop de zoekopdracht is gebaseerd.
    gemeente = context.get("gemeentenaam", "")
    plaats = context.get("plaatsnaam", "")
    jaar = context.get("jaar", "")
    if any([gemeente, plaats, jaar]):
        parts = [p for p in (gemeente, plaats, str(jaar) if jaar else "") if p]
        st.subheader(" — ".join(parts))

    if rapport_datum:
        st.caption(f"Rapportdatum: {rapport_datum}")

    if items:
        st.subheader(f"Lokaal actueel nieuws ({len(items)})")
        for item in items:
            titel = item.get("titel", "")
            # Korte kop in de expander-titel: plaats + datum als beschikbaar.
            localiteit = item.get("localiteit", {}) or {}
            plaats_kern = localiteit.get("plaats_of_kern", "")
            datum_pub = item.get("datum_publicatie") or ""
            subtitel_parts = [p for p in (plaats_kern, datum_pub) if p]
            subtitel = f"  — *{' · '.join(subtitel_parts)}*" if subtitel_parts else ""
            with st.expander(f"📰 {titel}{subtitel}", expanded=False):
                if item.get("samenvatting"):
                    st.markdown(clean_md(item["samenvatting"]))

                # Localiteitsdetails naast elkaar zodat de gebruiker snel ziet
                # waarop de lokale binding berust.
                if localiteit:
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        if localiteit.get("gemeente"):
                            st.caption(f"Gemeente: {localiteit['gemeente']}")
                    with c2:
                        if localiteit.get("plaats_of_kern"):
                            st.caption(f"Plaats/kern: {localiteit['plaats_of_kern']}")
                    with c3:
                        if localiteit.get("concrete_locatie"):
                            st.caption(
                                f"Locatie: {localiteit['concrete_locatie']}"
                            )

                _render_homiletische_duiding(item.get("homiletische_duiding", {}))
                _render_bronnen(item.get("bronnen", []))

    st.divider()

    # Lokaal-nieuws kent alleen preeklijnen en voorbeden (geen mededelingen/collecte,
    # anders dan bij wereldnieuws).
    st.subheader("Suggesties voor de predikant")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Preeklijnen**")
        _render_list(suggesties.get("preeklijnen", []))
    with c2:
        st.markdown("**Voorbeden**")
        _render_list(suggesties.get("voorbeden", []))

    if valkuilen:
        st.divider()
        st.subheader("Valkuilen")
        for v in valkuilen:
            with st.container(border=True):
                st.warning(f"**{v.get('valkuil', '')}** — {clean_md(v.get('risico', ''))}")
                if v.get("advies"):
                    st.markdown(f"*Advies:* {clean_md(v['advies'])}")
