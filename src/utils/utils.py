import streamlit as st


def redirect_to_login() -> None:
    """
    Redirect the user to the login page if no session token is present.
    This function checks if a 'session_token' exists in the Streamlit session state.
    If the token is not found, it redirects the user to the login page using the
    page navigation directory stored in session state.
    Returns:
        None
    Raises:
        KeyError: If 'page_navigation_dir' is not present in st.session_state when
                  'session_token' is missing.
    Example:
        >>> redirect_to_login()
        # Redirects to login page if session_token is not in session state
    """
    
    if not 'api_handler' in st.session_state:
        return st.switch_page(f'{st.session_state["page_navigation_dir"]}/login.py')
    
    if not st.session_state['api_handler'].jwt_handler.authorized:
    
        st.switch_page(f'{st.session_state["page_navigation_dir"]}/login.py')