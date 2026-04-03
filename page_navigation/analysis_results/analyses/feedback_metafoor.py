from typing import Any

import streamlit as st

from src.utils.utils import clean_md


def _beoordeling_badge(waarde: str) -> None:
    """Toon overall_beoordeling als gekleurde badge."""
    kleur = {
        "EXCELLENT": "green",
        "GOED": "blue",
        "ADEQUAAT": "orange",
        "VERBETERING_NODIG": "red",
        "ZWAK": "red",
    }.get(waarde.upper() if waarde else "", "gray")
    st.markdown(f"**Eindoordeel:** :{kleur}[{waarde}]")


def _render_list_of_dicts(items: list, skip_keys: set | None = None) -> None:
    """Render een lijst van dicts als gestileerde blokken."""
    skip_keys = skip_keys or set()
    for item in items:
        if not isinstance(item, dict):
            if item:
                st.markdown(f"- {clean_md(str(item))}")
            continue
        lines = []
        for k, v in item.items():
            if k in skip_keys:
                continue
            k_label = k.replace("_", " ").capitalize()
            if isinstance(v, list):
                if v:
                    lines.append(f"**{k_label}:** " + ", ".join(clean_md(str(x)) for x in v))
            elif v:
                lines.append(f"**{k_label}:** {clean_md(str(v))}")
        if lines:
            st.markdown("  \n".join(lines))
            st.divider()


def feedback_metafoor(analysis: dict[str, Any]) -> None:
    """Renderer voor metafoor-feedback (Conceptual Metaphor Theory)."""
    result = analysis.get("result", {})
    if not isinstance(result, dict) or not result:
        st.info("Geen resultaat beschikbaar.")
        return

    aanbev = result.get("aanbevelingen", {})
    diag = result.get("diagnostische_evaluatie", {})

    # --- Koptekst: eindoordeel + slotopmerking ---
    overall = aanbev.get("overall_beoordeling", "")
    if overall:
        _beoordeling_badge(overall)

    slotopmerking = aanbev.get("slotopmerking", "")
    if slotopmerking:
        st.info(clean_md(slotopmerking))

    audit_samenvatting = aanbev.get("metafoor_audit_samenvatting", "")
    if audit_samenvatting:
        st.markdown(clean_md(audit_samenvatting))

    # --- Sterktes ---
    sterktes = diag.get("sterktes", [])
    if sterktes:
        with st.expander("Sterktes", expanded=True):
            for s in sterktes:
                if not isinstance(s, dict):
                    st.markdown(f"+ {clean_md(str(s))}")
                    continue
                type_label = s.get("sterkte_type", "")
                beschrijving = s.get("beschrijving", "")
                voorbeeld = s.get("voorbeeld", "")
                header = f"**{clean_md(type_label)}**" if type_label else ""
                body = clean_md(beschrijving) if beschrijving else ""
                if header or body:
                    st.success(f"{header}  \n{body}" if header and body else header or body)
                if voorbeeld:
                    st.caption(f"> {clean_md(voorbeeld)}")

    # --- Risico's ---
    risicos = diag.get("risicos", [])
    if risicos:
        with st.expander("Risico's", expanded=True):
            for r in risicos:
                if not isinstance(r, dict):
                    st.markdown(f"△ {clean_md(str(r))}")
                    continue
                type_label = r.get("risico_type", "")
                beschrijving = r.get("beschrijving", "")
                ernst = r.get("ernst", "")
                voorbeeld = r.get("voorbeeld", "")
                header = f"**{clean_md(type_label)}**" + (f" _{ernst}_" if ernst else "")
                body = clean_md(beschrijving) if beschrijving else ""
                st.warning(f"{header}  \n{body}" if body else header)
                if voorbeeld:
                    st.caption(f"> {clean_md(voorbeeld)}")

    # --- Entailment checks ---
    entailment_checks = aanbev.get("entailment_checks", [])
    if entailment_checks:
        with st.expander("Entailment checks", expanded=False):
            _render_list_of_dicts(entailment_checks)

    # --- Coherentie verbeteringen ---
    coherentie_verb = aanbev.get("coherentie_verbeteringen", [])
    if coherentie_verb:
        with st.expander("Coherentie verbeteringen", expanded=False):
            _render_list_of_dicts(coherentie_verb)

    # --- Revitalisatie suggesties ---
    revitalisatie = aanbev.get("revitalisatie_suggesties", [])
    if revitalisatie:
        with st.expander("Revitalisatie suggesties", expanded=False):
            _render_list_of_dicts(revitalisatie)

    # --- Alternatieve domeinen ---
    alt_domeinen = aanbev.get("alternatieve_domeinen", [])
    if alt_domeinen:
        with st.expander("Alternatieve domeinen", expanded=False):
            _render_list_of_dicts(alt_domeinen)

    # --- Coherentie analyse ---
    coh = diag.get("coherentie_analyse", {})
    if coh:
        with st.expander("Coherentie analyse", expanded=False):
            overall_coh = coh.get("overall_coherentie", "")
            if overall_coh:
                st.markdown(f"**Overall:** {overall_coh}")
            verklaring = coh.get("coherentie_verklaring", "")
            if verklaring:
                st.markdown(clean_md(verklaring))
            incoherentie_punten = coh.get("incoherentie_punten", [])
            if incoherentie_punten:
                st.markdown("**Incoherentie punten:**")
                _render_list_of_dicts(incoherentie_punten)
            blending = coh.get("succesvolle_blending", [])
            if blending:
                st.markdown("**Succesvolle blending:**")
                _render_list_of_dicts(blending)

    # --- Primaire analyse: metafoor-inventaris ---
    prim = result.get("primaire_analyse", {})
    inventaris = prim.get("metafoor_inventaris", [])
    if inventaris:
        with st.expander(f"Metafoor-inventaris ({len(inventaris)} metaforen)", expanded=False):
            for i, m in enumerate(inventaris, 1):
                if not isinstance(m, dict):
                    continue
                expressie = m.get("metafoor_expressie", f"Metafoor {i}")
                vitaliteit = m.get("vitaliteit_status", "")
                st.markdown(f"**{i}. {clean_md(expressie)}** _{vitaliteit}_")
                bron = m.get("brondomein", {})
                doel = m.get("doeldomein", {})
                if isinstance(bron, dict) and bron.get("naam"):
                    st.markdown(f"Brondomein: {clean_md(bron['naam'])}")
                if isinstance(doel, dict) and doel.get("theologisch_concept"):
                    st.markdown(f"Doeldomein: {clean_md(doel['theologisch_concept'])}")
                onbedoeld = m.get("entailments", {})
                if isinstance(onbedoeld, dict):
                    conseq = onbedoeld.get("onbedoelde_consequenties", [])
                    if conseq:
                        st.markdown("Onbedoelde consequenties: " + ", ".join(clean_md(str(c)) for c in conseq))
                st.divider()

    # --- Metadata (compact) ---
    meta = result.get("metadata", {})
    if meta:
        with st.expander("Metadata", expanded=False):
            for k, v in meta.items():
                if v:
                    st.markdown(f"**{k.replace('_', ' ').capitalize()}:** {clean_md(str(v))}")
