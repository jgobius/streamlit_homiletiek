import json
from typing import Any

import streamlit as st

from src.models.sermon_analysis_model import SermonAnalysisModel
from src.utils.utils import (
    get_data,
    get_cached_data,
    redirect_to_login,
    get_structured_scriptures,
    save_scriptures,
    load_scriptures
)

redirect_to_login()

########### DEFINE FUNCTIONS ###########

@st.dialog('Details roosterlezing')
def show_scripture_details(scripture: dict[str, Any]) -> None:

    st.markdown(f'**Eerste lezing:**\t{scripture.get("first_scripture")}')
    st.markdown(f'**Tweede lezing:**\t{scripture.get("second_scripture")}')
    st.markdown(f'**Psalm:**\t{scripture.get("psalm")}')
    st.markdown(f'**Evangelie:**\t{scripture.get("gospel")}')
    
def update(options: list[str]) -> None:
    st.session_state["selected_scriptures"] = options
    
def clean_up_session_state() -> None:
    keys_to_remove = ["selected_scriptures", "structured_scriptures", "scriptures_approved"]
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]

########### GET DATA ###########

churches = get_data("api/churches/")
song_books = get_cached_data("api/song-books/")
bible_versions = get_cached_data("api/bible-versions/")
liturgy = get_cached_data("api/liturgy/")

st.header("Nieuwe analyse")

if "selected_scriptures" not in st.session_state:
    st.session_state["selected_scriptures"] = []

if "structured_scriptures" not in st.session_state:
    st.session_state["structured_scriptures"] = []

### FORM ###

col1, col2 = st.columns([11, 1], vertical_alignment="bottom")

with col1:
    selected_church = st.selectbox(
        "Selecteer de gemeente voor deze preekanalyse",
        options=churches,
        format_func=lambda church: church["name"],
    )

with col2:
    new_church = st.button(":material/Add:")

if new_church:
    st.switch_page(
        f"{st.session_state['page_navigation_dir']}/churches/new_church.py",
        query_params={"from_page": "new_analysis.py"},
    )

title = st.text_input("Thema (optioneel)", max_chars=64)
sermon_date = st.date_input("Datum van de preek", format="DD-MM-YYYY", min_value='today')
song_books = st.multiselect(
    "Selecteer de liedboeken die in deze preek gebruikt worden (optioneel):",
    placeholder="Geen liedboeken geselecteerd",
    options=song_books,
    format_func=lambda book: book["name"],
)

bible_version = st.selectbox(
    "Selecteer de bijbelvertaling die in deze preek gebruikt wordt (optioneel):",
    placeholder="Geen bijbelvertaling geselecteerd",
    options=bible_versions,
    format_func=lambda version: version["version"],
)

core_scripture = st.text_input("Voeg een kernlezing toe (optioneel)", max_chars=64, value="", placeholder="Geen kernlezing toegevoegd")


scriptures_choice = st.radio(
    "Schriftlezingen", options=["Kerkelijk rooster volgen", "Eigen lezingen"]
)

if scriptures_choice == "Kerkelijk rooster volgen":
    
    selected_liturgy = [l for l in liturgy if l.get('date') == sermon_date.strftime('%Y-%m-%d')]
    
    if len(selected_liturgy) == 0:
        st.warning("Er zijn geen roosterlezingen gevonden voor de geselecteerde datum. Kies een andere datum of selecteer 'Eigen lezingen' om handmatig lezingen toe te voegen.")
    else:
        st.session_state["selected_scripture_id"] = selected_liturgy[0].get("id")
        show_scriptures = st.button("Roosterlezingen tonen")
        if show_scriptures:
            show_scripture_details(selected_liturgy[0])


if scriptures_choice == "Eigen lezingen":
    options = st.multiselect(
        "Geselecteerde lezingen:",
        placeholder="Geen lezingen geselecteerd",
        options=[],
        accept_new_options=True
    )
    update(options)

extra_context = st.text_area(
    "Extra context (optioneel):", height=150, max_chars=1024
)

collect_structured_scriptures = st.button("Lezingen ophalen")

if collect_structured_scriptures:

    with st.status("Lezingen structureren (afhankelijk van het aantal lezingen kan dit even duren)..."):
    
        st.session_state['structured_scriptures'] = get_structured_scriptures(
            scriptures=st.session_state["selected_scriptures"],
            bible_version=bible_version.get('version'),
            language="nl",
        )
        
        # st.session_state['structured_scriptures'] = load_scriptures()

    # save_scriptures(structured_scriptures)
    
for scripture in st.session_state['structured_scriptures']:
    
    with st.expander(f"**{scripture.get('original_scripture')}**", expanded=False):
    
        for sc in scripture.get("scriptures"):
            st.markdown(f"Hoofdstuk **{sc.get('chapter')}**")
            for verse in sc.get("verses", []):
                st.markdown(f"**{verse.get('number')}**")
                st.markdown(f"{verse.get('text')}")
        
            st.write("---")
    
if 'structured_scriptures' in st.session_state and len(st.session_state['structured_scriptures']) > 0:

    st.session_state['scriptures_approved'] = st.checkbox("Ik bevestig dat de date zoals hierboven vermeldt, correct zijn en klaar voor analyse", value=False)


submit = st.button("Analyse starten", type="primary")

if submit:
    sermon_analysis_model = SermonAnalysisModel(
        church=selected_church['id'],
        title=title,
        sermon_date=sermon_date,
        liturgy=st.session_state.get("selected_scripture_id"),
        core_scriptures=core_scripture,
        scripture_json=st.session_state.get('structured_scriptures'),
        use_calender=(scriptures_choice == "Kerkelijk rooster volgen"),
        song_books=[book['id'] for book in song_books],
        extra_context=extra_context
    )
    data = json.loads(sermon_analysis_model.model_dump_json())

    st.session_state['api_handler'].post(
        endpoint="api/sermon-analyses/",
        data=data
    )
    
    clean_up_session_state()
    
    st.success("Analyse gestart! Je wordt doorgestuurd naar het dashboard.")

    st.switch_page(f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py")
