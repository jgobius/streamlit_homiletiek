import json
import os

import requests
import streamlit as st

from src.models.church_model import ChurchModel
from src.utils.utils import redirect_to_login, render_sidebar

redirect_to_login()
render_sidebar()

# Mogelijke denominaties met weergavelabels.
# TODO: Deze lijst is nu hardcoded in de frontend. Beter is om de keuzes op te slaan als
# een Denomination-model in de database en op te halen via bijv. GET /api/denominations/.
DENOMINATION_OPTIONS = ["", "PKN", "CGK", "NGK", "HHK", "EV", "BAPT", "RK", "OVR"]
DENOMINATION_LABELS = {
    "":     "— Selecteer denominatie —",
    "PKN":  "PKN (Protestantse Kerk in Nederland)",
    "CGK":  "Christelijk Gereformeerde Kerken",
    "NGK":  "Nederlands Gereformeerde Kerken",
    "HHK":  "Hersteld Hervormde Kerk",
    "EV":   "Evangelisch",
    "BAPT": "Baptistengemeente",
    "RK":   "Rooms-Katholiek",
    "OVR":  "Overig",
}

# Mogelijke modaliteiten met weergavelabels.
# TODO: Ook deze lijst is hardcoded. Beter is een Modality-model in de database met
# GET /api/modalities/ — zelfde reden als bij denominaties.
MODALITY_OPTIONS = [
    "", "confessioneel", "gereformeerd", "hervormd",
    "midden_orthodox", "evangelisch", "vrijzinnig", "oecumenisch", "overig",
]
MODALITY_LABELS = {
    "":               "— Selecteer modaliteit —",
    "confessioneel":  "Confessioneel",
    "gereformeerd":   "Gereformeerd",
    "hervormd":       "Hervormd",
    "midden_orthodox": "Midden-orthodox",
    "evangelisch":    "Evangelisch",
    "vrijzinnig":     "Vrijzinnig",
    "oecumenisch":    "Oecumenisch",
    "overig":         "Overig",
}

# ── Bestaande gemeente laden bij bewerken ─────────────────────────────────────
church_id = st.query_params.get("church_id")
church_data: dict = {}
if church_id:
    church_data = st.session_state["api_handler"].get(f"api/churches/{church_id}/")

is_edit = bool(church_id)
st.title("Kerkelijke gemeente bewerken" if is_edit else "Nieuwe kerkelijke gemeente toevoegen")

# ── Formulier ─────────────────────────────────────────────────────────────────
name = st.text_input(
    "Naam van de kerkelijke gemeente *",
    max_chars=128,
    value=church_data.get("name", ""),
)
place = st.text_input(
    "Plaats *",
    max_chars=128,
    value=church_data.get("place", ""),
)

denomination = st.selectbox(
    "Denominatie *",
    options=DENOMINATION_OPTIONS,
    format_func=lambda v: DENOMINATION_LABELS.get(v, v),
    index=DENOMINATION_OPTIONS.index(church_data.get("denomination") or "")
    if church_data.get("denomination") in DENOMINATION_OPTIONS else 0,
)

modality = st.selectbox(
    "Modaliteit *",
    options=MODALITY_OPTIONS,
    format_func=lambda v: MODALITY_LABELS.get(v, v),
    index=MODALITY_OPTIONS.index(church_data.get("modality") or "")
    if church_data.get("modality") in MODALITY_OPTIONS else 0,
)

website = st.text_input(
    "Website *",
    max_chars=200,
    value=church_data.get("website", "") or "",
)

# ── Adres met ophaal-knop ─────────────────────────────────────────────────────
# Het adresveld wordt voorgevuld vanuit de bestaande gemeente of leeg gelaten.
st.markdown("**Adres \\***")
col_addr, col_btn = st.columns([3, 1])

# address_input is de key van de text_input; zo kan session_state de waarde
# bijwerken na het ophalen via de API (zonder key negeert Streamlit de update).
if "address_input" not in st.session_state:
    st.session_state["address_input"] = church_data.get("address", "") or ""
if "address_error" not in st.session_state:
    st.session_state["address_error"] = ""

with col_btn:
    st.write("")  # verticale uitlijning met het tekstinvoerveld
    if st.button("Adres ophalen", disabled=not name or not place, use_container_width=True):
        with st.spinner("Adres opzoeken via internet..."):
            try:
                agent_url = os.environ.get("API_AGENT_URL").rstrip("/")
                resp = requests.post(
                    f"{agent_url}/address-lookup/",
                    json={"name": name, "place": place, "website": website},
                    timeout=30,
                )
                resp.raise_for_status()
                payload = resp.json()
                st.session_state["address_input"] = payload.get("adres", "")
                if payload.get("gevonden"):
                    st.session_state["address_error"] = ""
                else:
                    # Geen (volledig) adres gevonden; waarschuw de gebruiker
                    st.session_state["address_error"] = (
                        "Geen adres gevonden via OpenStreetMap. Vul het adres handmatig in."
                    )
            except Exception as e:
                st.session_state["address_error"] = f"Adres ophalen mislukt: {e}"

if st.session_state["address_error"]:
    # Technische fouten als error tonen, "niet gevonden" als warning
    if st.session_state["address_error"].startswith("Adres ophalen mislukt"):
        st.error(st.session_state["address_error"])
    else:
        st.warning(st.session_state["address_error"])

with col_addr:
    address = st.text_input(
        "Adres",
        max_chars=200,
        key="address_input",
        label_visibility="collapsed",
        placeholder="Straat huisnummer, postcode plaats",
    )

context = st.text_area(
    "Extra context over de gemeente",
    height=150,
    max_chars=1024,
    value=church_data.get("context", "") or "",
)

# ── Validatieberichten en opslaan ─────────────────────────────────────────────
# De knop is uitgeschakeld zolang verplichte velden ontbreken.
submit_disabled = not name or not place or not denomination or not modality or not address

hints = []
if not denomination:
    hints.append("selecteer een denominatie")
if not modality:
    hints.append("selecteer een modaliteit")
if not address:
    hints.append("voer een adres in of gebruik 'Adres ophalen'")
if hints:
    st.caption("⚠️ Verplicht: " + ", ".join(hints) + ".")

button_title = "Gemeente bijwerken" if is_edit else "Gemeente toevoegen"
add_church = st.button(button_title, type="primary", disabled=submit_disabled)

if add_church:
    try:
        church = ChurchModel(
            name=name,
            place=place,
            address=address or None,
            denomination=denomination or None,
            modality=modality or None,
            website=website,
            context=context if context else None,
        )
        data = json.loads(church.model_dump_json())

        if is_edit:
            st.session_state["api_handler"].put(f"api/churches/{church_id}/", data)
            st.session_state.pop("address_input", None)
            st.switch_page(f"{st.session_state['page_navigation_dir']}/churches/churches_overview.py")
        else:
            st.session_state["api_handler"].post("api/churches/", data)
            st.session_state.pop("address_input", None)
            if st.query_params.get("from_page"):
                st.switch_page(f"{st.session_state['page_navigation_dir']}/analyses/{st.query_params.get('from_page')}")
            else:
                st.switch_page(f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py")

    except Exception as e:
        st.error(f"Er is een fout opgetreden: {e}")
