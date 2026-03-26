import streamlit as st

st.session_state['page_navigation_dir'] = 'page_navigation'


def main():
    welcome_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/welcome.py", title='Welcome')
    login_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/login.py", title='Inloggen')
    logout_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/logout.py", title='Uitloggen')
    register_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/register.py", title='Registreren')
    dashboard_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py", title='Overzicht preekanalyses')
    # settings_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/settings.py", title='Instellingen')
    new_analysis_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/analyses/new_analysis.py", title='Nieuwe preekanalyse')
    liturgisch_jaar_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/analysis_results/liturgisch_jaar.py", title='Liturgisch jaar')

    church_overview_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/churches/churches_overview.py", title='Overzicht gemeentes')
    new_church_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/churches/new_church.py", title='Nieuwe gemeente')
    
    analysis_overview_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/analysis_results/overview.py", title='Analyse overzicht')

    pages = {
        "Gemeentes": [church_overview_page, new_church_page],
        "Voorbereidingsanalyses": [dashboard_page, new_analysis_page, liturgisch_jaar_page, analysis_overview_page],
        "Account": [logout_page],
    }

    if 'api_handler' not in st.session_state:
        pg = st.navigation([welcome_page, login_page, register_page, dashboard_page], position='hidden')
        pg.run()

    else:
        pg = st.navigation(pages, position='hidden')
        pg.run()


if __name__ == "__main__":
    main()
