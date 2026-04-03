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


def set_scripture(scriptures: list[dict[str, Any]]) -> str:

    if len(scriptures) == 0:
        return ""

    scripture_str = ""
    for scripture in scriptures:
        book = scripture["start_verse"]["scripture_book"]["book"]
        chapter = scripture["start_verse"]["chapter"]["value"]
        verse_start = scripture["start_verse"]["number"]["value"]
        verse_end = scripture["end_verse"]["number"]["value"]

        if verse_start == verse_end:
            scripture_str += f"{book} {chapter}:{verse_start}, "
        else:
            scripture_str += f"{book} {chapter}:{verse_start}-{verse_end}, "

    return scripture_str.rstrip(", ")


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
            status = item["status"]
            title = item["title"]
            congregation = item["church"]["name"]
            sermon_date = datetime.strptime(item["sermon_date"], "%Y-%m-%d").strftime(
                "%d-%m-%Y"
            )
            scriptures = item["scripture_json"]

            st.button(
                f"{format_title(title, congregation, sermon_date)}",
                type="secondary",
                key=item["id"],
                width="stretch",
                on_click=lambda item=item: st.session_state.update(
                    {"selected_analysis": item}
                ),
            )