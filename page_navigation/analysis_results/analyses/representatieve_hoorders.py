from typing import Any

import streamlit as st

from src.utils.utils import clean_md


def _render_list(values: list) -> None:
    for item in values:
        st.markdown(f"- {clean_md(str(item))}")


def _kv(label: str, value: str) -> None:
    if value:
        st.markdown(f"**{label}:** {clean_md(value)}")


def representatieve_hoorders(analysis: dict[str, Any]) -> None:
    """Render representatieve hoorders analysis result."""
    result: dict[str, Any] = analysis.get("result", {})

    church_name: str = st.session_state.get("church_name", "")
    if church_name:
        st.caption(f"**Gemeente:** {church_name}")

    personas: list = result.get("personas", [])

    if not personas:
        st.info("Geen personas gevonden.")
        return

    for persona in personas:
        naam_obj: dict = persona.get("naam", {})
        voornaam = naam_obj.get("voornaam", "")
        achternaam = naam_obj.get("achternaam", "")
        volledige_naam = f"{voornaam} {achternaam}".strip()
        leeftijd = persona.get("leeftijd", "")
        kernschets: str = persona.get("kernschets", "")

        with st.expander(f"👤 {volledige_naam} ({leeftijd})", expanded=False):
            if kernschets:
                st.info(clean_md(kernschets))

            st.divider()

            col1, col2 = st.columns(2)
            basis: dict = persona.get("basisgegevens", {})
            relaties: dict = persona.get("relaties_sociaal", {})
            with col1:
                st.markdown("**Basisgegevens**")
                _kv("Woonwijk", basis.get("woonwijk", ""))
                st.markdown("**Relaties en sociaal**")
                _kv("Woonsituatie", relaties.get("woonsituatie", ""))
                _kv("Relatiestatus", relaties.get("relatiestatus", ""))
                _kv("Kinderen", relaties.get("kinderen", ""))

            opleiding: dict = persona.get("opleiding_werk", {})
            gezondheid: dict = persona.get("gezondheid", {})
            with col2:
                st.markdown("**Opleiding en werk**")
                _kv("Opleiding", opleiding.get("opleiding", ""))
                _kv("Huidige werk", opleiding.get("huidige_werk", ""))
                st.markdown("**Gezondheid**")
                _kv("Lichamelijk", gezondheid.get("lichamelijk", ""))
                _kv("Mentaal", gezondheid.get("mentale_gezondheid") or gezondheid.get("mentaal", ""))

            st.divider()

            geloof: dict = persona.get("geloof_spiritualiteit", {})
            if geloof:
                st.markdown("**Geloof en spiritualiteit**")
                c1, c2 = st.columns(2)
                with c1:
                    _kv("Kerkelijke achtergrond", geloof.get("kerkelijke_achtergrond", ""))
                    _kv("Geloofsbeleving", geloof.get("geloofsbeleving", ""))
                with c2:
                    geloofsvragen: list = geloof.get("geloofsvragen", [])
                    if geloofsvragen:
                        st.markdown("*Geloofsvragen:*")
                        _render_list(geloofsvragen)

            aansluiting: dict = persona.get("aansluiting_schriftlezingen", {})
            if aansluiting:
                st.markdown("**Aansluiting bij de schriftlezingen**")
                if aansluiting.get("wat_raakt"):
                    st.success(f"**Raakt:** {clean_md(aansluiting['wat_raakt'])}")
                if aansluiting.get("wat_afstoot"):
                    st.warning(f"**Stoot af:** {clean_md(aansluiting['wat_afstoot'])}")
                if aansluiting.get("existentiele_vraag"):
                    st.info(f"**Existentiele vraag:** {clean_md(aansluiting['existentiele_vraag'])}")
