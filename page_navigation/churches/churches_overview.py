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

# Leesbare labels voor denominatie en modaliteit, gelijk aan de keuzes in het gemeente-formulier.
_DENOMINATIE_LABELS = {
    "PKN":  "PKN (Protestantse Kerk in Nederland)",
    "CGK":  "Christelijk Gereformeerde Kerken",
    "NGK":  "Nederlands Gereformeerde Kerken",
    "HHK":  "Hersteld Hervormde Kerk",
    "EV":   "Evangelisch",
    "BAPT": "Baptistengemeente",
    "RK":   "Rooms-Katholiek",
    "OVR":  "Overig",
}

_MODALITEIT_LABELS = {
    "confessioneel":   "Confessioneel",
    "gereformeerd":    "Gereformeerd",
    "hervormd":        "Hervormd",
    "midden_orthodox": "Midden-orthodox",
    "evangelisch":     "Evangelisch",
    "vrijzinnig":      "Vrijzinnig",
    "oecumenisch":     "Oecumenisch",
    "overig":          "Overig",
}

churches = get_data("api/churches/")
st.title("Overzicht van gemeenten")
st.write("Hieronder vind je een overzicht van alle toegevoegde gemeenten.")

# Toon een informatieve boodschap als er nog geen gemeenten zijn, analoog aan
# de lege-staatmelding op het kerkdienstanalyses-dashboard. De 'Nieuwe
# gemeente'-knop onderaan blijft zichtbaar zodat de gebruiker direct kan starten.
if len(churches) == 0:
    st.info("Er zijn nog geen gemeenten toegevoegd.")

for church in churches:
    name = church['name']
    place = church['place']
    website = church['website']
    denomination = church.get('denomination') or ""
    modality = church.get('modality') or ""
    address = church.get('address') or ""

    with st.expander(f"{name} - {place}"):
        st.write(f"**Naam:** {name}")
        st.write(f"**Plaats:** {place}")
        # Toon leesbaar label als de waarde bekend is, anders een streepje.
        st.write(f"**Denominatie:** {_DENOMINATIE_LABELS.get(denomination, '—') if denomination else '—'}")
        st.write(f"**Modaliteit:** {_MODALITEIT_LABELS.get(modality, '—') if modality else '—'}")
        st.write(f"**Adres:** {address if address else '—'}")
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

# Knop om een nieuwe gemeente toe te voegen, net als de 'Nieuwe analyse'-knop
# op het kerkdienstanalyses-dashboard. Navigeert naar hetzelfde formulier dat
# ook voor bewerken gebruikt wordt; zonder `church_id` query param start het
# in aanmaak-modus.
if st.button("Nieuwe gemeente", type="primary"):
    st.switch_page(
        f"{st.session_state['page_navigation_dir']}/churches/new_church.py"
    )
