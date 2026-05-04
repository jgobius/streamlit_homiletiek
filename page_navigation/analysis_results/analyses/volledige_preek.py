import streamlit as st
from src.utils.utils import (
    clean_md,
    tel_woorden,
    valideer_tekstinvoer,
    woord_meervoud,
    EIGEN_PREEK_MIN_WOORDEN,
    EIGEN_PREEK_MAX_WOORDEN,
)

# Max-woorden voor titel en ondertitel; komt overeen met de limiet in het
# 'Eigen preek'-dialoog in overview.py, zodat de prediker dezelfde grenzen
# ervaart ongeacht vanaf welke plek hij de preektekst bewerkt.
_MAX_WOORDEN_TITEL = 30


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
        new_titel = st.text_input("Titel", value=titel, max_chars=200)
        new_ondertitel = st.text_input("Ondertitel", value=ondertitel, max_chars=300)
        new_preektekst = st.text_area("Preektekst", value=preektekst, height=600)

        # Live woordentelling voor de preektekst zodat de prediker meteen ziet
        # of de invoer binnen de min/max-grenzen past. De harde validatie
        # gebeurt bij Opslaan (consistent met overview.py's dialoog).
        _aantal_woorden = tel_woorden(new_preektekst)
        st.caption(
            f"Aantal woorden: {_aantal_woorden} "
            f"(minimaal {EIGEN_PREEK_MIN_WOORDEN}, maximaal {EIGEN_PREEK_MAX_WOORDEN})"
        )

        if st.button("Opslaan", type="primary", icon="💾"):
            # Valideer titel en ondertitel op woorden + SQL-injectie.
            for waarde, veld in ((new_titel, "Titel"), (new_ondertitel, "Ondertitel")):
                ok, foutmelding = valideer_tekstinvoer(
                    waarde, max_woorden=_MAX_WOORDEN_TITEL, veldnaam=veld
                )
                if not ok:
                    st.error(foutmelding)
                    return
            # Valideer preektekst: eerst woordentelling (min/max), dan SQL-check.
            if _aantal_woorden < EIGEN_PREEK_MIN_WOORDEN:
                # woord_meervoud() voorkomt "1 woorden"; de min-grens is
                # altijd plural maar we gebruiken de helper consistent.
                st.error(
                    f"De preektekst bevat {_aantal_woorden} "
                    f"{woord_meervoud(_aantal_woorden)}; "
                    f"minimaal {EIGEN_PREEK_MIN_WOORDEN} "
                    f"{woord_meervoud(EIGEN_PREEK_MIN_WOORDEN)} vereist."
                )
                return
            ok_preek, fout_preek = valideer_tekstinvoer(
                new_preektekst,
                max_woorden=EIGEN_PREEK_MAX_WOORDEN,
                veldnaam="Preektekst",
            )
            if not ok_preek:
                st.error(fout_preek)
                return
            handler = st.session_state["api_handler"]
            updated = {**result, "titel": new_titel, "ondertitel": new_ondertitel, "preektekst": new_preektekst}
            handler.patch(f"api/analysis-results/{analysis['id']}/?sermon_analysis_id={analysis_id}", data={"result": updated})
            st.toast("Preektekst opgeslagen.")
            st.rerun()

    kerntekst = result.get("kerntekst", "")
    if kerntekst:
        with st.expander("Kerngedeelte", expanded=False):
            st.info(clean_md(kerntekst))

    structuuroverzicht = result.get("structuuroverzicht", "")
    if structuuroverzicht:
        with st.expander("Structuuroverzicht", expanded=False):
            st.markdown(clean_md(structuuroverzicht))

    theologische_kernbeweging = result.get("theologische_kernbeweging", "")
    if theologische_kernbeweging:
        with st.expander("Theologische kernbeweging", expanded=False):
            st.success(clean_md(theologische_kernbeweging))
