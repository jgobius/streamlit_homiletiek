import streamlit as st
from streamlit_cookies_controller import CookieController

from src.api.jwthandler import JwtHandler
from src.api.handler import APIHandler

# Sleutel waaronder het refresh token in de browser-cookie wordt opgeslagen.
_COOKIE_KEY = "auth_refresh_token"

st.session_state['page_navigation_dir'] = 'page_navigation'


def _try_restore_session(controller: CookieController) -> bool:
    """Herstel api_handler vanuit een opgeslagen refresh token cookie. Geeft True terug als herstel lukte."""
    try:
        refresh_token = controller.get(_COOKIE_KEY)
    except TypeError:
        # Cookies zijn nog niet geladen op de eerste render — wacht op volgende render.
        return False
    if not refresh_token:
        return False
    try:
        jwt_handler = JwtHandler.from_refresh_token(
            refresh_token=refresh_token,
            base_url=st.secrets["API_BASE_URL"],
            access_endpoint="/api/token/",
            refresh_endpoint="/api/token/refresh/",
        )
        st.session_state['api_handler'] = APIHandler(
            base_url=st.secrets["API_BASE_URL"],
            jwt_handler=jwt_handler,
        )
        return True
    except Exception:
        # Verwijder ongeldige cookie zodat de gebruiker opnieuw kan inloggen.
        controller.remove(_COOKIE_KEY)
        return False


def main():
    # Stel paginatitel en favicon in (oranje kruis-icoon).
    st.set_page_config(page_icon="static/favicon.png")
    # Initialiseer de cookie controller en sla hem op in session_state zodat
    # andere pagina's hem kunnen ophalen zonder hem opnieuw te initialiseren.
    controller = CookieController()
    st.session_state['cookie_controller'] = controller

    # Schrijf een pending refresh token naar de cookie zodra de controller gereed is.
    # Dit token wordt door login.py klaargezet na een succesvolle login.
    pending = st.session_state.get('_pending_refresh_token')
    if pending:
        try:
            controller.set(_COOKIE_KEY, pending)
            st.session_state.pop('_pending_refresh_token')
        except TypeError:
            pass  # controller nog niet gereed — volgende render probeert het opnieuw

    if 'api_handler' not in st.session_state:
        if not _try_restore_session(controller):
            # st.stop() stopt Python maar de browser verwerkt de render nog,
            # waardoor de cookie controller JS kan draaien en data terugstuurt.
            # Die component-callback triggert de volgende render mét cookies.
            # Begrens tot 1 poging zodat er geen oneindige lus ontstaat als er geen cookie is.
            attempts = st.session_state.get('_restore_attempts', 0)
            if attempts < 1:
                st.session_state['_restore_attempts'] = attempts + 1
                st.stop()

    # Verwijder de teller zodra we ingelogd zijn.
    if 'api_handler' in st.session_state:
        st.session_state.pop('_restore_attempts', None)

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

    pages = [dashboard_page, new_analysis_page, liturgisch_jaar_page, church_overview_page, new_church_page, analysis_overview_page, logout_page]

    if 'api_handler' not in st.session_state:
        pg = st.navigation([welcome_page, login_page, register_page, dashboard_page], position='hidden')
        pg.run()
    else:
        pg = st.navigation(pages, position='hidden')
        pg.run()

if __name__ == "__main__":
    main()
