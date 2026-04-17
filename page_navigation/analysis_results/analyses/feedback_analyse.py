import json
from typing import Any

import streamlit as st

from src.utils.utils import clean_md
from page_navigation.analysis_results.analyses.feedback_metafoor import feedback_metafoor
from page_navigation.analysis_results.analyses.feedback_kolb import feedback_kolb
from page_navigation.analysis_results.analyses.feedback_dekker import feedback_dekker
from page_navigation.analysis_results.analyses.feedback_aristoteles import feedback_aristoteles
from page_navigation.analysis_results.analyses.feedback_adversarial import feedback_adversarial
from page_navigation.analysis_results.analyses.feedback_schulz_von_thun import feedback_schulz_von_thun
from page_navigation.analysis_results.analyses.feedback_transactional import feedback_transactional
from page_navigation.analysis_results.analyses.feedback_esthetiek import feedback_esthetiek
from page_navigation.analysis_results.analyses.feedback_narratief import feedback_narratief
from page_navigation.analysis_results.analyses.feedback_taalhandeling import feedback_taalhandeling


_DEDICATED_RENDERERS = {
    "feedback_metafoor": feedback_metafoor,
    "feedback_kolb": feedback_kolb,
    "feedback_dekker": feedback_dekker,
    "feedback_aristoteles": feedback_aristoteles,
    "feedback_adversarial": feedback_adversarial,
    "feedback_schulz_von_thun": feedback_schulz_von_thun,
    "feedback_transactional": feedback_transactional,
    "feedback_esthetiek": feedback_esthetiek,
    "feedback_narratief": feedback_narratief,
    "feedback_taalhandeling": feedback_taalhandeling,
}


def feedback_analyse(analysis: dict[str, Any]) -> None:
    """Generieke renderer voor feedback-analyses."""
    analysis_type_name = analysis.get("analysis_type", {}).get("name", "")
    if analysis_type_name in _DEDICATED_RENDERERS:
        _DEDICATED_RENDERERS[analysis_type_name](analysis)
        return
    result = analysis.get("result", {})
    if isinstance(result, str):
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            if cleaned.endswith("```"):
                cleaned = cleaned[: cleaned.rfind("```")]
        try:
            result = json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            st.markdown(result)
            return
    if not result:
        st.info("Geen resultaat beschikbaar.")
        return

    samenvatting = result.get("samenvatting", "")
    if samenvatting:
        st.info(clean_md(samenvatting))

    sterke_punten = result.get("sterke_punten", [])
    if sterke_punten:
        with st.expander("Sterke punten", expanded=True):
            for punt in sterke_punten:
                st.success(f"+ {clean_md(str(punt))}")

    verbeterpunten = result.get("verbeterpunten", [])
    if verbeterpunten:
        with st.expander("Verbeterpunten", expanded=True):
            for punt in verbeterpunten:
                st.warning(f"△ {clean_md(str(punt))}")

    concrete_aanbevelingen = result.get("concrete_aanbevelingen", [])
    if concrete_aanbevelingen:
        with st.expander("Concrete aanbevelingen", expanded=False):
            for aanbeveling in concrete_aanbevelingen:
                st.markdown(f"- {clean_md(str(aanbeveling))}")

    # Domein-specifieke secties: alles wat geen basisveld is
    skip_keys = {"samenvatting", "sterke_punten", "verbeterpunten", "concrete_aanbevelingen"}
    for key, value in result.items():
        if key.startswith("_") or key in skip_keys:
            continue
        label = key.replace("_", " ").capitalize()
        if isinstance(value, list) and value:
            with st.expander(label, expanded=False):
                for item in value:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            k_label = k.replace("_", " ").capitalize()
                            if isinstance(v, list):
                                st.markdown(f"**{k_label}:** " + ", ".join(str(x) for x in v))
                            elif v:
                                st.markdown(f"**{k_label}:** {clean_md(str(v))}")
                        st.divider()
                    elif item:
                        st.markdown(f"- {clean_md(str(item))}")
        elif isinstance(value, dict) and value:
            with st.expander(label, expanded=False):
                for k, v in value.items():
                    k_label = k.replace("_", " ").capitalize()
                    if isinstance(v, list):
                        if v:
                            st.markdown(f"**{k_label}:**")
                            for item in v:
                                st.markdown(f"- {clean_md(str(item))}")
                    elif v:
                        st.markdown(f"**{k_label}:** {clean_md(str(v))}")
        elif isinstance(value, str) and value:
            with st.expander(label, expanded=False):
                st.markdown(clean_md(value))
