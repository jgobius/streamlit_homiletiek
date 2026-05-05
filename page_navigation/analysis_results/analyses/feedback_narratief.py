from typing import Any

import streamlit as st

from src.utils.utils import clean_md


_CLASSIFICATIE_COLORS = {
    "MORALISME": "red",
    "GENADE": "green",
    "GEMENGD": "orange",
}

_OVERALL_COLORS = {
    "EXCELLENT": "green",
    "GOED": "blue",
    "ADEQUAAT": "orange",
    "VERBETERING_NODIG": "red",
    "ZWAK": "red",
}

_ACTANTEN = [
    ("subject",     "Subject"),
    ("object",      "Object"),
    ("zender",      "Zender"),
    ("ontvanger",   "Ontvanger"),
    ("helper",      "Helper"),
    ("tegenstander","Tegenstander"),
]

_MODALITEITEN = [
    ("devoir_faire",  "Devoir (Moeten)"),
    ("vouloir_faire", "Vouloir (Willen)"),
    ("savoir_faire",  "Savoir (Weten)"),
    ("pouvoir_faire", "Pouvoir (Kunnen)"),
]

_AANBEV_SECTIES = [
    ("subject_herpositionering",    "Subject-herpositionering"),
    ("identificatie_herstel",       "Identificatie herstel"),
    ("modale_balans",               "Modale balans"),
    ("tegenstander_intensivering",  "Tegenstander-intensivering"),
    ("narratieve_hierarchie_herstel","Narratieve hiërarchie herstel"),
]


def _classificatie_badge(waarde: str) -> None:
    kleur = _CLASSIFICATIE_COLORS.get(waarde.upper() if waarde else "", "gray")
    st.markdown(f"**Classificatie:** :{kleur}[{waarde}]")


def _overall_badge(waarde: str) -> None:
    kleur = _OVERALL_COLORS.get(waarde.upper() if waarde else "", "gray")
    st.markdown(f"**Eindoordeel:** :{kleur}[{waarde}]")


def _is_truthy(val) -> bool:
    return val not in (None, False, "false", "False", "")


# Schaalsuffix '/10' weggelaten omdat 10 de standaardschaal is.
# Voeg een suffix pas toe wanneer de schaal écht afwijkt (bv. '/5').
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


