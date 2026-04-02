from __future__ import annotations

from typing import Optional

import streamlit as st

_CACHE_KEY = "user_suggestions"

_DEFAULTS = [
    "Een preekschets in de stijl van H.F. Kohlbrugge",
    "Passende poëzie, o.a. van I.G.M. (Ida) Gerhardt",
    "Meer liedbundels, waaronder 'Liefste Lied of Overzee' (Sytze de Vries)",
]


class UserSuggestions:

    @staticmethod
    def load(handler) -> list[dict]:
        """Return cached or freshly-fetched list of suggestion dicts."""
        if _CACHE_KEY in st.session_state:
            return st.session_state[_CACHE_KEY]
        try:
            suggestions = handler.get("api/user-suggestions/")
        except Exception:
            suggestions = []
        st.session_state[_CACHE_KEY] = suggestions
        return suggestions

    @staticmethod
    def _clear_cache() -> None:
        st.session_state.pop(_CACHE_KEY, None)

    @staticmethod
    def add(text: str, handler) -> None:
        """POST a new suggestion and clear cache."""
        handler.post("api/user-suggestions/", data={"text": text})
        UserSuggestions._clear_cache()

    @staticmethod
    def remove(suggestion_id: int, handler) -> None:
        """DELETE a suggestion and clear cache."""
        handler.delete(f"api/user-suggestions/{suggestion_id}/")
        UserSuggestions._clear_cache()

    @staticmethod
    def seed_defaults(handler) -> None:
        """Create default suggestions when the user has none yet."""
        for text in _DEFAULTS:
            handler.post("api/user-suggestions/", data={"text": text})
        UserSuggestions._clear_cache()


@st.dialog("Suggesties", width="small")
def _user_suggestions_dialog(handler) -> None:
    suggestions = UserSuggestions.load(handler)

    # Auto-seed defaults on first open
    if not suggestions:
        UserSuggestions.seed_defaults(handler)
        suggestions = UserSuggestions.load(handler)

    st.caption("Persoonlijke suggesties voor de analyse. Gebruik + en − om de lijst aan te passen.")

    for s in suggestions:
        col_text, col_del = st.columns([11, 1])
        with col_text:
            st.markdown(s["text"])
        with col_del:
            if st.button("−", key=f"del_sugg_{s['id']}", help="Verwijder"):
                UserSuggestions.remove(s["id"], handler)
                st.rerun(scope="fragment")

    st.divider()

    # Clear flag must be applied before the widget is instantiated
    if st.session_state.pop("_clear_suggestion_input", False):
        st.session_state["new_suggestion_input"] = ""

    col_input, col_add = st.columns([10, 1])
    with col_input:
        new_text = st.text_input(
            "Nieuwe suggestie",
            key="new_suggestion_input",
            placeholder="Typ een suggestie...",
            label_visibility="collapsed",
        )
    with col_add:
        if st.button("＋", type="primary", help="Toevoegen"):
            text = (st.session_state.get("new_suggestion_input") or "").strip()
            if text:
                UserSuggestions.add(text, handler)
                st.session_state["_clear_suggestion_input"] = True
                st.rerun(scope="fragment")

    if st.button("Sluiten", use_container_width=True):
        st.rerun()


def render_suggestions_trigger(handler) -> None:
    """Render the suggestions button in the sidebar."""
    st.divider()
    if st.button("💡 Suggesties", use_container_width=True, help="Beheer uw persoonlijke suggesties"):
        _user_suggestions_dialog(handler)
