from typing import Any

import streamlit as st

from src.utils.utils import clean_md


def preekschets(analysis: dict[str, Any]) -> None:
    """Render een preekschets met preek_onderdelen formaat."""
    result = analysis.get("result", {})

    kerntekst = result.get("kerntekst") or result.get("schriftlezing", "")
    structuur_type = result.get("structuur_type", "")

    if kerntekst:
        st.info(f"📖 {kerntekst}")
    if structuur_type:
        st.caption(f"Structuur: {structuur_type}")

    st.divider()

    for onderdeel in result.get("preek_onderdelen", []):
        titel = onderdeel.get("titel", "")
        type_label = onderdeel.get("type", "")
        volgorde = onderdeel.get("volgorde", "")
        inhoud = onderdeel.get("inhoud", "")
        toelichting = onderdeel.get("toelichting", "")

        header = f"{volgorde}. {titel} ({type_label})" if volgorde else f"{titel} ({type_label})"
        with st.expander(header, expanded=True):
            st.markdown(clean_md(inhoud))
            if toelichting:
                st.caption(toelichting)

    kernwoorden = result.get("kernwoorden", [])
    if kernwoorden:
        st.caption("**Kernwoorden:** " + " · ".join(kernwoorden))

    theologische_beweging = result.get("theologische_beweging", "")
    if theologische_beweging:
        st.success(f"🔷 {theologische_beweging}")
