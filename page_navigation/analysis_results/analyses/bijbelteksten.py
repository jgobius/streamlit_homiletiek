from typing import Any

import streamlit as st


def _is_hebrew(text: str) -> bool:
    return any("\u0590" <= ch <= "\u05FF" for ch in text)


def bijbelteksten(analysis: dict[str, Any]) -> None:
    """Render bijbelteksten analysis result."""
    result: Any = analysis.get("result")

    # Titel, actieknoppen én de afsluitende scheidingslijn worden centraal in
    # overview.py getoond, zodat alle tabs dezelfde kop hebben
    # (titel → actieknoppen → lijn → inhoud). Deze renderer begint daarom
    # direct met de eigen inhoud.

    # `result` is een lijst van lezing-entries in liturgische leesvolgorde
    # (eerste lezing → psalm → tweede lezing → evangelie). Elke entry heeft
    # een 'reference'-veld met de originele referentie. We gebruiken een
    # lijst in plaats van een dict-op-referentie omdat Postgres jsonb
    # object-key-volgorde niet bewaart, maar list-volgorde wél.
    if not isinstance(result, list):
        st.info("Nog geen bijbeltekst beschikbaar.")
        return

    for scripture in result:
        if not isinstance(scripture, dict):
            continue
        scripture_ref = (scripture.get("reference") or "").rstrip(".").strip()
        st.subheader(scripture_ref)
        verses: list[dict] = scripture.get("verses", [])

        for verse in verses:
            number = verse.get("number", "")
            modern_text = (verse.get("modern_text") or "").strip()
            source_text = (verse.get("source_text") or "").strip()

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
