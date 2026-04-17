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


def bijbelteksten(analysis: dict[str, Any]) -> None:
    """Render bijbelteksten analysis result."""
    result: dict[str, Any] = analysis.get("result", {})

    # De analytische naam tonen als paginatitel.
    st.title("Bijbelteksten")

    # Extra context knop direct onder de titel, zodat de gebruiker context kan bekijken of aanpassen.
    _, btn_col = st.columns([7, 3])
    with btn_col:
        if st.button("Extra context", icon="✏️", use_container_width=True):
            _extra_context_dialog()

    st.divider()

    for scripture_ref, scripture_data in result.items():
        # Sla niet-dict waarden over (bijv. metadata-velden op het root-niveau van result).
        if not isinstance(scripture_data, dict):
            continue
        st.subheader(scripture_ref.rstrip(".").strip())
        verses: list[dict] = scripture_data.get("verses", [])

        for verse in verses:
            number = verse.get("number", "")
            modern_text = verse.get("modern_text", "").strip()
            source_text = verse.get("source_text", "").strip()

            st.markdown(
                f"<span style='color:grey;font-size:0.85em;font-weight:bold;'>{number}</span>"
                f"&nbsp;&nbsp;{modern_text}",
                unsafe_allow_html=True,
            )
            if source_text:
                is_heb = _is_hebrew(source_text)
                direction = "rtl" if is_heb else "ltr"
                align = "right" if is_heb else "left"
                st.markdown(
                    f"<p style='color:#888;font-size:0.8em;font-style:italic;"
                    f"direction:{direction};text-align:{align};margin-top:2px;'>"
                    f"{source_text}</p>",
                    unsafe_allow_html=True,
                )

        st.write("")
