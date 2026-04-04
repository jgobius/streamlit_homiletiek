from typing import Any

import streamlit as st

from src.utils.utils import clean_md


_DOMEIN_A = [
    ("criterium_a1_beeldend_taalgebruik",      "A1 — Beeldend taalgebruik",    ["show_vs_tell_balans"]),
    ("criterium_a2_zorgvuldigheid_en_precisie", "A2 — Zorgvuldigheid & precisie", ["jargon_analyse"]),
    ("criterium_a3_muzikaliteit_en_ritme",      "A3 — Muzikaliteit & ritme",    ["papieren_taal_diagnose"]),
]

_DOMEIN_B = [
    ("criterium_b1_narratieve_spanningsboog",    "B1 — Narratieve spanningsboog",    ["plot_diagnose"]),
    ("criterium_b2_integratie_tekst_en_context", "B2 — Integratie tekst & context",  ["reframing_aanwezig"]),
    ("criterium_b3_openheid_vs_geslotenheid",    "B3 — Openheid vs. geslotenheid",   ["open_kunstwerk_diagnose"]),
]


def _score_label(score) -> str:
    try:
        s = int(score)
        if s >= 8:
            return f":green[{s}/10]"
        elif s >= 6:
            return f":blue[{s}/10]"
        elif s >= 4:
            return f":orange[{s}/10]"
        else:
            return f":red[{s}/10]"
    except (TypeError, ValueError):
        return str(score) if score else "—"


def _score_val(score) -> str:
    try:
        return f"{int(score)}/10" if score is not None else "—"
    except (TypeError, ValueError):
        return "—"


def _render_criterium(label: str, blok: dict, extra_keys: list[str]) -> None:
    if not isinstance(blok, dict):
        return
    score = blok.get("score")
    with st.expander(f"{label}  {_score_label(score)}", expanded=False):
        analyse = blok.get("analyse", "")
        if analyse:
            st.markdown(clean_md(analyse))
        for ek in extra_keys:
            v = blok.get(ek, "")
            if v:
                k_label = ek.replace("_", " ").capitalize()
                st.caption(f"**{k_label}:** {clean_md(str(v))}")
        quotes = blok.get("quotes", [])
        if quotes:
            st.markdown("**Quotes:**")
            for q in quotes:
                if q:
                    st.markdown(f"> {clean_md(str(q))}")
        sterke = blok.get("sterke_punten", [])
        verbeter = blok.get("verbeterpunten", [])
        col1, col2 = st.columns(2)
        with col1:
            if sterke:
                st.markdown("**Sterk:**")
                for p in sterke:
                    if p:
                        st.success(f"+ {clean_md(str(p))}")
        with col2:
            if verbeter:
                st.markdown("**Verbeteren:**")
                for p in verbeter:
                    if p:
                        st.warning(f"△ {clean_md(str(p))}")


