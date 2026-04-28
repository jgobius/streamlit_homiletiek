from typing import Any
import streamlit as st
from src.utils.utils import clean_md

_META_LABELS = {"type":"Type","bron":"Bron","toon":"Toon","lowry_stadium":"Lowry","buttrick_plaatsing":"Buttrick","retorische_functie":"Functie","doelgroep":"Doelgroep","culturele_context":"Cultuur","pastorale_gevoeligheid":"Pastoraal","concreetheid":"Concreetheid","lengte":"Lengte","kernthema":"Thema","actualiteit":"Actualiteit"}

def illustraties(analysis: dict[str, Any]) -> None:
    result: dict[str, Any] = analysis.get("result", {})
    illustraties_lijst: list = result.get("illustraties", [])
    totaal: int = int(result.get("totaal_aantal_illustraties", len(illustraties_lijst)))
    diversiteit: dict = result.get("diversiteit_analyse", {})

    # Filter op type — zonder afzonderlijke metric of "X van Y"-caption bij "Alle":
    # het totaal is af te leiden uit de zichtbare expanders, dus dat dubbel tonen
    # gaf overbodige informatie.
    alle_typen = sorted({ill.get("metadata", {}).get("type", "") for ill in illustraties_lijst if ill.get("metadata", {}).get("type")})
    filter_type = st.selectbox("Filter op type", options=["Alle"] + alle_typen, index=0)
    gefilterd = illustraties_lijst if filter_type == "Alle" else [ill for ill in illustraties_lijst if ill.get("metadata", {}).get("type", "") == filter_type]
    # Caption alleen tonen wanneer er daadwerkelijk gefilterd is — dan is "X van Y"
    # wel informatief (bv. 5 van 20).
    if filter_type != "Alle":
        st.caption(f"{len(gefilterd)} van {totaal} illustraties")
    st.divider()

    for ill in gefilterd:
        nummer: int = ill.get("nummer", 0)
        titel: str = ill.get("titel", "")
        meta: dict = ill.get("metadata", {})
        ill_type = meta.get("type", "")
        with st.expander(f"#{nummer} — {titel}  *({ill_type})*", expanded=False):
            ill_tekst: str = ill.get("illustratie_tekst", "")
            if ill_tekst:
                st.markdown(clean_md(ill_tekst))
            brug: str = ill.get("brug_naar_waarheid", "")
            if brug:
                st.info(f"**Brug naar de waarheid:** {clean_md(brug)}")
            if meta:
                badge_parts = [f"**{label}:** {meta[field]}" for field, label in _META_LABELS.items() if meta.get(field)]
                if badge_parts:
                    left = badge_parts[:len(badge_parts)//2+1]
                    right = badge_parts[len(badge_parts)//2+1:]
                    c1, c2 = st.columns(2)
                    with c1:
                        for part in left: st.caption(part)
                    with c2:
                        for part in right: st.caption(part)
