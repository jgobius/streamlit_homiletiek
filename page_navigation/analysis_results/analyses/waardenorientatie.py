"""Renderer voor de Tavily-gedreven waardenoriëntatie-analyse.

Toont naast de Vijf V's en Motivaction-milieus (op zowel wijk- als
gemeente-niveau) ook de wijk-/kern-context, trendanalyse, homiletische
implicaties, bron-onderbouwing en een meta-sectie over bronkwaliteit.
Dit is een Verdieping-analyse, parallel aan `politieke_orientatie` en
`gemeente_spiritualiteit`, en gebruikt hetzelfde patroon (kwaliteit
bovenaan, bronnen onderaan) zodat de prediker alle drie de Verdieping-
rapporten op dezelfde manier kan lezen.
"""

from typing import Any

import streamlit as st

from src.utils.utils import clean_md


# Labels voor de Vijf V's. Volgorde bewust gekozen: visioenen-verlangens-
# vreugden-verdriet-vragen volgt de oorspronkelijke didactische volgorde
# van het Vijf-V's-model (eerst toekomst, dan heden, dan zoekvragen).
_V_LABELS: dict[str, str] = {
    "visioenen": "Visioenen",
    "verlangens": "Verlangens",
    "vreugden": "Vreugden",
    "verdriet": "Verdriet",
    "vragen": "Vragen",
}

# Sub-veld labels voor de geneste Vijf V's-dict-structuur. Het schema heeft
# per V een `beschrijving` plus een handvol concrete arrays (zorgen,
# tradities, onzekerheden, ...). Dit mapje zorgt voor leesbare kopjes
# zonder dat we per V een aparte handler hoeven te schrijven.
_V_SUBLABELS: dict[str, str] = {
    "concrete_voorbeelden": "Concrete voorbeelden",
    "onvervulde_behoeften": "Onvervulde behoeften",
    "tradities": "Tradities",
    "vieringen": "Vieringen",
    "zorgen": "Zorgen",
    "verloren_gegaan": "Verloren gegaan",
    "onzekerheden": "Onzekerheden",
    "zoektochten": "Zoektochten",
    "collectieve_dromen": "Collectieve dromen",
}


def _render_list(values: list) -> None:
    # Bullet-helper met clean_md; de caller is verantwoordelijk voor
    # leeg-checks zodat we geen lege bullet-blokken renderen.
    for item in values:
        if item:
            st.markdown(f"- {clean_md(str(item))}")


def _render_vijf_vs(data: dict) -> None:
    """Render een Vijf V's dict.

    Het Tavily-schema levert per V een dict met `beschrijving` + één of
    meerdere arrays (afhankelijk van de V). Voor robuustheid accepteren
    we ook losse strings of platte lijsten — dat dekt zowel toekomstige
    schema-aanpassingen als een eventueel ouder formaat.
    """
    for key, label in _V_LABELS.items():
        v = data.get(key)
        if not v:
            continue
        with st.expander(label, expanded=False):
            if isinstance(v, dict):
                # Beschrijving eerst (vrije tekst), daarna gestructureerde
                # sub-arrays met leesbare kopjes uit `_V_SUBLABELS`.
                if v.get("beschrijving"):
                    st.markdown(clean_md(v["beschrijving"]))
                for sub_key, items in v.items():
                    if sub_key == "beschrijving" or not items:
                        continue
                    sub_label = _V_SUBLABELS.get(
                        sub_key, sub_key.replace("_", " ").capitalize()
                    )
                    st.markdown(f"*{sub_label}:*")
                    if isinstance(items, list):
                        _render_list(items)
                    else:
                        st.markdown(clean_md(str(items)))
            elif isinstance(v, list):
                _render_list(v)
            else:
                st.markdown(clean_md(str(v)))


