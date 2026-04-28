from typing import Any

import streamlit as st

from src.utils.utils import clean_md


def _render_list(values: list) -> None:
    # Simpele bullet-lijst; clean_md strippen we op elk item zodat losse markdown-chars
    # geen rendering-artefacten geven.
    for item in values:
        st.markdown(f"- {clean_md(str(item))}")


def _render_lokale_context(lokale: dict[str, Any]) -> None:
    # Toont bovenaan op welk geografisch niveau de synthese is uitgevoerd.
    # Bewust klein gehouden: het is context voor alles eronder, geen hoofdzaak.
    if not lokale:
        return
    niveau = lokale.get("analyse_niveau") or ""
    wijk = lokale.get("wijk_of_kern") or ""
    postcode = lokale.get("postcodegebied") or ""
    waarom = lokale.get("waarom_deze_schaal") or ""
    verhouding = lokale.get("wijk_versus_gemeente") or ""

    with st.container(border=True):
        kop = "📍 Lokale context"
        if wijk:
            kop = f"📍 {wijk}"
        if postcode:
            kop = f"{kop} · {postcode}"
        if niveau:
            kop = f"{kop} · niveau: {niveau}"
        st.markdown(f"**{kop}**")
        if verhouding:
            st.markdown(f"**Wijk vs. gemeente:** {clean_md(verhouding)}")
        if waarom:
            st.caption(f"Schaalkeuze: {clean_md(waarom)}")


def _render_specifiek_voor_datum(specifiek: dict[str, Any]) -> None:
    if not specifiek:
        return
    seizoen: list = specifiek.get("seizoens_associaties", []) or []
    verwachting: str = specifiek.get("verwachting_hoorders") or ""
    actualiteit: list = specifiek.get("actualiteit", []) or []
    if not (seizoen or verwachting or actualiteit):
        return
    with st.expander("Specifiek voor deze zondag", expanded=False):
        if verwachting:
            st.markdown(f"**Wat verwachten hoorders:** {clean_md(verwachting)}")
        if seizoen:
            st.markdown("**Seizoens-/liturgische associaties:**")
            _render_list(seizoen)
        if actualiteit:
            st.markdown("**Actualiteit die meespeelt:**")
            _render_list(actualiteit)


def _render_waarschuwingen(waarschuwingen: list) -> None:
    if not waarschuwingen:
        return
    st.markdown("**Waarschuwingen — heilige huisjes en gevoeligheden**")
    for w in waarschuwingen:
        if not isinstance(w, dict):
            continue
        onderwerp = w.get("onderwerp") or ""
        risico = w.get("risico") or ""
        advies = w.get("advies") or ""
        with st.container(border=True):
            if onderwerp:
                st.markdown(f"**{clean_md(onderwerp)}**")
            if risico:
                st.markdown(f"*Risico:* {clean_md(risico)}")
            if advies:
                st.markdown(f"*Advies:* {clean_md(advies)}")


