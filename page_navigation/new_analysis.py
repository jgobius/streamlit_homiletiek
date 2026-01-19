from uuid import uuid4

import streamlit as st

from src.models.sermon_analysis_model import SermonAnalysisModel

def update(options: list[str]) -> None:

    st.session_state["selected_scriptures"] = options


st.header("Contextanalyse")

if "selected_scriptures" not in st.session_state:
    st.session_state["selected_scriptures"] = []

title = st.text_input("Titel van de preekanalyse", max_chars=64)
place = st.text_input("Plaatsnaam gemeente", max_chars=64)
congregation = st.text_input("Naam gemeente", max_chars=64)
datum = st.date_input("Datum van de preek", format="DD-MM-YYYY")
website = st.text_input("Website van de gemeente (optioneel)", max_chars=64)
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
        
        sermon_analysis_model = SermonAnalysisModel(
            title=title,
            place=place,
            congregation=congregation,
            sermon_date=datum,
            website=website if website else None,
            scriptures=st.session_state["selected_scriptures"],
            extra_context=extra_context if extra_context else None
        )
        
        st.write(sermon_analysis_model.model_dump())
        
        st.success("Analyse gestart! Je wordt doorgestuurd naar het dashboard.")