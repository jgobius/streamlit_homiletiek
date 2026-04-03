import streamlit as st

st.session_state['page_navigation_dir'] = 'page_navigation'


def _calc_token_totals(usage: dict) -> tuple[int, int, float]:
    # Haal modelprijzen op uit st.secrets; ontbrekende sleutels leveren 0.0 op.
    model_prices = st.secrets.get("model_prices", {})
    fallback_model = st.secrets.get("CURRENT_MODEL", "")
    total_input = total_output = 0
    total_cost = 0.0
    for model, counts in usage.items():
        inp = counts.get("input_tokens", 0) or 0
        out = counts.get("output_tokens", 0) or 0
        # Gebruik modelprijzen als beschikbaar, anders de fallback.
        prices = model_prices.get(model) or model_prices.get(fallback_model, {})
        total_input += inp
        total_output += out
        total_cost += (inp / 1_000_000) * prices.get("input_eur", 0.0)
        total_cost += (out / 1_000_000) * prices.get("output_eur", 0.0)
    return total_input, total_output, total_cost


def _render_cumulative_token_usage_sidebar() -> None:
    # Toon het cumulatieve tokenverbruik van de ingelogde gebruiker in de sidebar.
    handler = st.session_state.get('api_handler')
    if not handler:
        return
    usage = handler.get("api/token-usage/cumulative/")
    if not isinstance(usage, dict):
        return
    total_input, total_output, total_cost = _calc_token_totals(usage)
    with st.sidebar:
        st.divider()
        st.caption(
            f"Totaal tokenverbruik: {total_input:,} in / {total_output:,} uit  \n"
            f"Totale kosten: €{total_cost:.2f}"
        )


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

    pages = [dashboard_page, new_analysis_page, liturgisch_jaar_page, church_overview_page, new_church_page, analysis_overview_page, logout_page]

    # pages = {
    #     "Preekanalyses": [dashboard_page, new_analysis_page, liturgisch_jaar_page],
    #     "Gemeentes": [church_overview_page, new_church_page],
    #     "Account": [logout_page],
    # }

    if 'api_handler' not in st.session_state:
        pg = st.navigation([welcome_page, login_page, register_page, dashboard_page], position='hidden')
        pg.run()

    else:
        pg = st.navigation(pages, position='hidden')
        pg.run()
        # Toon cumulatief tokenverbruik op de hoofdpagina (dashboard).
        if pg == dashboard_page:
            _render_cumulative_token_usage_sidebar()


if __name__ == "__main__":
    main()
