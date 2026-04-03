from datetime import datetime
from typing import Any

import streamlit as st

from src.utils.utils import redirect_to_login, get_data, render_sidebar

redirect_to_login()

render_sidebar()

def format_title(title: str | None, congregation: str, sermon_date: str) -> str:
    if title:
        return f"{title} - {congregation} - {sermon_date}"

    return f"{congregation} - {sermon_date}"

def set_analysis_id(analysis_id: int) -> None:
    st.session_state.selected_analysis_id = analysis_id

analysis = get_data("api/sermon-analyses/")

st.title("Kerkdienstanalyses")
st.write("Overzicht van alle kerkdienstanalyses.")

new_analysis = st.button("Nieuwe analyse", type="primary")

if new_analysis:
    st.switch_page(
        f"{st.session_state['page_navigation_dir']}/analyses/new_analysis.py"
    )

if len(analysis) == 0:
    st.info("Er zijn nog geen kerkdienstanalyses gestart.")
else:
    with st.container():
        for item in analysis:
            id = item["id"]
            status = item["status"]
            title = item["title"]
            congregation = item["church"]["name"]
            sermon_date = datetime.strptime(item["sermon_date"], "%Y-%m-%d").strftime(
                "%d-%m-%Y"
            )

            st.button(
                f"{format_title(title, congregation, sermon_date)}",
                type="secondary",
                key=item["id"],
                width="stretch",
                on_click=lambda id=id: set_analysis_id(id)
            )

if "selected_analysis_id" in st.session_state:
    analysis_id = st.session_state.selected_analysis_id
    del st.session_state.selected_analysis_id
    st.switch_page(
        f'{st.session_state["page_navigation_dir"]}/analysis_results/overview.py',
        query_params={"analysis_id": analysis_id}
    )