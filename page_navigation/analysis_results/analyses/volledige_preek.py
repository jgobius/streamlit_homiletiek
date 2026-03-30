import streamlit as st

from src.utils.utils import clean_md


def volledige_preek(analysis: dict, analysis_id: int) -> None:
    """Render de volledige preek met inline bewerkomgeving."""
    result = analysis.get("result", {})
    if not isinstance(result, dict):
        result = {}

    titel = result.get("titel", "")
    ondertitel = result.get("ondertitel", "")
    preektekst = result.get("preektekst", "")

    with st.container(border=True):
        st.subheader("Preektekst bewerken")
        new_titel = st.text_input("Titel", value=titel)
        new_ondertitel = st.text_input("Ondertitel", value=ondertitel)
        new_preektekst = st.text_area("Preektekst", value=preektekst, height=600)
        if st.button("Opslaan", type="primary", icon="💾"):
            handler = st.session_state["api_handler"]
            updated = {
                **result,
                "titel": new_titel,
                "ondertitel": new_ondertitel,
                "preektekst": new_preektekst,
            }
            handler.patch(
                f"api/analysis-results/{analysis['id']}/?sermon_analysis_id={analysis_id}",
                data={"result": updated},
            )
            st.toast("Preektekst opgeslagen.")
            st.rerun()

    kerntekst = result.get("kerntekst", "")
    if kerntekst:
        with st.expander("Kerntekst", expanded=False):
            st.info(clean_md(kerntekst))

    structuuroverzicht = result.get("structuuroverzicht", "")
    if structuuroverzicht:
        with st.expander("Structuuroverzicht", expanded=False):
            st.markdown(clean_md(structuuroverzicht))

    theologische_kernbeweging = result.get("theologische_kernbeweging", "")
    if theologische_kernbeweging:
        with st.expander("Theologische kernbeweging", expanded=False):
            st.success(clean_md(theologische_kernbeweging))