def waardenorientatie(analysis: dict[str, Any]) -> None:
    """Render waardenoriëntatie-analyse resultaat (Tavily Verdieping-versie)."""
    result: dict[str, Any] = analysis.get("result", {})

    church_name: str = st.session_state.get("church_name", "")
    church_place: str = st.session_state.get("church_place", "")
    if church_place or church_name:
        # Korte herinnering bovenaan: deze analyse draait om déze gemeente
        # op dit adres, niet om een generiek plaatsprofiel.
        delen: list[str] = []
        if church_name:
            delen.append(f"**Gemeente:** {church_name}")
        if church_place:
            delen.append(f"**Plaats:** {church_place}")
        st.caption(" · ".join(delen))

    lokale_context: dict = result.get("lokale_context", {}) or {}
    vijf_vs_wijk: dict = result.get("vijf_vs_wijk", {}) or {}
    vijf_vs_gemeente: dict = result.get("vijf_vs_gemeente", {}) or {}
    milieus_wijk: dict = result.get("motivaction_milieus_wijk", {}) or {}
    milieus_gemeente: dict = result.get("motivaction_milieus_gemeente", {}) or {}
    trendanalyse: dict = result.get("trendanalyse", {}) or {}
    homiletisch: dict = result.get("homiletische_implicaties", {}) or {}
    bronnen: list = result.get("bronnen", []) or []
    bronnen_kwaliteit: dict = result.get("bronnen_kwaliteit", {}) or {}

    # Bronnen-kwaliteit bovenaan: de prediker moet vóór hij percentages
    # leest weten op welk niveau (wijk/kern/gemeente) de analyse daadwerkelijk
    # betrouwbaar is. Zonder dit risico je dat een gemeente-totaal wordt
    # aangezien voor een wijk-profiel — precies de fout die dit prompt
    # probeert te voorkomen.
    _render_bronnen_kwaliteit(bronnen_kwaliteit, aantal_bronnen=len(bronnen))

    # Lokale context meteen daarna — welk wijk/kern-profiel ligt onder dit
    # waardenprofiel? In grote steden is dit het verschil tussen een bruikbaar
    # en een misleidend beeld.
    _render_lokale_context(lokale_context)

    # ── Vijf V's wijk/kern ────────────────────────────────────────────────
    wijk_naam: str = lokale_context.get("wijk_of_kern", "") or church_place
    plaats_label = (
        f"Vijf V's — wijk/kern ({wijk_naam})"
        if wijk_naam
        else "Vijf V's — wijk/kern"
    )
    st.subheader(plaats_label)
    _render_vijf_vs(vijf_vs_wijk)

    # ── Motivaction-milieus wijk ──────────────────────────────────────────
    with st.expander("Motivaction-milieus — wijk/kern", expanded=False):
        aanwezig_wijk: list = milieus_wijk.get("waarschijnlijk_aanwezig", [])
        if aanwezig_wijk:
            cols = st.columns([2, 1, 3])
            cols[0].caption("Milieu")
            cols[1].caption("Geschat %")
            cols[2].caption("Kenmerken lokaal")
            for m in aanwezig_wijk:
                c1, c2, c3 = st.columns([2, 1, 3])
                c1.markdown(f"**{m.get('milieu', '')}**")
                pct = m.get("geschat_percentage")
                # null is een geldige waarde uit het schema (geen bron) —
                # toon een streepje zodat de prediker direct ziet dat hier
                # geen percentage met bron beschikbaar was.
                c2.markdown(pct if pct else "—")
                c3.markdown(clean_md(m.get("kenmerken_lokaal", "")))
        else:
            st.caption("Geen milieus gerapporteerd op wijk/kern-niveau.")

    st.divider()

    # ── Vijf V's gemeente ─────────────────────────────────────────────────
    gemeente_label = (
        f"Vijf V's — kerkelijke gemeente ({church_name})"
        if church_name
        else "Vijf V's — kerkelijke gemeente"
    )
    st.subheader(gemeente_label)
    _render_vijf_vs(vijf_vs_gemeente)

    # ── Motivaction-milieus gemeente ──────────────────────────────────────
    with st.expander("Motivaction-milieus — gemeente", expanded=False):
        aanwezig_gemeente: list = milieus_gemeente.get(
            "waarschijnlijk_aanwezig", []
        )
        if aanwezig_gemeente:
            for m in aanwezig_gemeente:
                with st.container(border=True):
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        st.markdown(f"**{m.get('milieu', '')}**")
                        if m.get("kenmerken_lokaal"):
                            st.markdown(clean_md(m["kenmerken_lokaal"]))
                    with c2:
                        pct = m.get("geschat_percentage")
                        if pct:
                            st.metric("Geschat %", pct)
                    taal: list = m.get("taal_die_resoneert", [])
                    beelden: list = m.get("beelden_die_werken", [])
                    if taal:
                        st.caption(
                            "Taal die resoneert: " + " · ".join(taal)
                        )
                    if beelden:
                        st.caption(
                            "Beelden die werken: " + " · ".join(beelden)
                        )

        spanningen: list = milieus_gemeente.get(
            "spanningen_tussen_groepen", []
        )
        if spanningen:
            st.markdown("**Spanningen tussen groepen**")
            for s in spanningen:
                with st.container(border=True):
                    st.markdown(
                        f"*{s.get('groep_a', '')}* vs *{s.get('groep_b', '')}*"
                    )
                    if s.get("spanningsveld"):
                        st.markdown(clean_md(s["spanningsveld"]))
                    if s.get("implicatie_preek"):
                        st.caption(
                            f"Implicatie preek: {clean_md(s['implicatie_preek'])}"
                        )

    st.divider()

    # ── Trendanalyse ──────────────────────────────────────────────────────
    with st.expander("Trendanalyse", expanded=False):
        mesotrends: list = trendanalyse.get("mesotrends_5_15_jaar", [])
        microtrends: list = trendanalyse.get("microtrends_1_5_jaar", [])

        if mesotrends:
            st.markdown("**Mesotrends (5-15 jaar)**")
            for t in mesotrends:
                with st.container(border=True):
                    st.markdown(f"**{t.get('trend', '')}**")
                    if t.get("impact_lokaal"):
                        st.markdown(
                            f"*Lokale impact:* {clean_md(t['impact_lokaal'])}"
                        )
                    if t.get("relevantie_preek"):
                        st.markdown(
                            f"*Relevantie preek:* {clean_md(t['relevantie_preek'])}"
                        )

        if microtrends:
            st.markdown("**Microtrends (1-5 jaar)**")
            for t in microtrends:
                with st.container(border=True):
                    st.markdown(f"**{t.get('trend', '')}**")
                    if t.get("actueel_voor_datum"):
                        st.caption(f"Actueel voor: {t['actueel_voor_datum']}")
                    if t.get("lokale_uitwerking"):
                        st.markdown(clean_md(t["lokale_uitwerking"]))

    st.divider()

    # ── Homiletische implicaties ──────────────────────────────────────────
    st.subheader("Homiletische implicaties")
    if homiletisch.get("aanbevolen_taalveld"):
        st.success(clean_md(homiletisch["aanbevolen_taalveld"]))

    c1, c2 = st.columns(2)
    with c1:
        kansrijke: list = homiletisch.get("kansrijke_beelden", [])
        if kansrijke:
            st.markdown("**Kansrijke beelden:**")
            _render_list(kansrijke)
    with c2:
        te_vermijden: list = homiletisch.get("te_vermijden", [])
        if te_vermijden:
            st.markdown("**Te vermijden:**")
            _render_list(te_vermijden)

    st.divider()

    # ── Bronnen — klikbaar, per claim. ────────────────────────────────────
    _render_bronnen(bronnen)


