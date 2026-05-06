from __future__ import annotations

import json
from typing import Optional

import streamlit as st

from src.utils.utils import valideer_tekstinvoer

_RATING_LABELS = ["Slecht", "Matig", "Redelijk", "Goed", "Uitstekend"]
_CACHE_PREFIX = "user_feedback_"

# Max-woorden voor feedback-toelichting. Genoeg voor een paragraaf commentaar,
# niet bedoeld als lange tekstplek (daar zijn aparte analyse-velden voor).
_MAX_WOORDEN_FEEDBACK = 500


class UserFeedback:

    @staticmethod
    def _cache_key(analysis_result_id: int) -> str:
        return f"{_CACHE_PREFIX}{analysis_result_id}"

    @staticmethod
    def load(analysis_result_id: int, handler) -> Optional[dict]:
        """Geeft gecachte of vers opgehaalde feedback, of None als er geen is."""
        key = UserFeedback._cache_key(analysis_result_id)
        if key in st.session_state:
            return st.session_state[key]
        try:
            results = handler.get(
                "api/user-feedback/",
                params={"analysis_result_id": analysis_result_id},
            )
            feedback = results[0] if results else None
        except Exception:
            feedback = None
        st.session_state[key] = feedback
        return feedback

    @staticmethod
    def save(analysis_result_id: int, rating: int, text: str, handler) -> None:
        """POST (upsert) feedback. Verwijdert cache-entry bij succes."""
        handler.post(
            "api/user-feedback/",
            data={
                "analysis_result": analysis_result_id,
                "rating": rating,
                "text": text,
            },
        )
        st.session_state.pop(UserFeedback._cache_key(analysis_result_id), None)


@st.dialog("Feedback", width="small")
def _user_feedback_dialog(
    analysis_result_id: int,
    section_name: str,
    handler,
) -> None:
    existing = UserFeedback.load(analysis_result_id, handler)

    st.markdown(f"**{section_name}**")
    st.caption("Hoe beoordeel je dit analyseresultaat?")

    # Standaard op 'Redelijk' (index 2) als er nog geen beoordeling is
    current_index = (existing["rating"] - 1) if existing else 2
    rating_label = st.radio(
        "Beoordeling",
        options=_RATING_LABELS,
        index=current_index,
        horizontal=True,
        label_visibility="collapsed",
    )
    rating_value = _RATING_LABELS.index(rating_label) + 1

    text = st.text_area(
        "Toelichting (optioneel)",
        value=existing["text"] if existing else "",
        placeholder="Voeg een toelichting toe...",
        height=120,
        max_chars=4096,
    )

    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("Opslaan", type="primary", use_container_width=True):
            # Valideer de toelichting op maximaal aantal woorden en op
            # verdachte SQL-injectie-patronen voordat we POST'en.
            ok, fout = valideer_tekstinvoer(
                text or "",
                max_woorden=_MAX_WOORDEN_FEEDBACK,
                veldnaam="Toelichting",
            )
            if not ok:
                st.error(fout)
                return
            try:
                UserFeedback.save(analysis_result_id, rating_value, text, handler)
                st.toast("Feedback opgeslagen.")
                st.rerun()
            except Exception as e:
                st.error(f"Fout bij opslaan: {e}")
    with col_cancel:
        if st.button("Annuleren", use_container_width=True):
            st.rerun()


def _normalize_newlines(value: str) -> str:
    """Normaliseer Windows-/oude-Mac-regeleindes naar \n zodat Streamlit de tekst
    daadwerkelijk over meerdere regels rendert. In de database staat veelal \r\n."""
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _render_wrapped_text(text: str, key: str) -> None:
    """Render een leesbaar tekstvak met line-wrap en behoud van regeleindes.

    Een gewone st.text_area (niet disabled) wraps correct, behoudt regeleindes en
    blijft goed leesbaar. Disabled=True gaf een grijze waas over de tekst. De
    inhoud is puur debug-weergave — eventuele bewerkingen gaan nergens heen.
    Hoogte schaalt mee met de tekst tot max 600px.
    """
    normalized = _normalize_newlines(text)
    # Hoogte schat op basis van regelaantal; bovengrens voorkomt absurde popups.
    regels = max(5, normalized.count("\n") + 2)
    hoogte = min(600, regels * 22)
    st.text_area(
        label=key,
        value=normalized,
        height=hoogte,
        key=key,
        label_visibility="collapsed",
    )


