from typing import Any

import streamlit as st

from src.utils.utils import clean_md


_DIAGNOSE_COLORS = {
    "INFORMATIEF_DOCEREND":    "orange",
    "APPELLEREND_WETTISCH":    "red",
    "GETUIGEND_SUBJECTIEF":    "orange",
    "TROOSTEND_EVANGELISCH":   "blue",
    "SACRAMENTEEL_SCHEPPEND":  "green",
}

_OVERALL_COLORS = {
    "EXCELLENT":        "green",
    "GOED":             "blue",
    "ADEQUAAT":         "orange",
    "VERBETERING_NODIG":"red",
    "ZWAK":             "red",
}

_WERKWOORD_CATEGORIEEN = [
    ("assertieven",   "Assertieven"),
    ("directieven",   "Directieven"),
    ("expressieven",  "Expressieven"),
    ("commissieven",  "Commissieven"),
    ("declaratieven", "Declaratieven"),
]

_AANBEV_SECTIES = [
    ("performatieve_intensivering",   "Performatieve intensivering"),
    ("toezegging_versterking",        "Toezegging versterken"),
    ("adressering_verbetering",       "Adressering verbeteren"),
    ("indicatief_imperatief_herstel", "Indicatief-imperatief herstel"),
]


def _diagnose_badge(waarde: str) -> None:
    kleur = _DIAGNOSE_COLORS.get(waarde.upper() if waarde else "", "gray")
    label = waarde.replace("_", " ") if waarde else "—"
    st.markdown(f"**Diagnose:** :{kleur}[{label}]")


def _overall_badge(waarde: str) -> None:
    kleur = _OVERALL_COLORS.get(waarde.upper() if waarde else "", "gray")
    st.markdown(f"**Eindoordeel:** :{kleur}[{waarde}]")


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


