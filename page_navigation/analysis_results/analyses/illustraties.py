from typing import Any

import streamlit as st

from src.utils.utils import clean_md


def _render_list(values: list) -> None:
    for item in values:
        st.markdown(f"- {clean_md(str(item))}")


_META_LABELS = {
    "type": "Type",
    "bron": "Bron",
    "toon": "Toon",
    "lowry_stadium": "Lowry",
    "buttrick_plaatsing": "Buttrick",
    "retorische_functie": "Functie",
    "doelgroep": "Doelgroep",
    "culturele_context": "Cultuur",
    "pastorale_gevoeligheid": "Pastoraal",
    "concreetheid": "Concreetheid",
    "lengte": "Lengte",
    "kernthema": "Thema",
    "actualiteit": "Actualiteit",
}


def illustraties(analysis: dict[str, Any]) -> None:
    """Render illustraties analysis result."""
    result: dict[str, Any] = analysis.get("result", {})

    preek_context: dict = result.get("preek_context", {})
    illustraties_lijst: list = result.get("illustraties", [])
    totaal: float = result.get("totaal_aantal_illustraties", len(illustraties_lijst))
    diversiteit: dict = result.get("diversiteit_analyse", {})

    # ── Preek context ─────────────────────────────────────────────────────────
    with st.expander("Preekcontext", expanded=False):
        c1, c2 = st.columns([1, 2])
        with c1:
            if preek_context.get("bijbeltekst"):
                st.markdown(f"**Bijbeltekst:** {clean_md(preek_context['bijbeltekst'])}")
            if preek_context.get("fcf_samenvatting"):
                st.markdown(f"**FCF:** {clean_md(preek_context['fcf_samenvatting'])}")
        with c2:
            if preek_context.get("gemeente_context"):
                st.markdown(f"**Gemeentecontext:** {clean_md(preek_context['gemeente_context'])}")
            themas: list = preek_context.get("kernthemas", [])
            if themas:
                st.caption("Kernthemas: " + " · ".join(themas))

    st.divider()

    # ── Totaal en diversiteitsanalyse ─────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Totaal illustraties", int(totaal))

    type_verd: dict = diversiteit.get("type_verdeling", {})
    bron_verd: dict = diversiteit.get("bron_verdeling", {})
    toon_verd: dict = diversiteit.get("toon_verdeling", {})

    with c2:
        if type_verd:
            st.markdown("**Type verdeling**")
            for k, v in type_verd.items():
                st.caption(f"{k}: {v}")
    with c3:
        if bron_verd:
            st.markdown("**Bron verdeling**")
            for k, v in bron_verd.items():
                st.caption(f"{k}: {v}")
    with c4:
        if toon_verd:
            st.markdown("**Toon verdeling**")
            for k, v in toon_verd.items():
                st.caption(f"{k}: {v}")

    st.divider()

    # ── Filter ────────────────────────────────────────────────────────────────
    alle_typen = sorted({ill.get("metadata", {}).get("type", "") for ill in illustraties_lijst if ill.get("metadata", {}).get("type")})
    filter_type = st.selectbox("Filter op type", options=["Alle"] + alle_typen, index=0)

    gefilterd = illustraties_lijst
    if filter_type != "Alle":
        gefilterd = [ill for ill in illustraties_lijst if ill.get("metadata", {}).get("type", "") == filter_type]

    st.caption(f"{len(gefilterd)} van {int(totaal)} illustraties")

    st.divider()

    # ── Illustraties ───────────────────────────────────────────────────────────
    for ill in gefilterd:
        nummer: int = ill.get("nummer", 0)
        titel: str = ill.get("titel", "")
        meta: dict = ill.get("metadata", {})
        ill_type = meta.get("type", "")

        with st.expander(f"#{nummer} — {titel}  *({ill_type})*", expanded=False):
            # Illustratie tekst
            ill_tekst: str = ill.get("illustratie_tekst", "")
            if ill_tekst:
                st.markdown(clean_md(ill_tekst))

            # Brug naar waarheid
            brug: str = ill.get("brug_naar_waarheid", "")
            if brug:
                st.info(f"**Brug naar de waarheid:** {clean_md(brug)}")

            # Metadata als compacte badge-rij
            if meta:
                badge_parts = []
                for field, label in _META_LABELS.items():
                    val = meta.get(field, "")
                    if val:
                        badge_parts.append(f"**{label}:** {val}")

                if badge_parts:
                    # Toon metadata in twee kolommen
                    left = badge_parts[: len(badge_parts) // 2 + 1]
                    right = badge_parts[len(badge_parts) // 2 + 1 :]
                    c1, c2 = st.columns(2)
                    with c1:
                        for part in left:
                            st.caption(part)
                    with c2:
                        for part in right:
                            st.caption(part)

            # Gebruiksnotities
            notities: str = ill.get("gebruiksnotities", "")
            if notities:
                st.caption(f"Gebruiksnotities: {clean_md(notities)}")
