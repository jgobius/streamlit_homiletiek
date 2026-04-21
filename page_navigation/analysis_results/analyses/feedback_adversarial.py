from typing import Any

import streamlit as st

from src.utils.utils import clean_md


def feedback_adversarial(analysis: dict[str, Any]) -> None:
    """Renderer voor adversarial red-team feedback met vijf persona-aanvallen."""
    result = analysis.get("result", {})
    if not isinstance(result, dict) or not result:
        st.info("Geen resultaat beschikbaar.")
        return

    # Overkoepelende diagnose prominent bovenaan — één paragraaf over
    # de structurele kwetsbaarheden die uit alle aanvallen samen blijken.
    diagnose = result.get("overkoepelende_diagnose", "")
    if diagnose:
        st.info(clean_md(diagnose))

    # Twee kolommen voor de samenvattende velden: wat moet er gebeuren
    # (prioritaire nuanceringen) versus wat blijft overeind (bestaanskracht).
    prioritair = result.get("prioritaire_nuanceringen", [])
    bestaanskracht = result.get("bestaanskracht", "")
    if prioritair or bestaanskracht:
        col_p, col_b = st.columns(2)
        with col_p:
            if prioritair:
                st.markdown("**Prioritaire nuanceringen**")
                for p in prioritair:
                    if p:
                        st.warning(f"△ {clean_md(str(p))}")
        with col_b:
            if bestaanskracht:
                st.markdown("**Bestaanskracht**")
                st.success(clean_md(bestaanskracht))

    st.divider()

    # Per persona een expander met de volledige aanval. De persona-naam en
    # het perspectief-type (inside/outside) staan in de label zodat de
    # lezer meteen de invalshoek herkent zonder open te klappen.
    aanvallen = result.get("adversariale_aanvallen", [])
    if aanvallen:
        st.markdown("### Adversariale aanvallen")
        for aanval in aanvallen:
            if not isinstance(aanval, dict):
                continue
            nummer = aanval.get("nummer", "")
            persona = aanval.get("persona", "")
            perspectief = aanval.get("perspectief_type", "")
            traditie = aanval.get("traditie_of_achtergrond", "")
            aanvalshoek = aanval.get("aanvalshoek", "")
            citaat = aanval.get("preek_citaat", "")
            kritiek = aanval.get("kritiek", "")
            blinde_vlek = aanval.get("blinde_vlek_diagnose", "")
            suggestie = aanval.get("suggestie_voor_nuancering", "")

            label_parts = []
            if nummer:
                label_parts.append(f"{nummer}.")
            if persona:
                label_parts.append(clean_md(str(persona)))
            if perspectief:
                label_parts.append(f"({perspectief})")
            label = " ".join(label_parts) or "Aanval"

            with st.expander(label, expanded=False):
                if traditie:
                    st.caption(clean_md(traditie))
                if aanvalshoek:
                    st.markdown(f"**Aanvalshoek:** {clean_md(aanvalshoek)}")
                if citaat:
                    st.markdown(f"> {clean_md(citaat)}")
                if kritiek:
                    st.markdown(clean_md(kritiek))
                if blinde_vlek:
                    st.warning(f"**Blinde vlek:** {clean_md(blinde_vlek)}")
                if suggestie:
                    st.success(f"**Suggestie:** {clean_md(suggestie)}")
