import requests
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

with st.sidebar:
    st.page_link(label="< Terug", page=f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py")

if not analysis_id:
    st.warning("Geen analyse geselecteerd. Ga terug naar het overzicht en selecteer een analyse.")
    st.stop()

analysis_results = get_data(f"api/analysis-results?sermon_analysis_id={analysis_id}")

if not analysis_results:
    st.info("Er zijn nog geen analyseresultaten beschikbaar voor deze preekanalyse.")
    if st.button("Start analyse", type="primary"):
        agent_url = st.secrets["API_AGENT_URL"].rstrip("/")
        response = requests.post(
            f"{agent_url}/context_graph/",
            json={"sermon_analysis_id": int(analysis_id)},
        )
        if response.status_code == 200:
            st.success("Analyse gestart. Ververs de pagina over enkele minuten.")
        else:
            st.error(f"Fout bij starten analyse: {response.text}")
    st.stop()

# Houd per analysis_type alleen de nieuwste (hoogste id).
latest: dict[str, dict] = {}
for r in analysis_results:
    name = r['analysis_type']['name']
    if name not in latest or r['id'] > latest[name]['id']:
        latest[name] = r

summary = [latest["postille"]] if "postille" in latest else []
other_results = [r for name, r in latest.items() if name != "postille"]
summary.extend(other_results)

if "selected_analysis_id" not in st.session_state or st.session_state["selected_analysis_id"] not in {r["id"] for r in summary}:
    st.session_state["selected_analysis_id"] = summary[0]["id"] if summary else None

with st.sidebar:
    for r in summary:
        label = r["analysis_type"]["front_end_name"]
        is_selected = r["id"] == st.session_state["selected_analysis_id"]
        if is_selected:
            st.markdown(f"**→ {label}**")
        else:
            if st.button(label, key=f"nav_{r['id']}", use_container_width=True):
                st.session_state["selected_analysis_id"] = r["id"]
                st.rerun()

selected_analysis = next((r for r in summary if r["id"] == st.session_state["selected_analysis_id"]), None)

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


