import json
from typing import Any

import streamlit as st

from src.utils.utils import clean_md


def contextduiding(analysis: dict[str, Any]) -> None:
    """Render een contextduiding (Perspectieven) analyse."""
    result = analysis.get("result", {})
    if isinstance(result, str):
        # Verwijder markdown code fences (```json ... ```) die LLMs soms toevoegen
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

    analyses: list = result.get("analyses", [])
    metadata: dict = result.get("metadata", {})

    # Zoek het overkoepelende notitie-veld (naam verschilt per analyse-type)
    samenvatting = ""
    for key in result:
        if key not in ("analyses", "metadata") and isinstance(result[key], str):
            samenvatting = result[key]
            break

    if samenvatting:
        st.info(clean_md(samenvatting))

    for item in analyses:
        nummer = item.get("nummer", "")
        titel = item.get("titel", "")
        header = f"{nummer}. {titel}" if nummer else titel

        with st.expander(header, expanded=False):
            # Compacte metadata-balk
            meta_parts = []
            for key in ("sub_domein", "periode_traditie", "kerndenker_of_concept"):
                val = item.get(key, "")
                if val:
                    meta_parts.append(val)
            if meta_parts:
                st.caption(" · ".join(meta_parts))

            # Compactere scheidingslijn dan st.divider(): die voegt aan
            # beide kanten ~1rem witruimte toe wat tussen de caption en
            # 'Tekstueel vertrekpunt' onnodig groot voelt. We wikkelen de
            # <hr> in een <div> met expliciete top- én bottom-margin op 0
            # zodat browser-default-margins van zowel de <hr> zelf als de
            # omliggende <p>-elementen (Streamlit wrapt markdown-output
            # standaard in <p>) niet alsnog asymmetrische witruimte
            # opleveren. De border-color gebruikt currentColor met opacity
            # zodat de lijn in zowel light- als dark-mode subtiel mee-
            # kleurt met de tekstkleur van het thema. De marge is
            # asymmetrisch (0.5rem boven, 1.25rem onder) omdat de bold
            # kop 'Tekstueel vertrekpunt' direct onder de lijn anders
            # visueel tegen de streep aan plakt — Streamlit's eigen
            # margin-collapsing op de <p>-wrapper voegt aan die kant
            # geen extra ruimte toe.
            st.markdown(
                '<div style="margin: 0; padding: 0; line-height: 0;">'
                '<hr style="margin: 0.5rem 0 1.25rem 0; border: none; '
                'border-top: 1px solid currentColor; opacity: 0.2;">'
                '</div>',
                unsafe_allow_html=True,
            )

            # Tekstueel vertrekpunt
            vertrekpunt = item.get("tekstueel_vertrekpunt", "")
            if vertrekpunt:
                st.markdown(f"**Tekstueel vertrekpunt**")
                st.markdown(clean_md(vertrekpunt))

            # Analyse (hoofdtekst)
            analyse_tekst = item.get("analyse", "")
            if analyse_tekst:
                st.markdown("**Analyse**")
                st.markdown(clean_md(analyse_tekst))

            # Homiletische inzet
            homiletisch = item.get("homiletische_inzet", "")
            if homiletisch:
                st.success(f"**Homiletische inzet:** {clean_md(homiletisch)}")

            # Bronnen
            bronnen: list = item.get("bronnen", [])
            if bronnen:
                with st.expander("Bronnen", expanded=False):
                    for b in bronnen:
                        st.markdown(f"- {clean_md(str(b))}")

    # Metadata: verbindingslijnen e.d. Het label is bewust kort
    # ('Samenhang') en in italics — st.expander accepteert markdown in
    # zijn label, dus *...* rendert als cursief — om het submenu visueel
    # te onderscheiden van de inhoudelijke perspectief-secties hierboven.
    if metadata:
        with st.expander("*Samenhang*", expanded=False):
            verbindingen: list = metadata.get("verbindingslijnen", [])
            if verbindingen:
                st.markdown("**Verbindingslijnen**")
                for v in verbindingen:
                    st.markdown(f"- {clean_md(str(v))}")
            for key in metadata:
                if key == "verbindingslijnen":
                    continue
                val = metadata[key]
                label = key.replace("_", " ").capitalize()
                if isinstance(val, list):
                    st.markdown(f"**{label}:** " + ", ".join(str(v) for v in val))
                elif val:
                    st.markdown(f"**{label}:** {clean_md(str(val))}")
