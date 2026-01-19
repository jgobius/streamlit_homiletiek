import streamlit as st

from src.utils.utils import redirect_to_login

redirect_to_login()


analysis = [
    {
        "title": "Analyse 1",
        "date": "2024-06-01",
        "congregation": "Gemeente A",
    },
    {
        "title": "Analyse 2",
        "date": "2024-05-15",
        "congregation": "Gemeente B",
    },
    {
        "title": "Analyse 3",
        "date": "2024-04-20",
        "congregation": "Gemeente C",
    },
]


st.title("Preekanalyses")

new_analysis = st.button("Nieuwe analyse", type="primary")

if new_analysis:
    st.switch_page(f"{st.session_state['page_navigation_dir']}/new_analysis.py")

with st.container():
    for item in analysis:
        with st.expander(f"{item['title']} - {item['congregation']} ({item['date']})"):
            st.write(f"**Gemeente:** {item['congregation']}")
            st.write(f"**Datum:** {item['date']}")
            st.write("**Details van de analyse komen hier.**")