def feedback_narratief(analysis: dict[str, Any]) -> None:
    """Renderer voor narratieve semiotiek feedback (Greimas actantieel model)."""
    result = analysis.get("result", {})
    if not isinstance(result, dict) or not result:
        st.info("Geen resultaat beschikbaar.")
        return

    diag = result.get("diagnostische_evaluatie", {})
    aanbev = result.get("aanbevelingen", {})
    actant = result.get("actantiele_analyse", {})
    gram = result.get("grammaticale_analyse", {})

    # === 1. Diagnostisch overzicht ===
    classificatie = diag.get("primaire_classificatie", "")
    overall_beoordeling = aanbev.get("overall_beoordeling", "")

    cols = st.columns(2)
    with cols[0]:
        if classificatie:
            _classificatie_badge(classificatie)
    with cols[1]:
        if overall_beoordeling:
            _overall_badge(overall_beoordeling)

    classificatie_toelichting = diag.get("classificatie_toelichting", "")
    if classificatie_toelichting:
        st.info(clean_md(classificatie_toelichting))

    slotopmerking = aanbev.get("slotopmerking", "")
    if slotopmerking:
        st.markdown(clean_md(slotopmerking))

    indicatoren_moralisme = diag.get("indicatoren_moralisme", [])
    indicatoren_genade = diag.get("indicatoren_genade", [])
    if indicatoren_moralisme or indicatoren_genade:
        col_m, col_g = st.columns(2)
        with col_m:
            if indicatoren_moralisme:
                st.markdown("**Indicatoren moralisme**")
                for item in indicatoren_moralisme:
                    if not isinstance(item, dict):
                        continue
                    indicator = item.get("indicator", "")
                    bewijs = item.get("tekstueel_bewijs", "")
                    ernst = item.get("ernst", "")
                    label = clean_md(indicator) + (f" _({ernst})_" if ernst else "")
                    st.warning(f"△ {label}")
                    if bewijs:
                        st.markdown(f"> {clean_md(bewijs)}")
        with col_g:
            if indicatoren_genade:
                st.markdown("**Indicatoren genade**")
                for item in indicatoren_genade:
                    if not isinstance(item, dict):
                        continue
                    indicator = item.get("indicator", "")
                    bewijs = item.get("tekstueel_bewijs", "")
                    sterkte = item.get("sterkte", "")
                    label = clean_md(indicator) + (f" _({sterkte})_" if sterkte else "")
                    st.success(f"+ {label}")
                    if bewijs:
                        st.markdown(f"> {clean_md(bewijs)}")

    st.divider()

    # === 2. Actantiële analyse ===
    st.markdown("### Actantiële analyse")
    primair = actant.get("primair_narratief_programma", {}) if isinstance(actant, dict) else {}
    if primair:
        beschrijving = primair.get("beschrijving", "")
        if beschrijving:
            st.markdown(f"**Programma:** {clean_md(beschrijving)}")

        visualisatie = actant.get("actantieel_schema_visualisatie", {})
        if isinstance(visualisatie, dict) and any(visualisatie.values()):
            with st.expander("Schemavisualisatie", expanded=True):
                for v in visualisatie.values():
                    if v:
                        st.code(str(v), language=None)

        for actant_key, actant_label in _ACTANTEN:
            blok = primair.get(actant_key, {})
            if not isinstance(blok, dict) or not blok:
                continue
            ident = blok.get("identificatie", "")
            bewijs_list = blok.get("tekstueel_bewijs", [])
            with st.expander(f"{actant_label}: {clean_md(ident)}", expanded=False):
                extra_keys = [k for k in blok
                              if k not in ("identificatie", "tekstueel_bewijs") and blok.get(k)]
                for ek in extra_keys:
                    v = blok[ek]
                    k_label = ek.replace("_", " ").capitalize()
                    if isinstance(v, list) and v:
                        st.markdown(f"**{k_label}:**")
                        for x in v:
                            if x:
                                st.markdown(f"- {clean_md(str(x))}")
                    elif v:
                        st.markdown(f"**{k_label}:** {clean_md(str(v))}")
                if bewijs_list:
                    st.markdown("**Tekstueel bewijs:**")
                    for q in bewijs_list:
                        if q:
                            st.markdown(f"> {clean_md(str(q))}")

    secundair = actant.get("secundair_narratief_programma", {}) if isinstance(actant, dict) else {}
    if isinstance(secundair, dict) and _is_truthy(secundair.get("aanwezig")):
        with st.expander("Secundair narratief programma", expanded=False):
            for k, v in secundair.items():
                if k == "aanwezig" or not v:
                    continue
                k_label = k.replace("_", " ").capitalize()
                st.markdown(f"**{k_label}:** {clean_md(str(v))}")

    # === 3. Grammaticale analyse ===
    if gram:
        st.divider()
        st.markdown("### Grammaticale analyse")
        subject_check = gram.get("subject_check", {})
        modale = gram.get("modale_analyse", {})

        if subject_check:
            rutledge = subject_check.get("rutledge_score")
            god_count = subject_check.get("god_als_subject_count", "")
            mens_count = subject_check.get("mens_als_subject_count", "")
            ratio = subject_check.get("ratio", "")
            sc_cols = st.columns(3)
            with sc_cols[0]:
                if rutledge is not None:
                    # Compactere weergave dan st.metric — gekleurde badge laat
                    # in één oogopslag zien of de score sterk of zwak is.
                    st.markdown(f"**Rutledge-score**  \n{_score_label(rutledge)}")
            with sc_cols[1]:
                if god_count:
                    st.markdown(f"**God als subject:** {clean_md(str(god_count))}")
            with sc_cols[2]:
                if mens_count:
                    st.markdown(f"**Mens als subject:** {clean_md(str(mens_count))}")
            if ratio:
                st.caption(f"Verhouding God/Mens: {clean_md(str(ratio))}")

        if modale:
            dom = modale.get("dominante_modaliteit", "")
            interp = modale.get("modale_interpretatie", "")
            st.markdown("**Modale analyse**")
            if dom:
                st.caption(f"Dominant: **{clean_md(dom)}**")
            if interp:
                st.markdown(clean_md(interp))
            mod_cols = st.columns(4)
            for i, (mkey, mlabel) in enumerate(_MODALITEITEN):
                mblok = modale.get(mkey, {})
                mprom = mblok.get("prominentie") if isinstance(mblok, dict) else None
                afk = mlabel.split("(")[0].strip()
                with mod_cols[i]:
                    st.markdown(f"**{afk}**  \n{_score_label(mprom)}")

    # === 4. Exemplarisme-check ===
    exemplarisme = diag.get("exemplarisme_check", {})
    if isinstance(exemplarisme, dict) and _is_truthy(exemplarisme.get("aanwezig")):
        with st.expander("Exemplarisme-check", expanded=False):
            for k, v in exemplarisme.items():
                if k == "aanwezig" or not v:
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
        isinstance(aanbev.get(k), dict) and not (aanbev[k].get("nodig") in (False, "false", "False"))
        for k, _ in _AANBEV_SECTIES
    )
    if aanbev_beschikbaar:
        st.divider()
        st.markdown("### Aanbevelingen")
        for key, label in _AANBEV_SECTIES:
            blok = aanbev.get(key, {})
            if not isinstance(blok, dict) or not blok:
                continue
            if blok.get("nodig") in (False, "false", "False"):
                continue
            with st.expander(label, expanded=False):
                for k, v in blok.items():
                    if k == "nodig" or not v:
                        continue
                    k_label = k.replace("_", " ").capitalize()
                    st.markdown(f"**{k_label}:** {clean_md(str(v))}")

