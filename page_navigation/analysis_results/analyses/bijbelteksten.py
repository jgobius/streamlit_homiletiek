from typing import Any

import streamlit as st


def _is_hebrew(text: str) -> bool:
    return any("\u0590" <= ch <= "\u05FF" for ch in text)


@st.dialog("Extra context bewerken")
def _extra_context_dialog() -> None:
    """Dialoog om de extra context van de kerkdienstanalyse te bewerken."""
    new_val = st.text_area(
        "Extra context",
        value=st.session_state.get("extra_context", ""),
        height=150,
        max_chars=1024,
        label_visibility="collapsed",
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Opslaan", type="primary", use_container_width=True):
            try:
                sermon_analysis_id = st.session_state.get("current_analysis_id")
                st.session_state["api_handler"].patch(
                    f"api/sermon-analyses/{sermon_analysis_id}/",
                    data={"extra_context": new_val},
                )
                st.session_state["extra_context"] = new_val
                # Markeer de cache als vervuild zodat de pagina opnieuw laadt.
                st.session_state["analysis_data_dirty"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Fout bij opslaan: {e}")
    with col2:
        if st.button("Annuleren", use_container_width=True):
            st.rerun()


def _render_scripture(result: dict[str, Any]) -> None:
    """Render één bijbeltekst op basis van de huidige data-structuur.

    De agent levert: boek, hoofdstuk, pericoop {van_vers, tot_vers},
    verzen [{versnummer, tekst_modern, tekst_bron, annotaties}].
    """
    boek = result.get("boek", "")
    hoofdstuk = result.get("hoofdstuk", "")
    pericoop = result.get("pericoop", {})

    # Bouw de referentie-header op uit boek, hoofdstuk en pericoop-versbereik.
    if isinstance(pericoop, dict) and pericoop.get("van_vers") and pericoop.get("tot_vers"):
        ref = f"{boek} {hoofdstuk}:{pericoop['van_vers']}–{pericoop['tot_vers']}"
    elif boek and hoofdstuk:
        ref = f"{boek} {hoofdstuk}"
    else:
        ref = boek or str(hoofdstuk)

    st.subheader(ref)

    verzen: list[dict] = result.get("verzen", [])
    for vers in verzen:
        versnummer = vers.get("versnummer", "")
        tekst_modern = vers.get("tekst_modern", "").strip()
        tekst_bron = vers.get("tekst_bron", "").strip()

        st.markdown(
            f"<span style='color:grey;font-size:0.85em;font-weight:bold;'>{versnummer}</span>"
            f"&nbsp;&nbsp;{tekst_modern}",
            unsafe_allow_html=True,
        )
        if tekst_bron:
            is_heb = _is_hebrew(tekst_bron)
            direction = "rtl" if is_heb else "ltr"
            align = "right" if is_heb else "left"
            st.markdown(
                f"<p style='color:#888;font-size:0.8em;font-style:italic;"
                f"direction:{direction};text-align:{align};margin-top:2px;'>"
                f"{tekst_bron}</p>",
                unsafe_allow_html=True,
            )

    st.write("")


def bijbelteksten(analysis: dict[str, Any]) -> None:
    """Render bijbelteksten analysis result."""
    result: dict[str, Any] = analysis.get("result", {})

    st.title("Bijbelteksten")

    # Extra context knop direct onder de titel.
    _, btn_col = st.columns([7, 3])
    with btn_col:
        if st.button("Extra context", icon="✏️", use_container_width=True):
            _extra_context_dialog()

    st.divider()

    if not result:
        st.info("Nog geen bijbeltekst beschikbaar.")
        return

    # Result is een lijst van teksten (meerdere lezingen) of één tekst-dict.
    if isinstance(result, list):
        for tekst in result:
            if isinstance(tekst, dict):
                _render_scripture(tekst)
    elif isinstance(result, dict):
        _render_scripture(result)