def feedback_taalhandeling(analysis: dict[str, Any]) -> None:
    """Renderer voor Taalhandelingstheorie feedback (Austin/Searle)."""
    result = analysis.get("result", {})
    if not isinstance(result, dict) or not result:
        st.info("Geen resultaat beschikbaar.")
        return

    diag = result.get("diagnostische_evaluatie", {})
    aanbev = result.get("aanbevelingen", {})
    werkwoorden = result.get("werkwoord_analyse", {})
    constatief = result.get("constatief_performatief_diagnose", {})
    sacramenteel = result.get("sacramenteel_patroon_analyse", {})

    # === 1. Diagnostisch overzicht ===
    # Vroeger 4 kolommen (diagnose | eindoordeel | gebeur-score | sacramentele
    # kracht). Probleem: 'GETUIGEND SUBJECTIEF' wrapte over 2 regels in een
    # smalle kolom. Nu: twee badges naast elkaar op 2 kolommen (allebei 1
    # regel), en de twee korte scores inline op één regel daaronder.
    primaire_diagnose = diag.get("primaire_diagnose", "")
    overall_beoordeling = aanbev.get("overall_beoordeling", "")
    gebeuren_score = diag.get("gebeuren_score")
    sacramentele_kracht = diag.get("sacramentele_kracht")

    if primaire_diagnose or overall_beoordeling:
        col_d, col_e = st.columns(2)
        with col_d:
            if primaire_diagnose:
                _diagnose_badge(primaire_diagnose)
        with col_e:
            if overall_beoordeling:
                _overall_badge(overall_beoordeling)

    score_parts: list[str] = []
    if gebeuren_score is not None:
        score_parts.append(f"**Gebeur-score:** {_score_label(gebeuren_score)}")
    if sacramentele_kracht is not None:
        score_parts.append(f"**Sacramentele kracht:** {_score_label(sacramentele_kracht)}")
    if score_parts:
        st.markdown("  ·  ".join(score_parts))

    diagnose_toelichting = diag.get("diagnose_toelichting", "")
    if diagnose_toelichting:
        st.info(clean_md(diagnose_toelichting))

    slotopmerking = aanbev.get("slotopmerking", "")
    if slotopmerking:
        st.markdown(clean_md(slotopmerking))

    sterke = diag.get("sterke_punten", [])
    zwakke = diag.get("zwakke_punten", [])
    if sterke or zwakke:
        col_s, col_z = st.columns(2)
        with col_s:
            if sterke:
                st.markdown("**Sterke punten**")
                for item in sterke:
                    if isinstance(item, dict):
                        aspect = item.get("aspect", "")
                        bewijs = item.get("tekstueel_bewijs", "")
                        effect = item.get("effect", "")
                        if aspect:
                            st.success(f"+ {clean_md(aspect)}")
                        if bewijs:
                            st.markdown(f"> {clean_md(bewijs)}")
                        if effect:
                            st.caption(clean_md(effect))
                    elif item:
                        st.success(f"+ {clean_md(str(item))}")
        with col_z:
            if zwakke:
                st.markdown("**Zwakke punten**")
                for item in zwakke:
                    if isinstance(item, dict):
                        aspect = item.get("aspect", "")
                        bewijs = item.get("tekstueel_bewijs", "")
                        ernst = item.get("ernst", "")
                        label = clean_md(aspect) + (f" _({ernst})_" if ernst else "")
                        if label:
                            st.warning(f"△ {label}")
                        if bewijs:
                            st.markdown(f"> {clean_md(bewijs)}")
                    elif item:
                        st.warning(f"△ {clean_md(str(item))}")

    # === 2. Werkwoord-analyse ===
    # Geen leading divider; de H3-kop is voldoende scheiding.
    # Geen st.metric-rij meer: de percentages staan al in de expander-titels
    # ("Assertieven (124×, 70%)"), en st.metric rendert ze in een te grote
    # font waardoor het blok onnodig dominant werd.
    if werkwoorden:
        st.markdown("### Werkwoord-analyse")
        for key, label in _WERKWOORD_CATEGORIEEN:
            blok = werkwoorden.get(key, {})
            if not isinstance(blok, dict) or not blok:
                continue
            freq = blok.get("frequentie", "")
            pct = blok.get("procent", "")
            header = label
            if freq or pct:
                header += f" ({freq}×, {pct})"
            with st.expander(header, expanded=False):
                voorbeelden = blok.get("voorbeelden", [])
                if voorbeelden:
                    st.markdown("**Voorbeelden:**")
                    for v in voorbeelden:
                        if v:
                            st.markdown(f"> {clean_md(str(v))}")
                dom_ww = blok.get("dominante_werkwoorden", [])
                if dom_ww:
                    st.caption("Dominante werkwoorden: " + ", ".join(str(w) for w in dom_ww))
                for ek in ["fundament_check", "kwaliteit", "autoriteit"]:
                    v = blok.get(ek, "")
                    if v:
                        k_label = ek.replace("_", " ").capitalize()
                        st.caption(f"**{k_label}:** {clean_md(str(v))}")

    # === 3. Constatief / Performatief diagnose ===
    # Geen leading divider; de H3-kop is voldoende scheiding.
    if constatief:
        st.markdown("### Constatief / Performatief")
        prim_class = constatief.get("primaire_classificatie", "")
        con_pct = constatief.get("constatief_percentage", "")
        perf_pct = constatief.get("performatief_percentage", "")
        # Eén compacte regel i.p.v. drie st.metric-kolommen — st.metric was
        # visueel te dominant en de getallen kwamen al terug in de
        # surplus/deficit-secties hieronder.
        if prim_class:
            st.markdown(f"**Classificatie:** {clean_md(prim_class.replace('_', ' '))}")
        pct_parts: list[str] = []
        if con_pct:
            pct_parts.append(f"**Constatief:** {con_pct}")
        if perf_pct:
            pct_parts.append(f"**Performatief:** {perf_pct}")
        if pct_parts:
            st.markdown("  ·  ".join(pct_parts))

        toezegging = constatief.get("toezegging_check", {})
        if isinstance(toezegging, dict):
            tz_kwaliteit = toezegging.get("kwaliteit_toezeggen", "")
            tz_voorbeelden = toezegging.get("voorbeelden", [])
            tz_moment = toezegging.get("moment_in_preek", "")
            if tz_kwaliteit or tz_voorbeelden:
                with st.expander("Toezegging-check", expanded=False):
                    if tz_kwaliteit:
                        st.markdown(f"**Kwaliteit:** {clean_md(tz_kwaliteit)}")
                    if tz_moment:
                        st.caption(f"Moment: {clean_md(tz_moment)}")
                    for q in tz_voorbeelden:
                        if q:
                            st.markdown(f"> {clean_md(str(q))}")

        for sec_key, sec_label in [
            ("constatief_surplus_analyse", "Constatief surplus"),
            ("performatief_deficit_analyse", "Performatief deficit"),
        ]:
            blok = constatief.get(sec_key, {})
            if not isinstance(blok, dict):
                continue
            aanwezig = blok.get("aanwezig")
            if aanwezig in (None, False, "false", "False"):
                continue
            ernst = blok.get("ernst", "")
            with st.expander(f"{sec_label} ({ernst})" if ernst else sec_label, expanded=False):
                for k in ["indicatoren", "effect_op_hoorder", "missende_elementen"]:
                    v = blok.get(k)
                    if isinstance(v, list) and v:
                        k_label = k.replace("_", " ").capitalize()
                        st.markdown(f"**{k_label}:**")
                        for x in v:
                            if x:
                                st.markdown(f"- {clean_md(str(x))}")
                    elif v:
                        k_label = k.replace("_", " ").capitalize()
                        st.markdown(f"**{k_label}:** {clean_md(str(v))}")

    # === 4. Sacramenteel patroon ===
    # Geen leading divider; de H3-kop is voldoende scheiding.
    if sacramenteel:
        st.markdown("### Sacramenteel patroon")
        patroon = sacramenteel.get("patroon_identificatie", "")
        if patroon:
            st.markdown(f"**Patroon:** {clean_md(patroon)}")
        indicatief = sacramenteel.get("indicatief_imperatief_verhouding", {})
        if isinstance(indicatief, dict) and any(indicatief.values()):
            with st.expander("Indicatief — Imperatief verhouding", expanded=False):
                for k, v in indicatief.items():
                    if not v:
                        continue
                    k_label = k.replace("_", " ").capitalize()
                    if isinstance(v, list):
                        st.markdown(f"**{k_label}:**")
                        for x in v:
                            if x:
                                st.markdown(f"- {clean_md(str(x))}")
                    else:
                        st.markdown(f"**{k_label}:** {clean_md(str(v))}")

    # === 5. Aanbevelingen ===
    aanbev_beschikbaar = any(
        isinstance(aanbev.get(k), dict) and aanbev[k].get("nodig") not in (False, "false", "False")
        for k, _ in _AANBEV_SECTIES
    )
    if aanbev_beschikbaar:
        # Geen leading divider; de H3-kop is voldoende scheiding.
        st.markdown("### Aanbevelingen")
        for key, label in _AANBEV_SECTIES:
            blok = aanbev.get(key, {})
            if not isinstance(blok, dict) or not blok:
                continue
            if blok.get("nodig") in (False, "false", "False"):
                continue
            with st.expander(label, expanded=False):
                suggesties = blok.get("specifieke_suggesties", [])
                if suggesties:
                    for s in suggesties:
                        if isinstance(s, dict):
                            huidig = s.get("huidige_formulering", "")
                            revisie = s.get("voorgestelde_revisie", "")
                            verschil = s.get("verschil", "")
                            if huidig:
                                st.markdown(f"**Huidig:** _{clean_md(huidig)}_")
                            if revisie:
                                st.success(f"+ {clean_md(revisie)}")
                            if verschil:
                                st.caption(clean_md(verschil))
                else:
                    for k, v in blok.items():
                        if k == "nodig" or not v:
                            continue
                        k_label = k.replace("_", " ").capitalize()
                        if isinstance(v, list):
                            st.markdown(f"**{k_label}:**")
                            for x in v:
                                if x:
                                    st.markdown(f"- {clean_md(str(x))}")
                        else:
                            st.markdown(f"**{k_label}:** {clean_md(str(v))}")

