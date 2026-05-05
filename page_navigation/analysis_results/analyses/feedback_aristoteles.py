from typing import Any

import streamlit as st

from src.utils.utils import clean_md


_MODI = [
    ("logos",  "Logos",  "Rationele architectuur"),
    ("pathos", "Pathos", "Emotionele resonantie"),
    ("ethos",  "Ethos",  "Geloofwaardigheid"),
]

_ORTHO = [
    ("orthodoxie_logos",   "Orthodoxie (Logos)",  "Rechte leer"),
    ("orthopathie_pathos", "Orthopathie (Pathos)", "Rechte affectie"),
    ("orthopraxie_ethos",  "Orthopraxie (Ethos)", "Recht handelen"),
]


# Schaalsuffix '/10' weggelaten omdat 10 de standaardschaal is en
# de toevoeging in elke metric/badge dezelfde nutteloze ruis oplevert.
# Voeg pas een suffix (bv. '/5') toe wanneer de schaal écht afwijkt.
def _score_label(score) -> str:
    try:
        s = int(score)
        if s >= 8:
            color = "green"
        elif s >= 6:
            color = "blue"
        elif s >= 4:
            color = "orange"
        else:
            color = "red"
        return f":{color}[**{s}**]"
    except (TypeError, ValueError):
        return str(score) if score else "—"


def feedback_aristoteles(analysis: dict[str, Any]) -> None:
    """Renderer voor Aristoteles-feedback (Logos / Pathos / Ethos)."""
    result = analysis.get("result", {})
    if not isinstance(result, dict) or not result:
        st.info("Geen resultaat beschikbaar.")
        return

    totaal = result.get("totaalbeeld", {})
    modi = result.get("aristotelische_modi_analyse", {})
    balans = result.get("retorische_balans_analyse", {})
    ortho = result.get("orthodoxie_orthopathie_orthopraxie", {})

    # === 1. Totaalbeeld bovenaan ===
    overall = totaal.get("overall_retorische_score")
    stijl = totaal.get("primaire_retorische_stijl", "")
    doelgroep = totaal.get("doelgroep_analyse", "")

    cols = st.columns(3)
    with cols[0]:
        if overall is not None:
            # Geen st.metric — die schaalt de score naar een veel te grote
            # fontsize. Markdown houdt het compact en de gekleurde badge
            # blijft visueel herkenbaar.
            st.markdown(f"**Overall retorische score**  \n{_score_label(overall)}")
    with cols[1]:
        if stijl:
            st.markdown(f"**Retorische stijl**  \n{clean_md(stijl)}")
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

    aanbev = totaal.get("aanbevelingen_voor_volgende_preek", [])
    conclusie = totaal.get("conclusie", "")
    if aanbev:
        with st.expander("Aanbevelingen voor volgende preek", expanded=False):
            for a in aanbev:
                if a:
                    st.markdown(f"- {clean_md(str(a))}")
    if conclusie:
        with st.expander("Conclusie", expanded=False):
            st.markdown(clean_md(conclusie))

    st.divider()

    # === 2. Drie modi — scores naast elkaar ===
    st.markdown("### Aristotelische modi")
    score_cols = st.columns(3)
    for i, (key, label, _) in enumerate(_MODI):
        modus = modi.get(key, {})
        score = modus.get("score") if isinstance(modus, dict) else None
        with score_cols[i]:
            # Compactere weergave dan st.metric; gekleurde badge geeft
            # in één oogopslag aan of de score sterk of zwak is.
            st.markdown(f"**{label}**  \n{_score_label(score)}")

    for key, label, sublabel in _MODI:
        modus = modi.get(key, {})
        if not isinstance(modus, dict) or not modus:
            continue
        score = modus.get("score")
        with st.expander(f"{label} — {sublabel}  {_score_label(score)}", expanded=False):
            analyse = modus.get("analyse", "")
            if analyse:
                st.markdown(clean_md(analyse))

            diagnose = modus.get("specifieke_diagnose", "")
            if diagnose:
                st.caption(f"Kerndiagnose: {clean_md(diagnose)}")

            extra = modus.get("emotionele_toon") or modus.get("authenticiteit") or ""
            if extra:
                st.caption(clean_md(extra))

            quotes = modus.get("quotes", [])
            if quotes:
                st.markdown("**Quotes:**")
                for q in quotes:
                    if q:
                        st.markdown(f"> {clean_md(str(q))}")

            sterke = modus.get("sterke_punten", [])
            verbeter = modus.get("verbeterpunten", [])
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

    # === 3. Retorische balans ===
    if balans:
        st.divider()
        st.markdown("### Retorische balans")
        dominant = balans.get("dominante_modus", "")
        onderdrukt = balans.get("onderdrukte_modus", "")
        balans_score = balans.get("balans_score")
        col1, col2, col3 = st.columns(3)
        with col1:
            if dominant:
                st.markdown(f"**Sterkste modus**  \n{clean_md(dominant)}")
        with col2:
            if onderdrukt:
                st.markdown(f"**Zwakste modus**  \n{clean_md(onderdrukt)}")
        with col3:
            if balans_score is not None:
                st.markdown(f"**Balansscore**  \n{_score_label(balans_score)}")

        balans_analyse = balans.get("analyse", "")
        if balans_analyse:
            st.markdown(clean_md(balans_analyse))

        consequenties = balans.get("consequenties_van_onbalans", [])
        if consequenties:
            with st.expander("Consequenties van onbalans", expanded=False):
                for c in consequenties:
                    if c:
                        st.markdown(f"- {clean_md(str(c))}")

        aanbeveling = balans.get("aanbeveling_voor_balans", "")
        if aanbeveling:
            st.info(clean_md(aanbeveling))

    # === 4. Orthodoxie / Orthopathie / Orthopraxie ===
    if ortho:
        st.divider()
        st.markdown("### Orthodoxie · Orthopathie · Orthopraxie")
        o_cols = st.columns(3)
        for i, (key, label, sublabel) in enumerate(_ORTHO):
            blok = ortho.get(key, {})
            score = blok.get("score") if isinstance(blok, dict) else None
            with o_cols[i]:
                st.markdown(f"**{label}**  \n{_score_label(score)}")
        for key, label, sublabel in _ORTHO:
            blok = ortho.get(key, {})
            if not isinstance(blok, dict) or not blok:
                continue
            score = blok.get("score")
            analyse = blok.get("analyse", "")
            if analyse:
                with st.expander(f"{label}  {_score_label(score)}", expanded=False):
                    st.markdown(clean_md(analyse))

