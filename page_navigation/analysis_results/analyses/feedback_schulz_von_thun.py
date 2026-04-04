from typing import Any

import streamlit as st

from src.utils.utils import clean_md


_ZIJDEN = [
    ("zakelijk_inhoud_blauw",   "Blauw — Zakelijke inhoud",  ["verstandelijkheid_check"]),
    ("zelf_onthulling_groen",   "Groen — Zelf-onthulling",   ["riemann_type_diagnose", "diaconale_kwaliteit"]),
    ("relatie_aspect_geel",     "Geel — Relationeel aspect", ["betrekkingsruis_check", "houding_indicatie"]),
    ("appel_aspect_rood",       "Rood — Appel",              ["zuspruch_vs_anspruch_balans", "risico_op_moralisme"]),
]

_OOR_LABELS = [
    ("het_zakelijk_oor_hoort",       "Zakelijk oor"),
    ("het_relatie_oor_hoort",        "Relatie-oor"),
    ("het_appel_oor_hoort",          "Appel-oor"),
    ("het_zelfonthulling_oor_hoort", "Zelfonthulling-oor"),
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


def _render_zijde(label: str, blok: dict, extra_keys: list[str]) -> None:
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


def feedback_schulz_von_thun(analysis: dict[str, Any]) -> None:
    """Renderer voor Schulz von Thun vierkantenmodel feedback."""
    result = analysis.get("result", {})
    if not isinstance(result, dict) or not result:
        st.info("Geen resultaat beschikbaar.")
        return

    totaal = result.get("totaalbeeld", {})
    analyse_blok = result.get("schulz_von_thun_analyse", {})
    congruentie = result.get("congruentie_en_storingen", {})
    receptie = result.get("receptie_simulatie", {})
    meta = result.get("metadata", {})

    # === 1. Totaaloverzicht ===
    overall = totaal.get("overall_communicatie_score")
    waarschuwing = totaal.get("barthiaanse_waarschuwing", "")
    col_score, col_warn = st.columns([1, 3])
    with col_score:
        if overall is not None:
            st.metric("Overall communicatiescore", _score_val(overall))
    with col_warn:
        if waarschuwing:
            st.caption(f"Barthiaanse waarschuwing: {clean_md(waarschuwing)}")

    samenvatting = totaal.get("samenvatting", "")
    if samenvatting:
        st.info(clean_md(samenvatting))

    sterke_top = totaal.get("top_3_sterke_punten", [])
    verbeter_top = totaal.get("top_3_verbeterpunten", [])
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

    conclusie = totaal.get("conclusie", "")
    if conclusie:
        with st.expander("Conclusie", expanded=False):
            st.markdown(clean_md(conclusie))

    st.divider()

    # === 2. Vier zijden — scores naast elkaar ===
    st.markdown("### Vier zijden")
    score_cols = st.columns(4)
    for i, (key, label, _) in enumerate(_ZIJDEN):
        blok = analyse_blok.get(key, {}) if isinstance(analyse_blok, dict) else {}
        score = blok.get("score") if isinstance(blok, dict) else None
        kleur = label.split("—")[0].strip()
        with score_cols[i]:
            st.metric(kleur, _score_val(score))

    for key, label, extra_keys in _ZIJDEN:
        blok = analyse_blok.get(key, {}) if isinstance(analyse_blok, dict) else {}
        if blok:
            _render_zijde(label, blok, extra_keys)

    # === 3. Congruentie en storingen ===
    if congruentie:
        st.divider()
        st.markdown("### Congruentie en storingen")
        dominant = congruentie.get("dominante_zijde", "")
        oordeel = congruentie.get("congruentie_oordeel", "")
        if dominant or oordeel:
            col1, col2 = st.columns(2)
            with col1:
                if dominant:
                    st.markdown(f"**Dominante zijde:** {clean_md(dominant)}")
            with col2:
                if oordeel:
                    st.markdown(clean_md(oordeel))
        for k in ["storingen", "heilzame_storing"]:
            v = congruentie.get(k, "")
            if v:
                k_label = k.replace("_", " ").capitalize()
                st.markdown(f"**{k_label}:** {clean_md(str(v))}")

    # === 4. Receptie — vier oren ===
    if receptie:
        st.divider()
        st.markdown("### Receptie — vier oren")
        for key, label in _OOR_LABELS:
            v = receptie.get(key, "")
            if v:
                with st.expander(label, expanded=False):
                    st.markdown(clean_md(str(v)))

    # === 5. Metadata ===
    if meta:
        with st.expander("Metadata", expanded=False):
            for k, v in meta.items():
                if v:
                    st.markdown(f"**{k.replace('_', ' ').capitalize()}:** {clean_md(str(v))}")