def feedback_esthetiek(analysis: dict[str, Any]) -> None:
    """Renderer voor homiletische esthetiek feedback (Cilliers, Stark, Wilson)."""
    result = analysis.get("result", {})
    if not isinstance(result, dict) or not result:
        st.info("Geen resultaat beschikbaar.")
        return

    totaal = result.get("totaalbeeld_esthetiek", {})
    domein_a = result.get("domein_a_poetica_van_de_taal", {})
    domein_b = result.get("domein_b_dramaturgie_van_de_structuur", {})
    kitsch = result.get("kitsch_diagnose", {})
    ruimte = result.get("ruimte_voor_genade_analyse", {})
    meta = result.get("metadata", {})

    # === 1. Totaaloverzicht ===
    overall = totaal.get("overall_esthetische_score")
    stijl = totaal.get("primaire_esthetische_stijl", "")
    doelgroep = totaal.get("doelgroep_analyse", "")

    cols = st.columns(3)
    with cols[0]:
        if overall is not None:
            st.metric("Overall esthetische score", _score_val(overall))
    with cols[1]:
        if stijl:
            st.markdown(f"**Esthetische stijl**  \n{clean_md(stijl)}")
    with cols[2]:
        if doelgroep:
            st.markdown(f"**Doelgroep**  \n{clean_md(doelgroep)}")

    samenvatting = totaal.get("samenvatting", "")
    if samenvatting:
        st.info(clean_md(samenvatting))

    sterke_top = totaal.get("sterke_punten_top_3", [])
    verbeter_top = totaal.get("verbeterpunten_top_3", [])
    if sterke_top or verbeter_top:
        col_s, col_v = st.columns(2)
        with col_s:
            if sterke_top:
                st.markdown("**Sterke punten**")
                for p in sterke_top:
                    if p:
                        st.success(f"+ {clean_md(str(p))}")
        with col_v:
            if verbeter_top:
                st.markdown("**Verbeterpunten**")
                for p in verbeter_top:
                    if p:
                        st.warning(f"△ {clean_md(str(p))}")

    vergelijking = totaal.get("vergelijking_met_specialisten", "")
    if vergelijking:
        st.caption(f"Verwantschap: {clean_md(vergelijking)}")

    aanbev = totaal.get("aanbevelingen_voor_volgende_preek", [])
    if aanbev:
        with st.expander("Aanbevelingen voor volgende preek", expanded=False):
            for a in aanbev:
                if a:
                    st.markdown(f"- {clean_md(str(a))}")

    conclusie = totaal.get("conclusie", "")
    if conclusie:
        with st.expander("Conclusie", expanded=False):
            st.markdown(clean_md(conclusie))

    st.divider()

    # === 2. Domein A — Poëtica van de taal ===
    if domein_a:
        st.markdown("### Domein A — Poëtica van de taal")
        samenvatting_a = domein_a.get("samenvatting_taal", "")
        score_cols = st.columns(3)
        for i, (key, label, _) in enumerate(_DOMEIN_A):
            blok = domein_a.get(key, {})
            score = blok.get("score") if isinstance(blok, dict) else None
            afk = label.split("—")[0].strip()
            with score_cols[i]:
                st.metric(afk, _score_val(score))
        if samenvatting_a:
            st.caption(clean_md(samenvatting_a))
        for key, label, extra_keys in _DOMEIN_A:
            blok = domein_a.get(key, {})
            if blok:
                _render_criterium(label, blok, extra_keys)

    # === 3. Domein B — Dramaturgie van de structuur ===
    if domein_b:
        st.markdown("### Domein B — Dramaturgie van de structuur")
        samenvatting_b = domein_b.get("samenvatting_structuur", "")
        score_cols = st.columns(3)
        for i, (key, label, _) in enumerate(_DOMEIN_B):
            blok = domein_b.get(key, {})
            score = blok.get("score") if isinstance(blok, dict) else None
            afk = label.split("—")[0].strip()
            with score_cols[i]:
                st.metric(afk, _score_val(score))
        if samenvatting_b:
            st.caption(clean_md(samenvatting_b))
        for key, label, extra_keys in _DOMEIN_B:
            blok = domein_b.get(key, {})
            if blok:
                _render_criterium(label, blok, extra_keys)

    # === 4. Kitsch-diagnose ===
    if kitsch:
        st.divider()
        st.markdown("### Kitsch-diagnose")
        kitsch_score = kitsch.get("anti_kitsch_score")
        if kitsch_score is not None:
            st.metric("Anti-kitsch score", _score_val(kitsch_score))
        kitsch_analyse = kitsch.get("analyse", "")
        if kitsch_analyse:
            st.markdown(clean_md(kitsch_analyse))
        kitsch_voorbeelden = kitsch.get("voorbeelden_van_kitsch", [])
        authentiek = kitsch.get("authentieke_momenten", [])
        if kitsch_voorbeelden or authentiek:
            col_k, col_a = st.columns(2)
            with col_k:
                if kitsch_voorbeelden:
                    st.markdown("**Kitsch-voorbeelden:**")
                    for v in kitsch_voorbeelden:
                        if v:
                            st.warning(f"△ {clean_md(str(v))}")
            with col_a:
                if authentiek:
                    st.markdown("**Authentieke momenten:**")
                    for v in authentiek:
                        if v:
                            st.success(f"+ {clean_md(str(v))}")
        kitsch_aanbev = kitsch.get("aanbeveling", "")
        if kitsch_aanbev:
            st.caption(f"Aanbeveling: {clean_md(kitsch_aanbev)}")

    # === 5. Ruimte voor genade (Cilliers) ===
    if ruimte:
        st.divider()
        st.markdown("### Ruimte voor genade (Cilliers)")
        ruimte_score = ruimte.get("ruimte_score")
        if ruimte_score is not None:
            st.metric("Ruimte-score", _score_val(ruimte_score))
        ruimte_analyse = ruimte.get("analyse", "")
        if ruimte_analyse:
            st.markdown(clean_md(ruimte_analyse))
        for k in ["spanning_uitgehouden", "mysterie_gerespecteerd", "moralisering_vs_genade"]:
            v = ruimte.get(k, "")
            if v:
                k_label = k.replace("_", " ").capitalize()
                st.caption(f"**{k_label}:** {clean_md(str(v))}")
        ruimte_aanbev = ruimte.get("aanbeveling", "")
        if ruimte_aanbev:
            with st.expander("Aanbeveling", expanded=False):
                st.markdown(clean_md(ruimte_aanbev))

    # === 6. Metadata ===
    if meta:
        with st.expander("Metadata", expanded=False):
            for k, v in meta.items():
                if v:
                    st.markdown(f"**{k.replace('_', ' ').capitalize()}:** {clean_md(str(v))}")