def _render_lokale_context(lokale_context: dict) -> None:
    """Toon wijk-/kern-context bovenaan zodat het analyse-niveau duidelijk is.

    In grote steden (Den Haag, Rotterdam, Amsterdam, maar ook Katwijk) is
    het verschil tussen wijken vaak groter dan het verschil tussen plaatsen
    onderling. De prediker moet direct zien op welke schaal hij naar de
    Vijf V's en Motivaction-milieus kijkt — gemeente-totalen kunnen anders
    misleidend zijn.
    """
    if not lokale_context:
        return

    niveau = lokale_context.get("analyse_niveau", "")
    wijk = lokale_context.get("wijk_of_kern", "")
    postcode = lokale_context.get("postcodegebied", "")
    profiel = lokale_context.get("wijkprofiel", "")
    waarom = lokale_context.get("waarom_deze_schaal", "")

    # Kopregel met badge-achtige labels — in één oogopslag zie je het niveau
    # en de locatie waarop de rest van het rapport gebaseerd is.
    labelparts: list[str] = []
    if niveau:
        labelparts.append(f"**Niveau:** {clean_md(niveau)}")
    if wijk:
        labelparts.append(f"**Wijk / kern:** {clean_md(wijk)}")
    if postcode:
        labelparts.append(f"**Postcode:** {clean_md(postcode)}")
    if labelparts:
        st.markdown(" · ".join(labelparts))

    if profiel:
        st.info(clean_md(profiel))
    if waarom:
        st.caption(f"*Waarom dit niveau:* {clean_md(waarom)}")

    st.divider()


