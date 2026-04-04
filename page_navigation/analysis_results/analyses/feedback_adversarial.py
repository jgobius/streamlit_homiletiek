from typing import Any

import streamlit as st

from src.utils.utils import clean_md


def feedback_adversarial(analysis: dict[str, Any]) -> None:
    """Renderer voor adversarial red-team feedback."""
    result = analysis.get("result", {})
    if not isinstance(result, dict) or not result:
        st.info("Geen resultaat beschikbaar.")
        return

    samenvatting = result.get("samenvatting", "")
    if samenvatting:
        st.info(clean_md(samenvatting))

    eindbeoordeling = result.get("eindbeoordeling", "")
    if eindbeoordeling:
        st.markdown(clean_md(eindbeoordeling))

    sterke = result.get("sterke_punten", [])
    verbeter = result.get("verbeterpunten", [])
    if sterke or verbeter:
        col_s, col_v = st.columns(2)
        with col_s:
            if sterke:
                st.markdown("**Sterke punten**")
                for p in sterke:
                    if p:
                        st.success(f"+ {clean_md(str(p))}")
        with col_v:
            if verbeter:
                st.markdown("**Verbeterpunten**")
                for p in verbeter:
                    if p:
                        st.warning(f"△ {clean_md(str(p))}")

    st.divider()

    kwetsbaarheden = result.get("theologische_kwetsbaarheden", [])
    if kwetsbaarheden:
        st.markdown("### Theologische kwetsbaarheden")
        for item in kwetsbaarheden:
            if not isinstance(item, dict):
                continue
            passage = item.get("passage", "")
            kritiek = item.get("kritiek", "")
            suggestie = item.get("suggestie", "")
            label = (clean_md(passage[:60]) + "…") if len(passage) > 60 else clean_md(passage)
            with st.expander(label or "Kwetsbaarheid", expanded=False):
                if passage:
                    st.markdown(f"> {clean_md(passage)}")
                if kritiek:
                    st.warning(f"**Kritiek:** {clean_md(kritiek)}")
                if suggestie:
                    st.success(f"**Suggestie:** {clean_md(suggestie)}")

    retorische = result.get("retorische_zwaktes", [])
    if retorische:
        st.markdown("### Retorische zwaktes")
        for item in retorische:
            if not isinstance(item, dict):
                continue
            passage = item.get("passage", "")
            probleem = item.get("probleem", "")
            alternatief = item.get("alternatief", "")
            label = (clean_md(passage[:60]) + "…") if len(passage) > 60 else clean_md(passage)
            with st.expander(label or "Retorische zwakte", expanded=False):
                if passage:
                    st.markdown(f"> {clean_md(passage)}")
                if probleem:
                    st.warning(f"**Probleem:** {clean_md(probleem)}")
                if alternatief:
                    st.success(f"**Alternatief:** {clean_md(alternatief)}")

    blinde_vlekken = result.get("pastorale_blinde_vlekken", [])
    if blinde_vlekken:
        with st.expander("Pastorale blinde vlekken", expanded=False):
            for v in blinde_vlekken:
                if v:
                    st.markdown(f"- {clean_md(str(v))}")

    weerstand = result.get("maatschappelijke_weerstand", [])
    if weerstand:
        with st.expander("Maatschappelijke weerstand", expanded=False):
            for w in weerstand:
                if w:
                    st.markdown(f"- {clean_md(str(w))}")
