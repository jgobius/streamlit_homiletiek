from __future__ import annotations

from typing import Optional

import streamlit as st

_RATING_LABELS = ["Slecht", "Matig", "Redelijk", "Goed", "Uitstekend"]
_CACHE_PREFIX = "user_feedback_"


class UserFeedback:

    @staticmethod
    def _cache_key(analysis_result_id: int) -> str:
        return f"{_CACHE_PREFIX}{analysis_result_id}"

    @staticmethod
    def load(analysis_result_id: int, handler) -> Optional[dict]:
        """Return cached or freshly-fetched feedback dict, or None if none exists."""
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
        """POST (upsert) feedback. Clears cache entry on success."""
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

    current_index = (existing["rating"] - 1) if existing else 2  # default: Redelijk
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
    )

    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("Opslaan", type="primary", use_container_width=True):
            try:
                UserFeedback.save(analysis_result_id, rating_value, text, handler)
                st.toast("Feedback opgeslagen.")
                st.rerun()
            except Exception as e:
                st.error(f"Fout bij opslaan: {e}")
    with col_cancel:
        if st.button("Annuleren", use_container_width=True):
            st.rerun()


def render_feedback_trigger(
    analysis_result_id: int,
    section_name: str,
    handler,
    key: str,
) -> None:
    """Render a divider and subtle feedback button. Opens the feedback dialog on click."""
    st.divider()
    existing = UserFeedback.load(analysis_result_id, handler)
    label = "💬 Feedback aanpassen" if existing else "💬 Geef feedback"
    if st.button(label, type="secondary", key=key):
        _user_feedback_dialog(analysis_result_id, section_name, handler)
