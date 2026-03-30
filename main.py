import streamlit as st
from streamlit_cookies_controller import CookieController

st.set_page_config(page_icon="static/favicon.png")

from src.api.jwthandler import JwtHandler
from src.api.handler import APIHandler

_COOKIE_KEY = "auth_refresh_token"


def _render_token_usage_sidebar() -> None:
    handler = st.session_state.get('api_handler')
    if not handler:
        return
    usage = handler.get("api/token-usage/")
    if not isinstance(usage, dict):
        return
    model_prices = st.secrets.get("model_prices", {})
    fallback_model = st.secrets.get("CURRENT_MODEL", "")
    total_input = total_output = 0
    total_cost = 0.0
    for model, counts in usage.items():
        inp = counts.get("input_tokens", 0) or 0
        out = counts.get("output_tokens", 0) or 0
        prices = model_prices.get(model) or model_prices.get(fallback_model, {})
        total_input += inp
        total_output += out
        total_cost += (inp / 1_000_000) * prices.get("input_eur", 0.0)
        total_cost += (out / 1_000_000) * prices.get("output_eur", 0.0)
    with st.sidebar:
        st.divider()
        st.caption(
            f"Tokens huidige analyse: {total_input:,} in / {total_output:,} uit  \n"
            f"Kosten huidige analyse: €{total_cost:.2f}"
        )

st.session_state['page_navigation_dir'] = 'page_navigation'


def _try_restore_session(controller: CookieController) -> bool:
    """Restore api_handler from stored refresh token cookie. Returns True if restored."""
    try:
        refresh_token = controller.get(_COOKIE_KEY)
    except TypeError:
        return False  # cookies not loaded yet on first render
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
        controller.remove(_COOKIE_KEY)
        return False


def main():
    controller = CookieController()
    st.session_state['cookie_controller'] = controller

    # Write pending refresh token to cookie once the controller is ready.
    pending = st.session_state.get('_pending_refresh_token')
    if pending:
        try:
            controller.set(_COOKIE_KEY, pending)
            st.session_state.pop('_pending_refresh_token')
        except TypeError:
            pass  # controller not ready yet — will retry on next render

    if 'api_handler' not in st.session_state:
        if not _try_restore_session(controller):
            # st.stop() halts Python but the browser still processes the render,
            # allowing the cookie controller JS to run and send data back.
            # That component callback triggers the next render with cookies available.
            # Limit to 2 stops to avoid looping forever when there is no cookie.
            attempts = st.session_state.get('_restore_attempts', 0)
            if attempts < 1:
                st.session_state['_restore_attempts'] = attempts + 1
                st.stop()

    if 'api_handler' in st.session_state:
        st.session_state.pop('_restore_attempts', None)

    welcome_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/welcome.py", title='Welcome', default=('api_handler' not in st.session_state))
    login_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/login.py", title='Inloggen')
    logout_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/logout.py", title='Uitloggen')
    register_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/register.py", title='Registreren')
    dashboard_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py", title='Overzicht', default=('api_handler' in st.session_state))
    # settings_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/settings.py", title='Instellingen')
    new_analysis_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/analyses/new_analysis.py", title='Nieuw')
    liturgisch_jaar_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/analysis_results/liturgisch_jaar.py", title='Liturgisch jaar')

    church_overview_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/churches/churches_overview.py", title='Overzicht')
    new_church_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/churches/new_church.py", title='Nieuw')

    analysis_overview_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/analysis_results/overview.py", title='Kerkdienstanalyse overzicht')
    perspectieven_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/analysis_results/perspectieven_overview.py", title='Perspectieven')

    pages = {
        "Kerkelijke gemeenten": [church_overview_page, new_church_page],
        "Kerkdiensten": [dashboard_page, new_analysis_page, liturgisch_jaar_page, analysis_overview_page],
        "Perspectieven": [perspectieven_page],
        "Account": [logout_page],
    }

    if 'api_handler' not in st.session_state:
        pg = st.navigation([welcome_page, login_page, register_page, dashboard_page], position='hidden')
        st.session_state['current_page'] = pg
        pg.run()
    else:
        pg = st.navigation(pages, position='hidden')
        st.session_state['current_page'] = pg
        pg.run()
        if pg in (analysis_overview_page, perspectieven_page):
            _render_token_usage_sidebar()


if __name__ == "__main__":
    main()
