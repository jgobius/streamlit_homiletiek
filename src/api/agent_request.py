import os
from typing import Any

import streamlit as st
import requests
from requests import Response

class AgentRequest:
    
    def post(self, payload: dict[str, Any]) -> Response:
    
        headers = {
            "Authorization": f"Bearer {st.session_state['api_handler'].jwt_handler.token}",
            "Content-Type": "application/json",
        }
        
        agent_url = os.environ.get("API_AGENT_URL").rstrip("/")
        response = requests.post(
            url=f"{agent_url}/single_analysis/",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return response
