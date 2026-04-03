from uuid import uuid4
import json

import streamlit as st

from src.models.sermon_analysis_model import SermonAnalysisModel
from src.utils.utils import get_churches, get_song_books, redirect_to_login

redirect_to_login()

def update(options: list[str]) -> None:

    st.session_state["selected_scriptures"] = options

churches = get_churches()
song_books = get_song_books()

st.header("Nieuwe analyse")

if "selected_scriptures" not in st.session_state:
    st.session_state["selected_scriptures"] = []

### FORM ###    

col1, col2 = st.columns([11,1], vertical_alignment='bottom')

with col1:
    selected_church = st.selectbox(
        "Selecteer de gemeente voor deze kerkdienstanalyse",
        options=churches,
        format_func=lambda church: church['name'])

with col2:
    new_church = st.button(":material/Add:")
    
if new_church:
    st.switch_page(f"{st.session_state['page_navigation_dir']}/churches/new_church.py", query_params={'from_page': 'new_analysis.py'})

title = st.text_input("Thema van de kerkdienstanalyse (optioneel)", max_chars=64)
sermon_date = st.date_input("Datum van de preek", format="DD-MM-YYYY")
song_books = st.multiselect(
    "Selecteer de liedboeken die in deze preek gebruikt worden (optioneel):",
    placeholder="Geen liedboeken geselecteerd",
    options=song_books,
    format_func=lambda book: book['name']
)
scriptures_choice = st.radio(
    "Schriftlezingen", options=["Kerkelijk rooster volgen", "Eigen lezingen"]
)

if scriptures_choice == "Eigen lezingen":
    scripture = st.text_input("Voeg lezing toe")
    scripture_selected = st.button("Lezing toevoegen")

    if scripture_selected:
        unique_id = str(uuid4())
        st.session_state["selected_scriptures"].append(scripture)

if len(st.session_state["selected_scriptures"]) > 0:

    st.subheader("Geselecteerde lezingen:")

    options = st.multiselect(
        "Geselecteerde lezingen:",
        options=list(st.session_state["selected_scriptures"]),
        default=list(st.session_state["selected_scriptures"])
    )
    
    update(options)
    
    extra_context = st.text_area('Extra context (optioneel):', height=150, max_chars=1024)
    
    submit = st.button("Analyse starten", type="primary")

    if submit:
        
        scriptures_string = ", ".join(st.session_state["selected_scriptures"])
        
        sermon_analysis_model = SermonAnalysisModel(
            church=selected_church['id'],
            title=title,
            sermon_date=sermon_date,
            use_calender=(scriptures_choice == "Kerkelijk rooster volgen"),
            scriptures=scriptures_string,
            song_books=[book['id'] for book in song_books],
            extra_context=extra_context
        )
        data = json.loads(sermon_analysis_model.model_dump_json())
        
        st.session_state['api_handler'].post(
            endpoint="api/sermon-analyses/",
            data=data
        )
        
        st.success("Analyse gestart! Je wordt doorgestuurd naar het dashboard.")
        
        st.switch_page(f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py")