from typing import Any

import streamlit as st

from src.utils.utils import clean_md

_V_LABELS = {
    "vragen": "Vragen",
    "verdriet": "Verdriet",
    "vreugden": "Vreugden",
    "visioenen": "Visioenen",
    "verlangens": "Verlangens",
    "zorgen": "Zorgen",
    "tradities": "Tradities",
    "onzekerheden": "Onzekerheden",
    "concrete_voorbeelden": "Concrete voorbeelden",
    "onvervulde_behoeften": "Onvervulde behoeften",
    "vieringen": "Vieringen",
    "zoektochten": "Zoektochten",
    "verloren_gegaan": "Verloren gegaan",
    "collectieve_dromen": "Collectieve dromen",
}


def _render_list(values: list) -> None:
    for item in values:
        st.markdown(f"- {clean_md(str(item))}")


def _render_vijf_vs(data: dict) -> None:
    """Render a vijf V's dict whose values are either strings or lists."""
    for key, label in _V_LABELS.items():
        v = data.get(key)
        if not v:
            continue
        with st.expander(label, expanded=False):
            if isinstance(v, list):
                _render_list(v)
            elif isinstance(v, dict):
                # Legacy nested format: may have a "beschrijving" string plus sub-lists
                if v.get("beschrijving"):
                    st.markdown(clean_md(v["beschrijving"]))
                for ek, items in v.items():
                    if ek != "beschrijving" and items:
                        st.markdown(f"*{ek.replace('_', ' ').capitalize()}:*")
                        if isinstance(items, list):
                            _render_list(items)
                        else:
                            st.markdown(clean_md(str(items)))
            else:
                st.markdown(clean_md(str(v)))


# Keep old names as aliases for backward compatibility
_render_vijf_vs_plaatsniveau = _render_vijf_vs
_render_vijf_vs_gemeenteniveau = _render_vijf_vs


def waardenorientatie(analysis: dict[str, Any]) -> None:
    """Render waardenorientatie analysis result."""
    result: dict[str, Any] = analysis.get("result", {})

    vijf_vs_plaats: dict = result.get("vijf_vs_plaatsniveau", {})
    vijf_vs_gemeente: dict = result.get("vijf_vs_gemeenteniveau", {})
    trendanalyse: dict = result.get("trendanalyse", {})
    milieus_plaats: dict = result.get("motivaction_milieus_plaatsniveau", {})
    milieus_gemeente: dict = result.get("motivaction_milieus_gemeenteniveau", {})
    homiletisch: dict = result.get("homiletische_implicaties", {})

    # ── Vijf V's plaatsniveau ─────────────────────────────────────────────────
    st.subheader("Vijf V's — Plaatsniveau")
    _render_vijf_vs_plaatsniveau(vijf_vs_plaats)

    st.divider()

    # ── Vijf V's gemeenteniveau ───────────────────────────────────────────────
    st.subheader("Vijf V's — Gemeenteniveau")
    _render_vijf_vs_gemeenteniveau(vijf_vs_gemeente)

    st.divider()

    # ── Trendanalyse ──────────────────────────────────────────────────────────
    with st.expander("Trendanalyse", expanded=False):
        mesotrends: list = trendanalyse.get("mesotrends_5_15_jaar", [])
        microtrends: list = trendanalyse.get("microtrends_1_5_jaar", [])

        if mesotrends:
            st.markdown("**Mesotrends (5-15 jaar)**")
            for t in mesotrends:
                with st.container(border=True):
                    st.markdown(f"**{t.get('trend', '')}**")
                    if t.get("impact_lokaal"):
                        st.markdown(f"*Lokale impact:* {clean_md(t['impact_lokaal'])}")
                    if t.get("relevantie_preek"):
                        st.markdown(f"*Relevantie preek:* {clean_md(t['relevantie_preek'])}")

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

    # ── Motivaction milieus plaatsniveau ──────────────────────────────────────
    with st.expander("Motivaction milieus — Plaatsniveau", expanded=False):
        aanwezig_plaats: list = milieus_plaats.get("waarschijnlijk_aanwezig", [])
        if aanwezig_plaats:
            cols = st.columns([2, 1, 3])
            cols[0].caption("Milieu")
            cols[1].caption("Geschat %")
            cols[2].caption("Kenmerken lokaal")
            for m in aanwezig_plaats:
                c1, c2, c3 = st.columns([2, 1, 3])
                c1.markdown(m.get("milieu", ""))
                c2.markdown(m.get("geschat_percentage", ""))
                c3.markdown(clean_md(m.get("kenmerken_lokaal", "")))

    st.divider()

    # ── Motivaction milieus gemeenteniveau ────────────────────────────────────
    with st.expander("Motivaction milieus — Gemeenteniveau", expanded=False):
        aanwezig_gemeente: list = milieus_gemeente.get("waarschijnlijk_aanwezig", [])
        if aanwezig_gemeente:
            for m in aanwezig_gemeente:
                with st.container(border=True):
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        st.markdown(f"**{m.get('milieu', '')}**")
                        if m.get("kenmerken_lokaal"):
                            st.markdown(clean_md(m["kenmerken_lokaal"]))
                    with c2:
                        if m.get("geschat_percentage"):
                            st.metric("Geschat %", m["geschat_percentage"])
                    taal: list = m.get("taal_die_resoneert", [])
                    beelden: list = m.get("beelden_die_werken", [])
                    if taal:
                        st.caption("Taal die resoneert: " + " · ".join(taal))
                    if beelden:
                        st.caption("Beelden die werken: " + " · ".join(beelden))

        spanningen: list = milieus_gemeente.get("spanningen_tussen_groepen", [])
        if spanningen:
            st.markdown("**Spanningen tussen groepen**")
            for s in spanningen:
                with st.container(border=True):
                    st.markdown(f"*{s.get('groep_a', '')}* vs *{s.get('groep_b', '')}*")
                    if s.get("spanningsveld"):
                        st.markdown(clean_md(s["spanningsveld"]))
                    if s.get("implicatie_preek"):
                        st.caption(f"Implicatie preek: {clean_md(s['implicatie_preek'])}")

    st.divider()

    # ── Homiletische implicaties ──────────────────────────────────────────────
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
