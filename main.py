import streamlit as st

st.session_state['page_navigation_dir'] = 'page_navigation'

def main():
    
    welcome_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/welcome.py", title='Welcome')
    login_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/login.py", title='Login')
    dashboard_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/dashboard.py", title='Preekanalyses')
    # settings_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/settings.py", title='Instellingen')
    new_analysis_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/new_analysis.py", title='Nieuwe analyse')
    
    if 'session_token' not in st.session_state:
       pg = st.navigation([welcome_page, login_page, dashboard_page], position='hidden')
       pg.run()
    
    else:
       pg = st.navigation([dashboard_page, new_analysis_page])
       pg.run()

if __name__ == "__main__":
    main()