@st.dialog("LLM-prompt (debug)", width="large")
def _prompt_debug_dialog(analysis: dict) -> None:
    """Toon het LLM-prompt zoals opgeslagen in de database voor deze analyse.

    Tijdelijke debug-hulp: het prompt wordt bij elke analyse-run in AnalysisResult.prompt
    (JSONField) bewaard. We renderen elke string-waarde expliciet als code-block met
    echte regeleindes; alleen niet-string-waarden worden als JSON getoond. Zo blijven
    meerregelige prompts leesbaar i.p.v. één lange regel met \\r\\n-escapes.
    """
    analysis_type = analysis.get("analysis_type", {}) or {}
    naam = analysis_type.get("front_end_name") or analysis_type.get("name", "")
    st.markdown(f"**{naam}** — analysis_result id `{analysis.get('id')}`")
    prompt = analysis.get("prompt")
    if prompt is None or prompt == {} or prompt == "":
        st.info("Geen prompt opgeslagen voor deze analyse.")
        return

    analysis_id = analysis.get("id", "x")
    if isinstance(prompt, dict):
        # Per sleutel renderen zodat lange multiline-waardes (volledige_prompt e.d.)
        # niet door json.dumps als één regel met \r\n-escapes verschijnen.
        # system_prompt wordt overgeslagen: de inhoud zit al in volledige_prompt,
        # dus dubbel tonen is overbodig en maakt de dialog onnodig lang.
        for key, value in prompt.items():
            if key == "system_prompt":
                continue
            st.markdown(f"**`{key}`**")
            widget_key = f"prompt_debug_{analysis_id}_{key}"
            if isinstance(value, str):
                _render_wrapped_text(value, key=widget_key)
            else:
                _render_wrapped_text(
                    json.dumps(value, indent=2, ensure_ascii=False),
                    key=widget_key,
                )
    elif isinstance(prompt, list):
        _render_wrapped_text(
            json.dumps(prompt, indent=2, ensure_ascii=False),
            key=f"prompt_debug_{analysis_id}_list",
        )
    elif isinstance(prompt, str):
        _render_wrapped_text(prompt, key=f"prompt_debug_{analysis_id}_str")
    else:
        _render_wrapped_text(str(prompt), key=f"prompt_debug_{analysis_id}_raw")


def render_analysis_footer(
    analysis: dict,
    handler,
    key_prefix: str,
) -> None:
    """Render scheidingslijn + feedbackknop en prompt-debugknop naast elkaar.

    Wordt onder elke analyse getoond zodat de gebruiker feedback kan geven én
    (tijdelijk, voor debugdoeleinden) het door het LLM gebruikte prompt kan
    inspecteren. `analysis` is het volledige analyseresultaat-dict uit de API
    (inclusief het JSON-veld `prompt`).
    """
    # Vroeger st.divider(); vervangen door whitespace omdat de feedbackknop een
    # eigen rand en achtergrond heeft. Op feedback-pagina's leverde die extra
    # grijze streep een derde of vierde horizontale lijn op één pagina op.
    st.write("")
    analysis_result_id = int(analysis["id"])
    analysis_type = analysis.get("analysis_type", {}) or {}
    section_name = (
        analysis_type.get("front_end_name") or analysis_type.get("name", "")
    )
    existing = UserFeedback.load(analysis_result_id, handler)
    feedback_label = "💬 Feedback aanpassen" if existing else "💬 Geef feedback"

    # De debug-knop "Prompt bekijken" is bedoeld voor ontwikkel-/beheerinzicht
    # en mag niet zichtbaar zijn voor gewone gebruikers. is_superuser wordt bij
    # inloggen in session_state gezet vanuit /api/user-preferences/ (zie main.py).
    # Voor superusers tonen we twee kolommen (feedback + debug); voor reguliere
    # gebruikers renderen we de feedback-knop over de volle breedte, zonder
    # lege kolom ernaast.
    is_superuser = bool(st.session_state.get('is_superuser', False))
    if is_superuser:
        col_feedback, col_debug = st.columns(2)
        with col_feedback:
            if st.button(
                feedback_label,
                type="secondary",
                key=f"{key_prefix}_feedback_{analysis_result_id}",
                use_container_width=True,
            ):
                _user_feedback_dialog(analysis_result_id, section_name, handler)
        with col_debug:
            if st.button(
                "🐞 Prompt bekijken (debug)",
                type="secondary",
                key=f"{key_prefix}_prompt_{analysis_result_id}",
                use_container_width=True,
            ):
                _prompt_debug_dialog(analysis)
    else:
        if st.button(
            feedback_label,
            type="secondary",
            key=f"{key_prefix}_feedback_{analysis_result_id}",
            use_container_width=True,
        ):
            _user_feedback_dialog(analysis_result_id, section_name, handler)
