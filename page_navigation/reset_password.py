import streamlit as st
from requests.exceptions import HTTPError


st.title("Wachtwoord resetten")

password = st.text_input("Nieuw wachtwoord", type="password")
confirm_password = st.text_input("Bevestig nieuw wachtwoord", type="password")

if password != confirm_password:
    st.warning("Wachtwoorden komen niet overeen. Zorg ervoor dat beide wachtwoorden hetzelfde zijn.")

col1, col2 = st.columns([1, 1])
with col1:
    reset_password = st.button("Wachtwoord resetten", use_container_width=True)
with col2:
    if st.button("Terug naar hoofdpagina", use_container_width=True, type="primary"):
        st.switch_page(f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py")

if reset_password:
    # Frontend-validatie vóór de API-aanroep: lege of niet-overeenkomende
    # wachtwoorden lokken een 400 uit bij ChangePasswordSerializer en lieten
    # de pagina daarvoor crashen op een onafgevangen HTTPError.
    if not password or not confirm_password:
        st.error("Vul beide wachtwoordvelden in.")
    elif password != confirm_password:
        st.error("Wachtwoorden komen niet overeen.")
    else:
        try:
            result = st.session_state['api_handler'].post(
                endpoint="/api/change-password/",
                data={
                    "password": password,
                    "confirm_password": confirm_password,
                }
            )
        except HTTPError:
            # Backend-validatiefouten of andere HTTP-fouten netjes tonen
            # i.p.v. de Streamlit-pagina te laten crashen met een stacktrace.
            st.error("Er is een fout opgetreden bij het resetten van het wachtwoord. Probeer het opnieuw.")
        else:
            if result.get('detail') == "Wachtwoord succesvol gewijzigd.":
                st.success("Wachtwoord succesvol gereset!")
            else:
                st.error("Er is een fout opgetreden bij het resetten van het wachtwoord. Probeer het opnieuw.")

