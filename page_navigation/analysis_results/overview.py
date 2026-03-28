import requests
import streamlit as st

from src.utils.utils import redirect_to_login, get_data
from page_navigation.analysis_results.aanpassen_dialog import aanpassen_dialog
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

all_analysis_types = get_data("api/analysis-types/")
missing_types = sorted(
    [at for at in all_analysis_types if at.get("front_end_name") and at["name"] not in latest],
    key=lambda x: x.get("order", 99),
)

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

    if missing_types:
        st.divider()
        with st.expander("Analyse toevoegen"):
            for at in missing_types:
                if st.button(at["front_end_name"], key=f"add_{at['name']}", use_container_width=True):
                    try:
                        agent_url = st.secrets["API_AGENT_URL"].rstrip("/")
                        response = requests.post(
                            f"{agent_url}/run_single_analysis/",
                            json={
                                "sermon_analysis_id": int(analysis_id),
                                "analysis_type_name": at["name"],
                            },
                        )
                        response.raise_for_status()
                        st.toast(f"'{at['front_end_name']}' wordt uitgevoerd. Ververs de pagina over enkele minuten.")
                    except Exception as e:
                        st.error(f"Fout: {e}")

selected_analysis = next((r for r in summary if r["id"] == st.session_state["selected_analysis_id"]), None)

@st.dialog("Analyse-element verwijderen")
def confirm_delete_result(result: dict) -> None:
    label = result["analysis_type"]["front_end_name"]
    st.write(f"Weet je zeker dat je **'{label}'** wilt verwijderen? Dit kan niet ongedaan worden gemaakt.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ja, verwijderen", type="primary", use_container_width=True):
            try:
                handler = st.session_state['api_handler']
                sermon_analysis_id = result["sermon_analysis"]["id"]
                url = f"{handler.base_url}/api/analysis-results/{result['id']}/?sermon_analysis_id={sermon_analysis_id}"
                headers = {"Authorization": f"Bearer {handler.jwt_handler.token}"}
                requests.delete(url, headers=headers).raise_for_status()
                st.session_state.pop("selected_analysis_id", None)
                st.rerun()
            except Exception as e:
                st.error(f"Fout bij verwijderen: {e}")
    with col2:
        if st.button("Annuleren", use_container_width=True):
            st.rerun()


@st.dialog("Analyse opnieuw uitvoeren")
def confirm_rerun_analysis(sermon_analysis_id: int, analysis_type_name: str, front_end_name: str) -> None:
    st.write(f"Weet je zeker dat je **'{front_end_name}'** opnieuw wilt uitvoeren? Dit kan enkele minuten duren.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ja, opnieuw uitvoeren", type="primary", use_container_width=True):
            try:
                agent_url = st.secrets["API_AGENT_URL"].rstrip("/")
                response = requests.post(
                    f"{agent_url}/run_single_analysis/",
                    json={
                        "sermon_analysis_id": sermon_analysis_id,
                        "analysis_type_name": analysis_type_name,
                    },
                )
                response.raise_for_status()
                st.success(f"'{front_end_name}' wordt opnieuw uitgevoerd. Ververs de pagina over enkele minuten.")
                st.rerun()
            except Exception as e:
                st.error(f"Fout bij starten analyse: {e}")
    with col2:
        if st.button("Annuleren", use_container_width=True):
            st.rerun()


@st.dialog("Liedsuggesties opnieuw uitvoeren")
def confirm_rerun_liedsuggesties(sermon_analysis_id: int) -> None:
    all_books = get_data("api/song-books/")
    selected = st.multiselect(
        "Selecteer liedbundels (20 suggesties per bundel):",
        options=all_books,
        format_func=lambda b: b["name"],
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Uitvoeren", type="primary", use_container_width=True):
            if not selected:
                st.warning("Selecteer minimaal één liedbundel.")
                return
            try:
                agent_url = st.secrets["API_AGENT_URL"].rstrip("/")
                response = requests.post(
                    f"{agent_url}/run_single_analysis/",
                    json={
                        "sermon_analysis_id": sermon_analysis_id,
                        "analysis_type_name": "liedsuggesties",
                        "song_books": [b["id"] for b in selected],
                    },
                )
                response.raise_for_status()
                st.success("Liedsuggesties worden opnieuw uitgevoerd. Ververs de pagina over enkele minuten.")
                st.rerun()
            except Exception as e:
                st.error(f"Fout bij starten analyse: {e}")
    with col2:
        if st.button("Annuleren", use_container_width=True):
            st.rerun()


col_del, col_rerun, col_ctx = st.columns([3, 3, 4])
with col_del:
    if selected_analysis and st.button("Verwijder", icon="🗑️", use_container_width=True):
        confirm_delete_result(selected_analysis)
with col_rerun:
    if st.button("Opnieuw", icon="🔄", use_container_width=True):
        if selected_analysis and selected_analysis["analysis_type"]["name"] == "liedsuggesties":
            confirm_rerun_liedsuggesties(sermon_analysis_id=int(analysis_id))
        else:
            confirm_rerun_analysis(
                sermon_analysis_id=int(analysis_id),
                analysis_type_name=selected_analysis["analysis_type"]["name"] if selected_analysis else "",
                front_end_name=selected_analysis["analysis_type"]["front_end_name"] if selected_analysis else "",
            )
with col_ctx:
    if st.button("Aanpassen", icon="✏️", use_container_width=True):
        aanpassen_dialog(selected_analysis)

if st.session_state.get("extra_context"):
    st.info(f"**Extra context:** {st.session_state['extra_context']}")

if not selected_analysis:
    st.stop()

st.title(selected_analysis["analysis_type"]["front_end_name"])

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


