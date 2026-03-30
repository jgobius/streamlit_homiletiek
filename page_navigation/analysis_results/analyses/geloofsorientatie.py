from typing import Any

import streamlit as st

from src.utils.utils import clean_md


def _render_list(values: list) -> None:
    for item in values:
        st.markdown(f"- {clean_md(str(item))}")


_ERVARINGS_LABELS = {
    "schepping_goede_leven": "Schepping en het goede leven",
    "eindigheid_zingeving": "Eindigheid en zingeving",
    "menselijk_tekort": "Menselijk tekort",
    "lijden_kwaad": "Lijden en kwaad",
    "wijsheid_volken": "Wijsheid van de volken",
    "humaniteit_gemeenschap": "Humaniteit en gemeenschap",
}


def geloofsorientatie(analysis: dict[str, Any]) -> None:
    """Render geloofsorientatie analysis result."""
    result: dict[str, Any] = analysis.get("result", {})

    church_name: str = st.session_state.get("church_name", "")
    if church_name:
        st.caption(f"**Gemeente:** {church_name}")

    ervaringsgebieden: dict = result.get("ervaringsgebieden", {})
    geloofstaal: dict = result.get("geloofstaal_analyse", {})
    spirituele_trends: dict = result.get("spirituele_trends_regio", {})
    gemeente_profiel: dict = result.get("gemeente_geloofsprofiel", {})
    homiletisch: dict = result.get("homiletische_implicaties", {})

    # ── Ervaringsgebieden ─────────────────────────────────────────────────────
    st.subheader("Ervaringsgebieden")
    for key, label in _ERVARINGS_LABELS.items():
        eb: dict = ervaringsgebieden.get(key, {})
        if not eb:
            continue
        with st.expander(label, expanded=False):
            for field, val in eb.items():
                if isinstance(val, list):
                    if val:
                        st.markdown(f"*{field.replace('_', ' ').capitalize()}:*")
                        _render_list(val)
                elif val:
                    st.markdown(f"**{field.replace('_', ' ').capitalize()}:** {clean_md(val)}")

    st.divider()

    # ── Geloofstaal analyse ────────────────────────────────────────────────────
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

    st.divider()

    # ── Spirituele trends regio ───────────────────────────────────────────────
    with st.expander("Spirituele trends regio", expanded=False):
        kerkbezoek: dict = spirituele_trends.get("kerkbezoek", {})
        if kerkbezoek:
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
        if kerkverlating:
            st.markdown(f"**Kerkverlating — omvang:** {clean_md(kerkverlating.get('omvang', ''))}")
            redenen: list = kerkverlating.get("redenen", [])
            if redenen:
                st.markdown("*Redenen:*")
                _render_list(redenen)

        nieuwe_vormen: list = spirituele_trends.get("nieuwe_vormen", [])
        if nieuwe_vormen:
            st.markdown("**Nieuwe vormen van kerk-zijn**")
            for vorm in nieuwe_vormen:
                with st.container(border=True):
                    st.markdown(f"**{vorm.get('naam', '')}**  — *{vorm.get('doelgroep', '')}*")
                    if vorm.get("beschrijving"):
                        st.markdown(clean_md(vorm["beschrijving"]))

        oecumene: list = spirituele_trends.get("oecumenische_initiatieven", [])
        if oecumene:
            st.markdown("**Oecumenische initiatieven:**")
            _render_list(oecumene)

    st.divider()

    # ── Gemeente geloofsprofiel ───────────────────────────────────────────────
    with st.expander("Gemeente geloofsprofiel", expanded=True):
        if gemeente_profiel.get("theologische_positie"):
            st.info(clean_md(gemeente_profiel["theologische_positie"]))
        if gemeente_profiel.get("verhouding_tot_plaatscultuur"):
            st.markdown(f"**Verhouding tot plaatscultuur:** {clean_md(gemeente_profiel['verhouding_tot_plaatscultuur'])}")
        if gemeente_profiel.get("verwachte_liturgische_stijl"):
            st.markdown(f"**Liturgische stijl:** {clean_md(gemeente_profiel['verwachte_liturgische_stijl'])}")
        kenmerken: list = gemeente_profiel.get("distinctieve_kenmerken", [])
        if kenmerken:
            st.markdown("**Distinctieve kenmerken:**")
            _render_list(kenmerken)

    st.divider()

    # ── Homiletische implicaties ──────────────────────────────────────────────
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