def interpretatieve_synthese(analysis: dict[str, Any]) -> None:
    """Render interpretatieve synthese analysis result."""
    result: dict[str, Any] = analysis.get("result", {})

    lokale: dict = result.get("lokale_context", {}) or {}
    congruentie: dict = result.get("congruentie_analyse", {}) or {}
    verbindingspunten: dict = result.get("verbindingspunten", {}) or {}
    confrontatie: dict = result.get("confrontatiepunten", {}) or {}
    hoorders: dict = result.get("hoordersanalyse", {}) or {}
    specifiek: dict = result.get("specifiek_voor_datum", {}) or {}
    aanbevelingen: dict = result.get("homiletische_aanbevelingen", {}) or {}

    # Bovenaan: op welk geografisch niveau is er gesynthetiseerd en hoe verhoudt
    # de gemeente zich tot de wijk? Geeft de prediker direct duiding van de scope.
    _render_lokale_context(lokale)

    # Standaard ingeklapt zodat de prediker de synthese-onderdelen zelf openvouwt;
    # dat sluit aan bij de andere expanders hieronder en houdt de pagina rustig.
    with st.expander("Congruentie-analyse: norm vs. praktijk", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            if congruentie.get("officiele_geloofsopvatting"):
                st.markdown("**Officiele geloofsopvatting**")
                st.markdown(clean_md(congruentie["officiele_geloofsopvatting"]))
        with c2:
            if congruentie.get("geleefde_praktijk"):
                st.markdown("**Geleefde praktijk**")
                st.markdown(clean_md(congruentie["geleefde_praktijk"]))
        spanningen: list = congruentie.get("spanningen_norm_praktijk", []) or []
        if spanningen:
            st.markdown("**Spanningen norm–praktijk:**")
            _render_list(spanningen)
        aannames: list = congruentie.get("onbewuste_aannames", []) or []
        if aannames:
            st.markdown("**Onbewuste aannames:**")
            _render_list(aannames)

    with st.expander("Verbindingspunten", expanded=False):
        aansluiting: list = verbindingspunten.get("aansluiting_geleefde_ervaring", []) or []
        if aansluiting:
            st.markdown("**Aansluiting geleefde ervaring:**")
            _render_list(aansluiting)
        resonerende: list = verbindingspunten.get("resonerende_beelden", []) or []
        if resonerende:
            st.markdown("**Resonerende beelden**")
            for beeld in resonerende:
                if not isinstance(beeld, dict):
                    continue
                with st.container(border=True):
                    c1, c2 = st.columns([2, 2])
                    with c1:
                        st.markdown(f"**{beeld.get('beeld', '')}**")
                        if beeld.get("waarom_resoneert"):
                            st.markdown(clean_md(beeld["waarom_resoneert"]))
                    with c2:
                        if beeld.get("bijbelse_parallel"):
                            st.caption(
                                f"Bijbelse parallel: {clean_md(beeld['bijbelse_parallel'])}"
                            )
        brugverhalen: list = verbindingspunten.get("brugverhalen", []) or []
        if brugverhalen:
            st.markdown("**Brugverhalen uit de gemeenschap:**")
            _render_list(brugverhalen)

    with st.expander("Confrontatiepunten", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            bijbel_conf: list = confrontatie.get("bijbeltekst_confronteert", []) or []
            if bijbel_conf:
                st.markdown("**Bijbeltekst confronteert:**")
                _render_list(bijbel_conf)
        with c2:
            profetisch: list = confrontatie.get("profetische_kritiek", []) or []
            if profetisch:
                st.markdown("**Profetische kritiek:**")
                _render_list(profetisch)
        with c3:
            blind: list = confrontatie.get("blinde_vlekken", []) or []
            if blind:
                st.markdown("**Blinde vlekken:**")
                _render_list(blind)

    with st.expander("Hoordersanalyse", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            los_te_laten: list = hoorders.get("los_te_laten_aannames", []) or []
            if los_te_laten:
                st.markdown("**Los te laten aannames:**")
                _render_list(los_te_laten)
        with c2:
            diversiteit: list = hoorders.get("diversiteit_binnen_gemeente", []) or []
            if diversiteit:
                st.markdown("**Diversiteit gemeente:**")
                _render_list(diversiteit)
        with c3:
            onzichtbaar: list = hoorders.get("onzichtbare_hoorders", []) or []
            if onzichtbaar:
                st.markdown("**Onzichtbare hoorders:**")
                _render_list(onzichtbaar)

    # Datum-specifieke duiding — los blok, ingeklapt zodat de synthese eerst leidend is.
    _render_specifiek_voor_datum(specifiek)

    st.divider()

    st.subheader("Homiletische aanbevelingen")
    toon: dict = aanbevelingen.get("toon", {}) or {}
    if toon:
        c1, c2 = st.columns(2)
        with c1:
            if toon.get("aanbevolen"):
                st.success(f"**Toon aanbevolen:** {clean_md(toon['aanbevolen'])}")
        with c2:
            if toon.get("te_vermijden"):
                st.warning(f"**Toon te vermijden:** {clean_md(toon['te_vermijden'])}")

    taal: dict = aanbevelingen.get("taal", {}) or {}
    beelden: dict = aanbevelingen.get("beelden", {}) or {}
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        toegankelijk: list = taal.get("toegankelijk", []) or []
        if toegankelijk:
            st.markdown("**Toegankelijke taal:**")
            _render_list(toegankelijk)
    with c2:
        uit_te_leggen: list = taal.get("uit_te_leggen", []) or []
        if uit_te_leggen:
            st.markdown("**Uit te leggen:**")
            _render_list(uit_te_leggen)
    with c3:
        werkend: list = beelden.get("werkend", []) or []
        if werkend:
            st.markdown("**Beelden die werken:**")
            _render_list(werkend)
    with c4:
        niet_werkend: list = beelden.get("niet_werkend", []) or []
        if niet_werkend:
            st.markdown("**Beelden die niet werken:**")
            _render_list(niet_werkend)

    balans: dict = aanbevelingen.get("balans", {}) or {}
    if balans:
        b1, b2 = st.columns(2)
        with b1:
            pp = balans.get("pastoraal_profetisch")
            if pp:
                st.info(f"**Balans pastoraal/profetisch:** {clean_md(pp)}")
        with b2:
            tv = balans.get("troost_vermaning")
            if tv:
                st.info(f"**Balans troost/vermaning:** {clean_md(tv)}")

    waarschuwingen: list = aanbevelingen.get("waarschuwingen", []) or []
    _render_waarschuwingen(waarschuwingen)
