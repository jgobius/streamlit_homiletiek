import streamlit as st

from src.utils.utils import redirect_to_login, get_data
from page_navigation.analysis_results.analyses.postille import postille
from page_navigation.analysis_results.analyses.bijbelteksten import bijbelteksten
from page_navigation.analysis_results.analyses.liturgisch_jaar import liturgisch_jaar
from page_navigation.analysis_results.analyses.liedsuggesties import liedsuggesties
from page_navigation.analysis_results.analyses.structuralistische_exegese import structuralistische_exegese
from page_navigation.analysis_results.analyses.commentaren import commentaren
from page_navigation.analysis_results.analyses.theologie import theologie

redirect_to_login()

analysis_id = st.query_params.get('analysis_id')

if not analysis_id:
    st.warning("Geen analyse geselecteerd. Ga terug naar het overzicht en selecteer een analyse.")
    st.stop()

analysis_results = get_data(f"api/analysis-results?sermon_analysis_id={analysis_id}")

if not analysis_results:
    st.info("Er zijn nog geen analyseresultaten beschikbaar voor deze preekanalyse.")
    st.stop()

summary  = [r for r in analysis_results if r['analysis_type']['name'] == "postille"]
other_results = [r for r in analysis_results if r['id'] != summary[0]['id']]
summary.extend(other_results)


with st.sidebar:
    st.page_link(label="< Terug", page=f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py")

    selected_analysis = st.radio(
        "Analyse",
        options=summary,
        format_func=lambda x: x['analysis_type']['front_end_name'],
        label_visibility="collapsed",
    )

@st.dialog("Extra context")
def extra_context_dialog() -> None:
    st.text_area("Geef extra context voor deze analyse", key="extra_context_input", height=200)
    if st.button("Opslaan", type="primary"):
        st.session_state["extra_context"] = st.session_state["extra_context_input"]
        st.rerun()
_, btn_col = st.columns([7, 3])
with btn_col:
    if st.button("Extra context", icon="✏️", use_container_width=True):
        extra_context_dialog()

if st.session_state.get("extra_context"):
    st.info(f"**Extra context:** {st.session_state['extra_context']}")

if not selected_analysis:
    st.stop()

# st.write(analysis_results)
analysis_type_name = selected_analysis.get("analysis_type", {}).get("name", "")

if analysis_type_name == "postille":
    postille(selected_analysis)
elif analysis_type_name == "bijbelteksten":
    bijbelteksten(selected_analysis)
elif analysis_type_name == "liturgisch_jaar":
    liturgisch_jaar(selected_analysis)
elif analysis_type_name == "liedsuggesties":
    liedsuggesties(selected_analysis)
elif analysis_type_name == "structuralistische_exegese":
    structuralistische_exegese(selected_analysis)
elif analysis_type_name == "commentaries":
    commentaren(selected_analysis)
elif analysis_type_name == "theology":
    theologie(selected_analysis)


