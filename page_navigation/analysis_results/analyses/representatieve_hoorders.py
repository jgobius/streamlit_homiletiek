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

            # Kernschets prominent
            if kernschets:
                st.info(clean_md(kernschets))

            st.divider()

            # Basisgegevens + Relaties + Opleiding + Gezondheid (compact key-value)
            col1, col2 = st.columns(2)

            basis: dict = persona.get("basisgegevens", {})
            relaties: dict = persona.get("relaties_sociaal", {})
            with col1:
                st.markdown("**Basisgegevens**")
                _kv("Woonwijk", basis.get("woonwijk", ""))
                _kv("Fysieke verschijning", basis.get("fysieke_verschijning", ""))
                st.markdown("**Relaties en sociaal**")
                _kv("Woonsituatie", relaties.get("woonsituatie", ""))
                _kv("Relatiestatus", relaties.get("relatiestatus", ""))
                _kv("Kinderen", relaties.get("kinderen", ""))
                _kv("Familie", relaties.get("familie_relatie", ""))
                _kv("Sociaal netwerk", relaties.get("sociaal_netwerk", ""))

            opleiding: dict = persona.get("opleiding_werk", {})
            gezondheid: dict = persona.get("gezondheid", {})
            with col2:
                st.markdown("**Opleiding en werk**")
                _kv("Opleiding", opleiding.get("opleiding", ""))
                _kv("Leerstijl", opleiding.get("intelligentie_leerstijl", ""))
                _kv("Huidige werk", opleiding.get("huidige_werk", ""))
                _kv("Voormalig werk", opleiding.get("voormalig_werk", ""))
                _kv("Financieel", opleiding.get("financiele_situatie", ""))
                st.markdown("**Gezondheid**")
                _kv("Lichamelijk", gezondheid.get("lichamelijk", ""))
                _kv("Mentaal", gezondheid.get("mentaal", ""))
                _kv("Leefstijl", gezondheid.get("leefstijl", ""))

            st.divider()

            # Levensgeschiedenis
            levensg: dict = persona.get("levensgeschiedenis_vragen", {})
            if levensg:
                st.markdown("**Levensgeschiedenis en vragen**")
                gevormd: list = levensg.get("wat_heeft_gevormd", [])
                speelt_nu: list = levensg.get("wat_speelt_nu", [])
                onuitgesproken: str = levensg.get("onuitgesproken", "")
                c1, c2 = st.columns(2)
                with c1:
                    if gevormd:
                        st.markdown("*Wat heeft gevormd:*")
                        _render_list(gevormd)
                with c2:
                    if speelt_nu:
                        st.markdown("*Wat speelt nu:*")
                        _render_list(speelt_nu)
                if onuitgesproken:
                    st.caption(f"Onuitgesproken: {clean_md(onuitgesproken)}")

            st.divider()

            # Geloof en spiritualiteit
            geloof: dict = persona.get("geloof_spiritualiteit", {})
            if geloof:
                st.markdown("**Geloof en spiritualiteit**")
                c1, c2 = st.columns(2)
                with c1:
                    _kv("Kerkelijke achtergrond", geloof.get("kerkelijke_achtergrond", ""))
                    _kv("Huidige betrokkenheid", geloof.get("huidige_betrokkenheid", ""))
                    _kv("Geloofsbeleving", geloof.get("geloofsbeleving", ""))
                    _kv("Geloofstaal", geloof.get("geloofstaal", ""))
                with c2:
                    geloofsvragen: list = geloof.get("geloofsvragen", [])
                    if geloofsvragen:
                        st.markdown("*Geloofsvragen:*")
                        _render_list(geloofsvragen)
                    verwachting: str = geloof.get("spirituele_verwachting", "")
                    if verwachting:
                        st.caption(f"Spirituele verwachting: {clean_md(verwachting)}")

            # Hobbys en interesses (compact)
            hobbys: dict = persona.get("hobbys_interesses", {})
            if hobbys:
                all_items = []
                for key in ("vrijetijd", "media", "verenigingen"):
                    items = hobbys.get(key, [])
                    if items:
                        all_items.append(f"*{key.capitalize()}:* " + ", ".join(items))
                if all_items:
                    st.caption(" | ".join(all_items))

            st.divider()

            # Aansluiting bij de schriftlezingen
            aansluiting: dict = persona.get("aansluiting_schriftlezingen", {})
            if aansluiting:
                st.markdown("**Aansluiting bij de schriftlezingen**")
                if aansluiting.get("wat_raakt"):
                    st.success(f"**Raakt:** {clean_md(aansluiting['wat_raakt'])}")
                if aansluiting.get("wat_afstoot"):
                    st.warning(f"**Stoot af:** {clean_md(aansluiting['wat_afstoot'])}")
                if aansluiting.get("existentiele_vraag"):
                    st.info(f"**Existentiele vraag:** {clean_md(aansluiting['existentiele_vraag'])}")
