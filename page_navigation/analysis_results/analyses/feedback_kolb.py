from typing import Any

import streamlit as st

from src.utils.utils import clean_md


_FASE_LABELS = {
    "fase_1_concrete_ervaring": ("CE", "Concrete Ervaring"),
    "fase_2_reflectieve_observatie": ("RO", "Reflectieve Observatie"),
    "fase_3_abstracte_conceptualisering": ("AC", "Abstracte Conceptualisering"),
    "fase_4_actief_experimenteren": ("AE", "Actief Experimenteren"),
}

_LEERSTIJL_LABELS = {
    "assimilator_AC_RO": "Assimilator (AC+RO)",
    "converger_AC_AE": "Converger (AC+AE)",
    "accommodator_CE_AE": "Accommodator (CE+AE)",
    "diverger_CE_RO": "Diverger (CE+RO)",
}

_ANDERSON_LABELS = {
    "declaratief_assimilator": "Declaratief — advocaat/filosoof",
    "pragmatisch_converger": "Pragmatisch — gids/coach",
    "narratief_accommodator": "Narratief — verteller",
    "visionair_diverger": "Visionair — kunstenaar/poëet",
}

_OSMER_LABELS = {
    "descriptief_empirisch": "Descriptief-empirisch — 'Wat is er aan de hand?'",
    "interpretatief": "Interpretatief — 'Waarom is dit aan de hand?'",
    "normatief": "Normatief — 'Wat zou er aan de hand moeten zijn?'",
    "pragmatisch": "Pragmatisch — 'Hoe moeten we reageren?'",
}


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


def _render_fase_detail(key: str, fase: dict) -> None:
    """Render één Kolb-fase als expander."""
    if not isinstance(fase, dict):
        return
    afk, label = _FASE_LABELS.get(key, ("?", key.replace("_", " ").capitalize()))
    score = fase.get("score")
    with st.expander(f"{afk} — {label}  {_score_label(score)}", expanded=False):
        analyse = fase.get("analyse", "")
        if analyse:
            st.markdown(clean_md(analyse))

        manifestaties = fase.get("homiletische_manifestaties", "")
        if manifestaties:
            st.caption(f"Manifestaties: {clean_md(manifestaties)}")

        quotes = fase.get("quotes", [])
        if quotes:
            st.markdown("**Quotes:**")
            for q in quotes:
                if q:
                    st.markdown(f"> {clean_md(str(q))}")

        sterke = fase.get("sterke_punten", [])
        verbeter = fase.get("verbeterpunten", [])
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


def _render_analyse_block(label: str, blok: dict, extra_keys: list[str] | None = None) -> None:
    """Render een generiek analyse-blok (Anderson/Osmer/leerstijl) in een expander."""
    if not isinstance(blok, dict):
        return
    score = blok.get("score")
    with st.expander(f"{label} {_score_label(score)}", expanded=False):
        for k in ["analyse", "kernvraag_beantwoord", "rol_prediker",
                  "priesterlijk_luisteren", "wijsheid_van_sage",
                  "profetisch_onderscheidingsvermogen", "dienend_leiderschap",
                  "voorkeuren_geadresseerd", "risicos",
                  *(extra_keys or [])]:
            v = blok.get(k, "")
            if v:
                k_label = k.replace("_", " ").capitalize()
                st.markdown(f"**{k_label}:** {clean_md(str(v))}")

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


