import streamlit as st 

from src.utils.utils import get_data, redirect_to_login, render_sidebar

redirect_to_login()

render_sidebar()

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
        
        col1, col2 = st.columns([5,5])
        with col1:
            edit_church = st.button("Gemeente bewerken", key=f"edit_{name}")
            if edit_church:
                st.switch_page(f"{st.session_state['page_navigation_dir']}/churches/new_church.py", query_params={"church_id": church['id']})
        with col2:
            delete_church = st.button("Gemeente verwijderen", key=f"delete_{name}", type="primary")
            if delete_church:
                response = st.session_state['api_handler'].delete(f"api/churches/{church['id']}/")
                if response.get('success'):
                    st.success(f"Gemeente '{name}' is succesvol verwijderd.")
                else:
                    st.error(f"Er is een fout opgetreden bij het verwijderen van gemeente '{name}'.")