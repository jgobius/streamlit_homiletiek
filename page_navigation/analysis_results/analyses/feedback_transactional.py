from typing import Any

import streamlit as st

from src.utils.utils import clean_md


# Schaalsuffix '/10' weggelaten omdat 10 de standaardschaal is.
# Voeg een suffix pas toe wanneer de schaal écht afwijkt (bv. '/5').
def _score_label(score) -> str:
    try:
        s = int(score)
        if s >= 8:
            return f":green[**{s}**]"
        elif s >= 6:
            return f":blue[**{s}**]"
        elif s >= 4:
            return f":orange[**{s}**]"
        else:
            return f":red[**{s}**]"
    except (TypeError, ValueError):
        return str(score) if score else "—"


def _render_ego_blok(label: str, blok: dict, extra_keys: list[str] | None = None) -> None:
    if not isinstance(blok, dict):
        return
    score = blok.get("score")
    with st.expander(f"{label}  {_score_label(score)}", expanded=False):
        analyse = blok.get("analyse", "")
        if analyse:
            st.markdown(clean_md(analyse))
        for ek in (extra_keys or []):
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


def feedback_transactional(analysis: dict[str, Any]) -> None:
    """Renderer voor Transactionele Analyse feedback (Berne/Karpman)."""
    result = analysis.get("result", {})
    if not isinstance(result, dict) or not result:
        st.info("Geen resultaat beschikbaar.")
        return

    conclusie = result.get("conclusie_en_aanbeveling", {})
    ego = result.get("ego_posities_scan", {})
    transactie = result.get("transactie_analyse", {})
    spelen = result.get("spel_analyse_games", {})
    drama = result.get("dramadriehoek_analyse", {})

    # === 1. Totaaloverzicht ===
    overall = conclusie.get("psychologische_gezondheid_score")
    if overall is not None:
        # Compactere weergave dan st.metric — gekleurde badge laat
        # in één oogopslag zien of de score sterk of zwak is.
        st.markdown(f"**Psychologische gezondheid**  \n{_score_label(overall)}")

    samenvatting = conclusie.get("samenvatting", "")
    if samenvatting:
        st.info(clean_md(samenvatting))

    sterke = conclusie.get("sterke_punten", [])
    verbeter = conclusie.get("verbeterpunten", [])
    if sterke or verbeter:
        col_s, col_v = st.columns(2)
        with col_s:
            if sterke:
                st.markdown("**Sterke punten**")
                for p in sterke:
                    if p:
                        st.success(f"+ {clean_md(str(p))}")
        with col_v:
            if verbeter:
                st.markdown("**Verbeterpunten**")
                for p in verbeter:
                    if p:
                        st.warning(f"△ {clean_md(str(p))}")

    advies = conclusie.get("advies_voor_game_vrije_communicatie", "")
    if advies:
        with st.expander("Advies voor game-vrije communicatie", expanded=False):
            st.markdown(clean_md(advies))

    st.divider()

    # === 2. Ego-posities — scores naast elkaar ===
    st.markdown("### Ego-posities")

    ouder = ego.get("ouder_parent", {}) if isinstance(ego, dict) else {}
    cp_blok = ouder.get("vrijheid_van_kritische_ouder_CP", {}) if isinstance(ouder, dict) else {}
    np_blok = ouder.get("gezonde_zorg_NP", {}) if isinstance(ouder, dict) else {}
    adult_blok = ego.get("volwassene_adult", {}) if isinstance(ego, dict) else {}
    kind = ego.get("kind_child", {}) if isinstance(ego, dict) else {}
    ac_blok = kind.get("vrijheid_van_aangepast_kind_AC", {}) if isinstance(kind, dict) else {}
    fc_blok = kind.get("vrij_kind_FC", {}) if isinstance(kind, dict) else {}

    scores_matrix = [
        ("CP", cp_blok.get("score") if isinstance(cp_blok, dict) else None),
        ("NP", np_blok.get("score") if isinstance(np_blok, dict) else None),
        ("A",  adult_blok.get("score") if isinstance(adult_blok, dict) else None),
        ("AC", ac_blok.get("score") if isinstance(ac_blok, dict) else None),
        ("FC", fc_blok.get("score") if isinstance(fc_blok, dict) else None),
    ]
    score_cols = st.columns(5)
    for i, (afk, score) in enumerate(scores_matrix):
        with score_cols[i]:
            st.markdown(f"**{afk}**  \n{_score_label(score)}")

    dominante = ego.get("dominante_ego_positie", "") if isinstance(ego, dict) else ""
    if dominante:
        st.caption(f"Dominante positie: **{clean_md(dominante)}**")

    _render_ego_blok("Kritische Ouder (CP) — vrijheid van dwang", cp_blok,
                     ["toelichting_score", "aanwezigheid_van_dwang"])
    _render_ego_blok("Voedende Ouder (NP) — gezonde zorg", np_blok,
                     ["toelichting_score", "aanwezigheid"])
    _render_ego_blok("Volwassene (A)", adult_blok,
                     ["toelichting_score", "aanwezigheid"])
    _render_ego_blok("Aangepast Kind (AC) — vrijheid van aanpassing", ac_blok,
                     ["toelichting_score", "aanwezigheid_van_aanpassing"])
    _render_ego_blok("Vrij Kind (FC)", fc_blok,
                     ["toelichting_score", "aanwezigheid"])

    # === 3. Transactie-analyse ===
    if transactie:
        st.divider()
        st.markdown("### Transactie-analyse")
        zuiverheid = transactie.get("communicatieve_zuiverheid_score")
        stijl = transactie.get("primaire_transactie_stijl", "")
        col1, col2 = st.columns(2)
        with col1:
            if zuiverheid is not None:
                st.markdown(f"**Communicatieve zuiverheid**  \n{_score_label(zuiverheid)}")
        with col2:
            if stijl:
                st.markdown(f"**Transactiestijl:** {clean_md(stijl)}")
        for k in ["analyse", "ulterieure_motieven", "toelichting_risico"]:
            v = transactie.get(k, "")
            if v:
                k_label = k.replace("_", " ").capitalize()
                with st.expander(k_label, expanded=False):
                    st.markdown(clean_md(str(v)))

    # === 4. Spel-analyse (Games) ===
    if spelen:
        st.divider()
        st.markdown("### Spel-analyse (Games)")
        gedetecteerde = spelen.get("gedetecteerde_spelen", [])
        if gedetecteerde:
            for spel in gedetecteerde:
                if not isinstance(spel, dict):
                    continue
                naam = spel.get("naam", "Spel")
                kans = spel.get("waarschijnlijkheid", "")
                label = clean_md(naam) + (f" — {kans}" if kans else "")
                with st.expander(label, expanded=False):
                    formule = spel.get("formule_g_analyse", {})
                    if isinstance(formule, dict):
                        for fk in ["con", "gimmick", "switch", "payoff"]:
                            fv = formule.get(fk, "")
                            if fv:
                                st.markdown(f"**{fk.capitalize()}:** {clean_md(str(fv))}")
                    quotes = spel.get("bewijs_quotes", [])
                    if quotes:
                        st.markdown("**Quotes:**")
                        for q in quotes:
                            if q:
                                st.markdown(f"> {clean_md(str(q))}")
        geen_spelen = spelen.get("afwezigheid_van_spelen_analyse", "")
        if geen_spelen:
            with st.expander("Authenticiteitsanalyse (geen spelen)", expanded=False):
                st.markdown(clean_md(geen_spelen))

    # === 5. Dramadriehoek (Karpman) ===
    if drama:
        st.divider()
        st.markdown("### Dramadriehoek (Karpman)")
        rollen = drama.get("rollen_van_prediker", {})
        if isinstance(rollen, dict):
            for rol, tekst in rollen.items():
                if tekst:
                    st.markdown(f"**{rol.capitalize()}:** {clean_md(str(tekst))}")
        positie_gemeente = drama.get("positie_van_gemeente", "")
        ontsnapping = drama.get("ontsnappings_mogelijkheden", "")
        if positie_gemeente:
            st.caption(f"Positie gemeente: {clean_md(positie_gemeente)}")
        if ontsnapping:
            st.caption(f"Ontsnappingsmogelijkheden: {clean_md(ontsnapping)}")

