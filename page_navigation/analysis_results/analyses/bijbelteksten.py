from typing import Any

import streamlit as st

from src.utils.utils import (
    format_verse_range,
    groepeer_samengevoegde_verzen,
    render_verse_layout,
)


def _is_hebrew(text: str) -> bool:
    return any("֐" <= ch <= "׿" for ch in text)


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

        # Vouw opeenvolgende verzen met identieke tekst samen vóór het
        # renderen — voorkomt dubbele regels bij samengevoegde verzen
        # (BGT v13-14, Hebreeuws/Grieks dat over twee versnummers loopt).
        # text_fields=("modern_text", "source_text") eist dat *beide*
        # velden gelijk zijn; alleen-NL-gelijk maar verschillende brontekst
        # blijft dan apart staan zodat de Hebreeuws/Grieks-nuances
        # zichtbaar blijven.
        groepen = groepeer_samengevoegde_verzen(
            verses, text_fields=("modern_text", "source_text")
        )
        for groep in groepen:
            label = format_verse_range(groep["numbers"])
            # `modern_text` voor weergave: rstrip houdt leading whitespace
            # intact — de Naardense Bijbel gebruikt dat als poëtische
            # inspringing. De helper deed hierboven `.strip()` alleen voor
            # de identiteits-vergelijking, niet voor de waarde zelf.
            modern_text = (groep["modern_text"] or "").rstrip()
            source_text = (groep["source_text"] or "").strip()

            st.markdown(
                f"<span style='color:grey;font-size:0.85em;font-weight:bold;'>{label}</span>"
                f"&nbsp;&nbsp;{render_verse_layout(modern_text)}",
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
