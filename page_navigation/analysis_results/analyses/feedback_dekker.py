from typing import Any

import streamlit as st

from src.utils.utils import clean_md


_CRITERIA = [
    ("1_specifiek_bijbelgedeelte",           "1. Specifiek bijbelgedeelte"),
    ("2_exegese_oorspronkelijke_context",    "2. Exegese — oorspronkelijke context"),
    ("3_toepassing_concreet_actueel",        "3. Toepassing — concreet en actueel"),
    ("4_verwevenheid_uitleg_toepassing",     "4. Verwevenheid uitleg en toepassing"),
    ("5_drie_stukken_ellende_verlossing_dankbaarheid", "5. Drie stukken — ellende, verlossing, dankbaarheid"),
    ("6_twee_wegen_ernst_van_keuze",         "6. Twee wegen — ernst van de keuze"),
    ("7_christocentrisch_genade",            "7. Christocentrisch — genade"),
    ("8_diepgang_en_lengte",                 "8. Diepgang en lengte"),
]


def _score_color(score) -> str:
    try:
        s = int(score)
        if s >= 8:
            return "green"
        elif s >= 6:
            return "blue"
        elif s >= 4:
            return "orange"
        else:
            return "red"
    except (TypeError, ValueError):
        return "gray"


def _score_label(score) -> str:
    try:
        s = int(score)
        color = _score_color(s)
        return f":{color}[{s}/10]"
    except (TypeError, ValueError):
        return str(score) if score else "—"


def feedback_dekker(analysis: dict[str, Any]) -> None:
    """Renderer voor Dekker-feedback (8 thesen)."""
    result = analysis.get("result", {})
    if not isinstance(result, dict) or not result:
        st.info("Geen resultaat beschikbaar.")
        return

    criteria = result.get("analyse_per_criterium", {})
    algeheel = result.get("algehele_beoordeling", {})

    # === 1. Algehele beoordeling bovenaan ===
    eindoordeel = algeheel.get("eindoordeel_volgens_dekker", "")
    if eindoordeel:
        st.info(clean_md(eindoordeel))

    samenvatting = algeheel.get("samenvatting", "")
    if samenvatting:
        st.markdown(clean_md(samenvatting))

    sterke = algeheel.get("sterke_punten", [])
    zwakke = algeheel.get("zwakke_punten", [])
    if sterke or zwakke:
        col_s, col_z = st.columns(2)
        with col_s:
            if sterke:
                st.markdown("**Sterke punten**")
                for p in sterke:
                    if p:
                        st.success(f"+ {clean_md(str(p))}")
        with col_z:
            if zwakke:
                st.markdown("**Zwakke punten**")
                for p in zwakke:
                    if p:
                        st.warning(f"△ {clean_md(str(p))}")

    st.divider()

    # === 2. Scoregrid — 8 criteria als 4×2 metrics ===
    st.markdown("### Analyse per criterium")

    scores = []
    for key, label in _CRITERIA:
        blok = criteria.get(key, {})
        score = blok.get("score_1_tot_10") if isinstance(blok, dict) else None
        scores.append((key, label, score, blok))

    col_rows = [st.columns(4), st.columns(4)]
    for i, (key, label, score, blok) in enumerate(scores):
        row = col_rows[i // 4]
        with row[i % 4]:
            try:
                score_val = f"{int(score)}/10" if score is not None else "—"
            except (TypeError, ValueError):
                score_val = "—"
            short = label.split("—")[0].strip() if "—" in label else label
            st.metric(short, score_val)

    # === 3. Detail per criterium ===
    for key, label, score, blok in scores:
        if not isinstance(blok, dict) or not blok:
            continue
        with st.expander(f"{label}  {_score_label(score)}", expanded=False):
            bevindingen = blok.get("bevindingen", "")
            if bevindingen:
                st.markdown(clean_md(bevindingen))

            quotes = blok.get("quotes", [])
            if quotes:
                st.markdown("**Quotes:**")
                for q in quotes:
                    if q:
                        st.markdown(f"> {clean_md(str(q))}")

            verbeterpunt = blok.get("verbeterpunt", "")
            if verbeterpunt:
                st.warning(f"△ {clean_md(verbeterpunt)}")
