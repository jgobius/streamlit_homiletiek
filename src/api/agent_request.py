import os
from typing import Any

import streamlit as st
import requests
from requests import Response


class AgentRequest:
    """Wrapper voor POST-aanroepen naar de FastAPI-agent met JWT-injectie.

    Alle agent-endpoints (single_analysis, run_single_analysis,
    original_scriptures, structured_scripture, address-lookup) verwachten
    een Bearer-token; door alle aanroepen via deze klasse te leiden staat
    de header-opbouw op één plek (DRY) en is een vergeten Authorization-
    header bij een nieuw endpoint niet meer mogelijk.
    """

    def post(
        self,
        endpoint: str,
        payload: dict[str, Any],
        timeout: int = 30,
        headers: dict[str, str] | None = None,
    ) -> Response:
        # Lstrip '/' zodat zowel "single_analysis/" als "/single_analysis/" werkt
        # voor de caller; de URL-samenstelling blijft zo idempotent.
        endpoint_clean = endpoint.lstrip("/")

        agent_url = os.environ.get("API_AGENT_URL").rstrip("/")
        response = requests.post(
            url=f"{agent_url}/{endpoint_clean}",
            headers=headers if headers is not None else self.auth_header(),
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        return response
    
    def get(self, endpoint: str, timeout: int, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Response:
        endpoint_clean = endpoint.lstrip("/")
        agent_url = os.environ.get("API_AGENT_URL").rstrip("/")
        response = requests.get(
            url=f"{agent_url}/{endpoint_clean}",
            headers=headers if headers is not None else self.auth_header(),
            params=params,
            timeout=timeout
        )
        response.raise_for_status()
        return response

    def auth_header(self) -> dict[str, str]:
        """Geef de Bearer-headers terug voor scenario's waarin .post() niet past.

        Specifiek voor de parallelle structured_scripture-aanroep in
        src/utils/utils.py: daar wordt het token één keer in de hoofdthread
        gesnapshotted om race-condities op JwtHandler.token (de @property kan
        een refresh triggeren) in worker-threads te vermijden.
        """
        return {
            "Authorization": f"Bearer {st.session_state['api_handler'].jwt_handler.token}",
            "Content-Type": "application/json",
        }
