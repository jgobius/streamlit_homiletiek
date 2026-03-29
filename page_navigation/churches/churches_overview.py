import requests
import streamlit as st

from src.utils.utils import get_data, redirect_to_login, render_sidebar

redirect_to_login()

render_sidebar()

@st.dialog("Gemeente verwijderen")
def confirm_delete_church():
    church = st.session_state.get("_pending_delete_church")
    if not church:
        st.rerun()
    st.write(f"Weet je zeker dat je gemeente **'{church['name']}'** wilt verwijderen?")
    st.warning("Alle gekoppelde kerkdienstanalyses worden ook permanent verwijderd. Dit kan niet ongedaan worden gemaakt.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ja, verwijderen", type="primary", use_container_width=True):
            try:
                handler = st.session_state['api_handler']
                url = f"{handler.base_url}/api/churches/{church['id']}/"
                headers = {"Authorization": f"Bearer {handler.jwt_handler.token}"}
                requests.delete(url, headers=headers).raise_for_status()
                st.session_state.pop("_pending_delete_church", None)
                st.rerun()
            except Exception as e:
                st.error(f"Fout bij verwijderen: {e}")
    with col2:
        if st.button("Annuleren", use_container_width=True):
            st.session_state.pop("_pending_delete_church", None)
            st.rerun()

churches = get_data("api/churches/")
st.title("Overzicht van gemeenten")
st.write("Hieronder vind je een overzicht van alle toegevoegde gemeenten.")

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

DENOMINATION_LABELS = {
    "PKN":  "PKN (Protestantse Kerk in Nederland)",
    "CGK":  "Christelijk Gereformeerde Kerken",
    "NGK":  "Nederlands Gereformeerde Kerken",
    "HHK":  "Hersteld Hervormde Kerk",
    "EV":   "Evangelisch",
    "BAPT": "Baptistengemeente",
    "RK":   "Rooms-Katholiek",
    "OVR":  "Overig",
}

MODALITY_LABELS = {
    "confessioneel":   "Confessioneel",
    "gereformeerd":    "Gereformeerd",
    "hervormd":        "Hervormd",
    "midden_orthodox": "Midden-orthodox",
    "evangelisch":     "Evangelisch",
    "vrijzinnig":      "Vrijzinnig",
    "oecumenisch":     "Oecumenisch",
    "overig":          "Overig",
}

for church in churches:
    name = church['name']
    place = church['place']
    website = church['website']
    address = church.get('address') or ''
    denomination = church.get('denomination') or ''
    modality = church.get('modality') or ''
    denomination_label = DENOMINATION_LABELS.get(denomination, denomination)
    modality_label = MODALITY_LABELS.get(modality, modality)

    with st.expander(f"{name} - {place}"):
        st.write(f"**Naam:** {name}")
        if address:
            st.write(f"**Adres:** {address}")
        if denomination_label:
            st.write(f"**Denominatie:** {denomination_label}")
        if modality_label:
            st.write(f"**Modaliteit:** {modality_label}")
        st.write(f"**Website:** {website}")

        col1, col2, col3 = st.columns([5, 4, 1])
        with col1:
            if st.button("Gemeente bewerken", key=f"edit_{name}"):
                st.switch_page(f"{st.session_state['page_navigation_dir']}/churches/new_church.py", query_params={"church_id": church['id']})
        with col3:
            if st.button("✕", key=f"delete_{name}"):
                st.session_state["_pending_delete_church"] = church
                confirm_delete_church()