def feedback_kolb(analysis: dict[str, Any]) -> None:
    """Renderer voor Kolb-leercyclus feedback."""
    result = analysis.get("result", {})
    if not isinstance(result, dict) or not result:
        st.info("Geen resultaat beschikbaar.")
        return

    totaal = result.get("totaalbeeld", {})
    fasen = result.get("kolb_fasen_analyse", {})
    leerstijlen = result.get("leerstijlen_analyse", {})
    integraal = result.get("integraliteit_en_cyclus", {})
    anderson = result.get("anderson_structuren_analyse", {})
    osmer = result.get("osmer_taken_analyse", {})

    # === 1. Totaaloverzicht ===
    overall_score = totaal.get("overall_kolb_score")
    primaire_stijl = totaal.get("primaire_homiletische_stijl", "")
    primaire_leerstijl = totaal.get("primaire_leerstijl_aangesproken", "")
    uitgesloten = totaal.get("uitgesloten_leerstijlen", [])

    cols = st.columns(3)
    with cols[0]:
        if overall_score is not None:
            # Compactere weergave dan st.metric — gekleurde badge laat
            # in één oogopslag zien of de score sterk of zwak is.
            st.markdown(f"**Overall Kolb-score**  \n{_score_label(overall_score)}")
    with cols[1]:
        if primaire_stijl:
            st.markdown(f"**Dominante stijl**  \n{clean_md(primaire_stijl)}")
    with cols[2]:
        if primaire_leerstijl:
            st.markdown(f"**Primaire leerstijl**  \n{clean_md(primaire_leerstijl)}")

    samenvatting = totaal.get("samenvatting", "")
    if samenvatting:
        st.info(clean_md(samenvatting))

    conclusie = totaal.get("conclusie", "")
    if conclusie:
        with st.expander("Conclusie", expanded=False):
            st.markdown(clean_md(conclusie))

    # Sterke punten + verbeterpunten naast elkaar
    sterke_top = totaal.get("sterke_punten_top_5", [])
    verbeter_top = totaal.get("verbeterpunten_top_5", [])
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
    if aanbev:
        with st.expander("Aanbevelingen voor volgende preek", expanded=False):
            for a in aanbev:
                if a:
                    st.markdown(f"- {clean_md(str(a))}")

    if uitgesloten:
        st.caption("Niet aangesproken leerstijlen: " + ", ".join(str(u) for u in uitgesloten))

    st.divider()

    # === 2. Kolb fasen (details — score staat in expander-titel) ===
    st.markdown("### Kolb-fasen")
    if fasen:
        for key in _FASE_LABELS:
            fase = fasen.get(key, {})
            if fase:
                _render_fase_detail(key, fase)

    # === 3. Leerstijlen ===
    if leerstijlen:
        st.markdown("### Leerstijlen")
        for key, label in _LEERSTIJL_LABELS.items():
            blok = leerstijlen.get(key, {})
            if blok:
                _render_analyse_block(label, blok)

    # === 4. Integraliteit en cyclus ===
    if integraal:
        st.markdown("### Integraliteit en cyclus")
        for key, blok in integraal.items():
            if not isinstance(blok, dict):
                continue
            k_label = key.replace("_", " ").capitalize()
            score = blok.get("score")
            with st.expander(f"{k_label} {_score_label(score)}", expanded=False):
                for veld in ["analyse", "volgorde_en_flow", "geïdentificeerde_structuur",
                             "effectiviteit", "dominante_fase", "onderdrukte_fase",
                             "consequenties", "epistemologische_benadering"]:
                    v = blok.get(veld, "")
                    if v:
                        v_label = veld.replace("_", " ").capitalize()
                        st.markdown(f"**{v_label}:** {clean_md(str(v))}")
                ontbrekend = blok.get("ontbrekende_fasen", [])
                if ontbrekend:
                    st.markdown("**Ontbrekende fasen:** " + ", ".join(str(f) for f in ontbrekend))

    # === 5. Anderson structuren (ingeklapt) ===
    if anderson:
        st.markdown("### Anderson — Homiletic Window")
        for key, label in _ANDERSON_LABELS.items():
            blok = anderson.get(key, {})
            if blok:
                _render_analyse_block(label, blok)

    # === 6. Osmer taken (ingeklapt) ===
    if osmer:
        st.markdown("### Osmer — Praktisch-theologische taken")
        for key, label in _OSMER_LABELS.items():
            blok = osmer.get(key, {})
            if blok:
                _render_analyse_block(label, blok)

