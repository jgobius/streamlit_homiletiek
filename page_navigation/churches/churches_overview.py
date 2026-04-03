import streamlit as st

from src.utils.utils import get_data, redirect_to_login, render_sidebar

redirect_to_login()

render_sidebar()


@st.dialog("Gemeente verwijderen")
def _bevestig_verwijder_gemeente() -> None:
    # Haal de gemeente op die verwijderd moet worden uit session_state.
    # De keuze voor session_state zorgt dat de dialoog de juiste gemeente heeft
    # ongeacht de Streamlit rerun-cyclus.
    church = st.session_state.get("_gemeente_te_verwijderen")
    if not church:
        st.rerun()

    st.write(f"Weet je zeker dat je gemeente **'{church['name']}'** wilt verwijderen?")
    st.warning(
        "Alle gekoppelde kerkdienstanalyses worden ook permanent verwijderd. "
        "Dit kan niet ongedaan worden gemaakt."
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ja, verwijderen", type="primary", use_container_width=True):
            try:
                # Gebruik de centrale api_handler voor het DELETE-verzoek.
                st.session_state['api_handler'].delete(f"api/churches/{church['id']}/")
                st.session_state.pop("_gemeente_te_verwijderen", None)
                st.rerun()
            except Exception as e:
                st.error(f"Fout bij verwijderen: {e}")
    with col2:
        if st.button("Annuleren", use_container_width=True):
            st.session_state.pop("_gemeente_te_verwijderen", None)
            st.rerun()


# CSS om de verwijderknop (✕) subtiel te stylen zodat hij minder prominent is
# dan de bewerkknop, maar toch klikbaar blijft.
st.markdown("""
<style>
div[data-testid="stHorizontalBlock"] > div:last-child button {
    background-color: transparent !important;
    border: 1px solid rgba(49,51,63,0.2) !important;
    color: rgba(49,51,63,0.4) !important;
}
div[data-testid="stHorizontalBlock"] > div:last-child button:hover {
    border-color: rgba(49,51,63,0.5) !important;
    color: rgba(49,51,63,0.6) !important;
}
</style>
""", unsafe_allow_html=True)

churches = get_data("api/churches/")
st.title("Overzicht van gemeentes")
st.write("Hieronder vind je een overzicht van alle toegevoegde gemeentes.")

for church in churches:
    name = church['name']
    place = church['place']
    website = church['website']

    with st.expander(f"{name} - {place}"):
        st.write(f"**Naam:** {name}")
        st.write(f"**Plaats:** {place}")
        st.write(f"**Website:** {website}")

        # Drie kolommen: bewerkknop links, lege ruimte, kleine verwijderknop rechts.
        col1, col2, col3 = st.columns([5, 4, 1])
        with col1:
            if st.button("Gemeente bewerken", key=f"edit_{name}"):
                st.switch_page(
                    f"{st.session_state['page_navigation_dir']}/churches/new_church.py",
                    query_params={"church_id": church['id']},
                )
        with col3:
            # Bij klik: sla de gemeente op in session_state en open de bevestigingsdialoog.
            if st.button("✕", key=f"delete_{name}"):
                st.session_state["_gemeente_te_verwijderen"] = church
                _bevestig_verwijder_gemeente()