def _render_bronnen_kwaliteit(
    bronnen_kwaliteit: dict, *, aantal_bronnen: int
) -> None:
    """Toon compacte meta-indicatie van bronbetrouwbaarheid bovenaan.

    Het `aantal_bronnen`-argument komt uit de lengte van `result["bronnen"]`;
    we vertrouwen niet blind op een eventueel `aantal_bronnen`-veld in het
    schema want een LLM kan dat veld vergeten bijwerken — zelf tellen is
    autoritatief.
    """
    if not bronnen_kwaliteit:
        return

    niveau_bereikt: str = bronnen_kwaliteit.get("analyse_niveau_bereikt", "")
    differentiatie: str = bronnen_kwaliteit.get(
        "wijkdifferentiatie_geslaagd", ""
    )

    c1, c2, c3 = st.columns([1, 2, 2])
    with c1:
        st.metric("Bronnen", aantal_bronnen)
    with c2:
        st.markdown("**Niveau bereikt**")
        st.markdown(clean_md(niveau_bereikt) if niveau_bereikt else "_onbekend_")
    with c3:
        st.markdown("**Wijkdifferentiatie**")
        st.markdown(
            clean_md(differentiatie) if differentiatie else "_onbekend_"
        )

    ontbreekt: list = bronnen_kwaliteit.get("onderbouwing_ontbreekt", []) or []
    if ontbreekt:
        with st.expander(
            f"⚠ Onderbouwing ontbreekt voor {len(ontbreekt)} veld(en)",
            expanded=False,
        ):
            # Uitleg vóór de lijst: zonder deze context is het label voor de
            # prediker onduidelijk. Geen actie vereist, maar wees voorzichtig
            # met deze specifieke claims in de preek.
            st.caption(
                "Voor deze onderdelen vond de analyse geen expliciete bron. "
                "De inhoud kan nog steeds bruikbaar zijn, maar is speculatiever — "
                "gebruik deze claims niet als harde feiten."
            )
            for dotpad in ontbreekt:
                st.markdown(f"- `{clean_md(str(dotpad))}`")

    st.divider()


def _render_bronnen(bronnen: list) -> None:
    """Toon klikbare bronnen met citaat en claim-verwijzing.

    Sortering op claim_id zodat bronnen die hetzelfde veld onderbouwen
    bij elkaar blijven staan — dat helpt de prediker snel te zien hoeveel
    bronnen er voor een specifieke claim zijn.
    """
    if not bronnen:
        st.caption(
            "Geen bronnen geleverd door de analyse — inhoudelijke claims zijn dan speculatiever."
        )
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
