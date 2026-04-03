from typing import Any

import streamlit as st


def _is_hebrew(text: str) -> bool:
    return any("\u0590" <= ch <= "\u05FF" for ch in text)


def bijbelteksten(analysis: dict[str, Any]) -> None:
    """Render bijbelteksten analysis result."""
    result: dict[str, Any] = analysis.get("result", {})
    sermon: dict[str, Any] = analysis.get("sermon_analysis", {})

    if sermon.get("sermon_date"):
        st.caption(f"**Preekdatum:** {sermon['sermon_date']}")

    st.divider()

    for scripture_ref, scripture_data in result.items():
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
