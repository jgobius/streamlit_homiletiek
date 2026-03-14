import streamlit as st

from src.utils.utils import redirect_to_login, get_cached_data

st.cache_data.clear()

analysis_results = get_cached_data(f"api/analysis-results?sermon_analysis_id={st.query_params.get('analysis_id')}")

st.write(analysis_results[0])
with st.sidebar:
    st.page_link(label="< Terug", page=f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py")
    
    for result in analysis_results:
        st.markdown(f"### {result['analysis_type']['front_end_name']}")


st.write(analysis_results)