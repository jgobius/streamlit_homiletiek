import json

import requests
import streamlit as st

from src.models.church_model import ChurchModel
from src.utils.utils import redirect_to_login, render_sidebar

redirect_to_login()
render_sidebar()

DENOMINATION_OPTIONS = ["", "PKN", "GKV", "CGK", "NGK", "HHK", "EV", "BAPT", "LUTH", "RK", "OVR"]
DENOMINATION_LABELS = {
    "":     "— Selecteer denominatie —",
    "PKN":  "PKN (Protestantse Kerk in Nederland)",
    "GKV":  "Gereformeerde Kerken (vrijgemaakt)",
    "CGK":  "Christelijk Gereformeerde Kerken",
    "NGK":  "Nederlands Gereformeerde Kerken",
    "HHK":  "Hersteld Hervormde Kerk",
    "EV":   "Evangelisch",
    "BAPT": "Baptistengemeente",
    "LUTH": "Luthers",
    "RK":   "Rooms-Katholiek",
    "OVR":  "Overig",
}

MODALITY_OPTIONS = [
    "", "confessioneel", "gereformeerd_vrijgemaakt", "hervormd_gereformeerd",
    "midden_orthodox", "evangelisch", "vrijzinnig", "oecumenisch", "overig",
]
MODALITY_LABELS = {
    "":                         "— Selecteer modaliteit —",
    "confessioneel":            "Confessioneel",
    "gereformeerd_vrijgemaakt": "Gereformeerd-vrijgemaakt",
    "hervormd_gereformeerd":    "Hervormd-gereformeerd",
    "midden_orthodox":          "Midden-orthodox",
    "evangelisch":              "Evangelisch",
    "vrijzinnig":               "Vrijzinnig",
    "oecumenisch":              "Oecumenisch",
    "overig":                   "Overig",
}

# ── Bestaande gemeente laden bij bewerken ─────────────────────────────────────
church_id = st.query_params.get("church_id")
church_data: dict = {}
if church_id:
    church_data = st.session_state["api_handler"].get(f"api/churches/{church_id}/")

is_edit = bool(church_id)
st.title("Gemeente bewerken" if is_edit else "Nieuwe gemeente toevoegen")

# ── Formulier ─────────────────────────────────────────────────────────────────
name = st.text_input(
    "Naam van de gemeente *",
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
st.markdown("**Adres \\***")
col_addr, col_btn = st.columns([3, 1])

if "fetched_address" not in st.session_state:
    st.session_state["fetched_address"] = church_data.get("address", "") or ""
if "address_error" not in st.session_state:
    st.session_state["address_error"] = ""

with col_btn:
    st.write("")  # verticale uitlijning
    if st.button("Adres ophalen", disabled=not name or not place, use_container_width=True):
        with st.spinner("Adres opzoeken via Google Search..."):
            try:
                agent_url = st.secrets["API_AGENT_URL"].rstrip("/")
                resp = requests.post(
                    f"{agent_url}/address-lookup/",
                    json={"name": name, "place": place, "website": website},
                    timeout=30,
                )
                resp.raise_for_status()
                st.session_state["fetched_address"] = resp.json().get("adres", "")
                st.session_state["address_error"] = ""
            except Exception as e:
                st.session_state["address_error"] = f"Adres ophalen mislukt: {e}"

if st.session_state["address_error"]:
    st.error(st.session_state["address_error"])

with col_addr:
    address = st.text_input(
        "Adres",
        max_chars=200,
        value=st.session_state["fetched_address"],
        label_visibility="collapsed",
        placeholder="Straat huisnummer, postcode plaats",
    )
    st.session_state["fetched_address"] = address

context = st.text_area(
    "Extra context over de gemeente",
    height=150,
    max_chars=1024,
    value=church_data.get("context", "") or "",
)

# ── Validatieberichten en opslaan ─────────────────────────────────────────────
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
            st.session_state.pop("fetched_address", None)
            st.switch_page(f"{st.session_state['page_navigation_dir']}/churches/churches_overview.py")
        else:
            st.session_state["api_handler"].post("api/churches/", data)
            st.session_state.pop("fetched_address", None)
            if st.query_params.get("from_page"):
                st.switch_page(f"{st.session_state['page_navigation_dir']}/analyses/{st.query_params.get('from_page')}")
            else:
                st.switch_page(f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py")

    except Exception as e:
        st.error(f"Er is een fout opgetreden: {e}")
