import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import streamlit as st

from src.utils.utils import (
    redirect_to_login,
    get_data,
    render_sidebar,
    haal_cumulatief_tokenverbruik_op,
    bereken_kosten_eur,
    formatteer_eur,
)
# Word-export helper: pure module die de .docx-bytes bouwt uit één
# kerkdienstanalyse (zie src/utils/word_export.py voor de implementatie).
from src.utils.word_export import bouw_kerkdienstanalyse_docx

redirect_to_login()

render_sidebar()

# Django levert `created_at` in UTC (settings.USE_TZ=True, TIME_ZONE="UTC").
# Voor weergave converteren we naar Nederlandse tijd (DST-aware via zoneinfo).
_DISPLAY_TZ = ZoneInfo("Europe/Amsterdam")

# Auto-gegenereerde titels eindigen op ' HH:MM' (zie new_analysis.py, waar de
# titel wordt opgebouwd als '<gemeente> <zondagdatum> <aanmaaktijd>'). Op deze
# suffix haken we aan als fallback wanneer `created_at` ontbreekt (records van
# vóór de migratie).
_AUTO_TIME_SUFFIX = re.compile(r"\s(\d{2}:\d{2})$")


def _split_aanmaaktijd(title: str | None) -> tuple[str | None, str | None]:
    """Splitst de HH:MM-suffix (aanmaaktijd) van een auto-gegenereerde titel.

    Geeft (titel_zonder_tijd, aanmaaktijd) terug. Voor custom titels zonder
    tijd-suffix is de tweede waarde ``None`` en blijft de titel ongewijzigd.
    """
    if not title:
        return None, None
    match = _AUTO_TIME_SUFFIX.search(title)
    if not match:
        return title, None
    return title[: match.start()], match.group(1)


def _format_aanmaak_label(created_at: str | None, title_suffix: str | None) -> str | None:
    """Formatteert het label voor het grijze aanmaaktijdstip naast de knop.

    Voorkeur heeft het `created_at`-veld van de API (ISO-8601 UTC), dat we naar
    Europa/Amsterdam converteren en als 'dd-mm-yyyy HH:MM' weergeven. Ontbreekt
    dit veld — bij records van vóór de 0008-migratie of als de backend nog
    geen `created_at` serializet — dan vallen we terug op de HH:MM-suffix die
    uit de auto-gegenereerde titel is gesplitst.
    """
    if created_at:
        try:
            dt_utc = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            return dt_utc.astimezone(_DISPLAY_TZ).strftime("%d-%m-%Y %H:%M")
        except ValueError:
            # Onverwacht formaat: val terug op de titel-suffix zodat er toch
            # iets leesbaars getoond wordt.
            pass
    return title_suffix


def format_title(title: str | None, congregation: str, sermon_date: str) -> str:
    # Auto-gegenereerde titels bevatten al gemeente + zondagdatum; die info
    # laten we in dat geval weg om dubbele weergave te voorkomen. Custom titels
    # (zonder HH:MM-suffix) blijven volledig zichtbaar.
    _, aanmaaktijd = _split_aanmaaktijd(title)
    if title and aanmaaktijd is None:
        return f"{title} - {congregation} - {sermon_date}"

    return f"{congregation} - {sermon_date}"

def set_analysis_id(analysis_id: int) -> None:
    st.session_state.selected_analysis_id = analysis_id


@st.dialog("Word-document aanmaken")
def word_export_dialog() -> None:
    # Haal het te exporteren item op uit session_state. Bij ontbreken herladen
    # we de pagina zodat de dialog niet in een halve staat blijft hangen.
    item = st.session_state.get("_pending_word_export")
    if not item:
        st.rerun()

    # Korte header zodat de gebruiker ziet voor welke analyse het document
    # wordt gegenereerd.
    st.write(
        f"Document voor **{item['church']['name']} — "
        f"{datetime.strptime(item['sermon_date'], '%Y-%m-%d').strftime('%d-%m-%Y')}**"
    )

    # We cachen de gegenereerde bytes in session_state zodat een re-render van
    # de dialog (bv. omdat de gebruiker op de download-knop klikt) niet steeds
    # opnieuw een document bouwt. De key is per-analyse uniek.
    cache_key = f"_word_bytes_{item['id']}"

    if cache_key not in st.session_state:
        # Voortgang-feedback: progressbar + caption-regel. word_export.py
        # importeert zelf geen Streamlit; we voeden het via deze callback.
        progress_bar = st.progress(0.0, text="Voorbereiden...")
        status_slot = st.empty()

        def toon_voortgang(fractie: float, tekst: str) -> None:
            # Clamp tussen 0 en 1 zodat kleine afrondingsverschillen in de
            # word_export-module geen StreamlitAPIException opleveren.
            veilige_fractie = max(0.0, min(1.0, fractie))
            progress_bar.progress(veilige_fractie, text=tekst)
            status_slot.caption(tekst)

        try:
            handler = st.session_state["api_handler"]
            data, bestandsnaam = bouw_kerkdienstanalyse_docx(
                item["id"], handler, voortgang_callback=toon_voortgang
            )
            st.session_state[cache_key] = (data, bestandsnaam)
        except Exception as e:
            st.error(f"Fout bij genereren: {e}")
            return
        # Na succes de voortgang-widgets legen zodat alleen de download-knop
        # in de dialog overblijft. .empty() verwijdert de placeholder-content.
        progress_bar.empty()
        status_slot.empty()

    data, bestandsnaam = st.session_state[cache_key]
    st.download_button(
        "Download Word-document",
        data=data,
        file_name=bestandsnaam,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        type="primary",
        use_container_width=True,
    )
    if st.button("Sluiten", use_container_width=True):
        # Opruimen zodat een volgende klik een frisse generatie triggert
        # (bv. nadat een extra sub-analyse is afgerond).
        st.session_state.pop(cache_key, None)
        st.session_state.pop("_pending_word_export", None)
        st.rerun()


@st.dialog("Analyse verwijderen")
def confirm_delete_analysis() -> None:
    # Haal het te verwijderen item op uit session_state.
    item = st.session_state.get("_pending_delete_analysis")
    if not item:
        st.rerun()
    label = item.get('title') or f"{item['church']['name']} - {datetime.strptime(item['sermon_date'], '%Y-%m-%d').strftime('%d-%m-%Y')}"
    st.write(f"Weet je zeker dat je de analyse **'{label}'** wilt verwijderen? Dit kan niet ongedaan worden gemaakt.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ja, verwijderen", type="primary", use_container_width=True):
            try:
                handler = st.session_state['api_handler']
                handler.delete(f"api/sermon-analyses/{item['id']}/")
                st.session_state.pop("_pending_delete_analysis", None)
                # Markeer cache als vervuild zodat de lijst opnieuw opgehaald wordt.
                st.session_state["dashboard_data_dirty"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Fout bij verwijderen: {e}")
    with col2:
        if st.button("Annuleren", use_container_width=True):
            st.session_state.pop("_pending_delete_analysis", None)
            st.rerun()


# Cache de lijst om te voorkomen dat elke klik een API-roundtrip veroorzaakt.
# De vlag `dashboard_data_dirty` wordt gezet na aanmaken of verwijderen van een analyse.
if st.session_state.pop("dashboard_data_dirty", False) or "dashboard_analyses_cache" not in st.session_state:
    st.session_state["dashboard_analyses_cache"] = get_data("api/sermon-analyses/")
analysis = st.session_state["dashboard_analyses_cache"]

# Controleer cumulatief verbruik van de ingelogde gebruiker tegen het
# persoonlijke EUR-budget uit UserPreferences (backend). Per 2026-04
# vergelijken we geschatte kosten (€2 / 1M invoer, €12 / 1M uitvoer) met
# `BUDGET_EUR` in plaats van tegen aparte token-drempels: het tegoed in
# euro's is wat we de testgebruiker beloven en dus ook de juiste
# stop-conditie. De vlag `_limiet_overschreden` wordt verderop hergebruikt
# om de "Nieuwe analyse"-knop te verbergen — zo hoeven we niet dezelfde
# tuple twee keer te unpacken.
_token_info = haal_cumulatief_tokenverbruik_op()
_limiet_overschreden = False
if _token_info is not None:
    _tot_in, _tot_uit, _, _max_in, _max_uit, _budget_eur = _token_info
    # Frontend-only kostenberekening (zie `bereken_kosten_eur`); blijft
    # parallel lopen met de bestaande token-velden zonder DB-wijziging.
    _kosten_eur = bereken_kosten_eur(_tot_in, _tot_uit)
    _limiet_overschreden = _budget_eur > 0 and _kosten_eur > _budget_eur
    if _limiet_overschreden:
        # st.warning geeft Streamlit's native oranje/gele waarschuwingsbalk.
        st.warning(
            f"Je tegoed voor de early-test ({formatteer_eur(_budget_eur)}) is op. "
            f"Cumulatief verbruik: {formatteer_eur(_kosten_eur)}."
        )

st.title("Kerkdienstanalyses")
st.write("Overzicht van alle kerkdienstanalyses.")

# Paginascoped CSS: geef de knop van de laatste analyse (meest recente zondagdatum)
# dezelfde zachte oranje styling als het actieve tabblad en de geselecteerde
# sidebar-knop (achtergrond rgba(255,128,0,0.12), oranje rand en oranje tekst).
# De styling haakt aan op de `st-key-<key>` CSS-klasse die st.container(key=...)
# automatisch genereert, zodat alleen déze specifieke knop oranje wordt en de
# naastgelegen verwijder-knop onaangetast blijft.
st.markdown(
    """
    <style>
    .st-key-dashboard_latest_analysis [data-testid="stBaseButton-secondary"] {
        background-color: rgba(255, 128, 0, 0.12) !important;
        color: #FF8000 !important;
        border-color: #FF8000 !important;
    }
    .st-key-dashboard_latest_analysis [data-testid="stBaseButton-secondary"] * {
        color: #FF8000 !important;
    }
    .st-key-dashboard_latest_analysis [data-testid="stBaseButton-secondary"]:hover {
        background-color: rgba(255, 128, 0, 0.20) !important;
        border-color: #FF8000 !important;
        color: #FF8000 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Toon eerst de bestaande analyses, daarna de knop om een nieuwe te starten.
if len(analysis) == 0:
    st.info("Er zijn nog geen kerkdienstanalyses gestart.")
else:
    # Sorteren op zondagdatum. Tonen we meer dan één analyse, dan krijgt de
    # gebruiker een segmented_control om de volgorde te wisselen. Default is
    # 'Nieuwste eerst' zodat de oranje gemarkeerde 'laatste' analyse ook direct
    # bovenaan staat.
    if len(analysis) > 1:
        sort_order = st.segmented_control(
            "Sorteren op zondagdatum",
            options=["Nieuwste eerst", "Oudste eerst"],
            default="Nieuwste eerst",
            key="dashboard_sort_order",
        )
        # segmented_control kan None teruggeven als de gebruiker de selectie
        # deselecteert; val in dat geval terug op de default.
        sort_order = sort_order or "Nieuwste eerst"
    else:
        sort_order = "Nieuwste eerst"

    # Sorteer op (sermon_date, id). De id-tiebreak zorgt voor een stabiele
    # volgorde bij meerdere analyses op dezelfde zondag (hoogste id = meest
    # recent aangemaakt).
    sorted_analysis = sorted(
        analysis,
        key=lambda it: (it["sermon_date"], it["id"]),
        reverse=(sort_order == "Nieuwste eerst"),
    )

    # Bepaal welke analyse als 'laatste' gemarkeerd wordt: de analyse met de
    # meest recente zondagdatum. Dit is onafhankelijk van de gekozen sortering,
    # zodat dezelfde analyse oranje blijft ook als de gebruiker op 'Oudste
    # eerst' sorteert.
    latest_id = max(
        analysis,
        key=lambda it: (it["sermon_date"], it["id"]),
    )["id"]

    with st.container():
        for item in sorted_analysis:
            id = item["id"]
            title = item["title"]
            congregation = item["church"]["name"]
            sermon_date = datetime.strptime(item["sermon_date"], "%Y-%m-%d").strftime(
                "%d-%m-%Y"
            )
            is_latest = item["id"] == latest_id
            # Markeer analyses waar de agent in een fout is geëindigd. Single_analysis
            # zet `status='error'` bij faal; we tonen dan een rode 'Mislukt'-badge in
            # de tijd-kolom zodat de gebruiker direct ziet welke analyse opnieuw
            # gestart moet worden. Andere statussen (`draft`) blijven onzichtbaar.
            heeft_fout = item.get("status") == "error"
            # Bepaal het label voor het grijze aanmaaktijdstip. Voorkeur:
            # `created_at` uit de API (volledige datum+tijd); fallback: alleen
            # de HH:MM-suffix uit de auto-gegenereerde titel voor oude records.
            _, aanmaaktijd_titel = _split_aanmaaktijd(title)
            aanmaak_label = _format_aanmaak_label(
                item.get("created_at"), aanmaaktijd_titel
            )
            # Vier kolommen: knop, aanmaaktijdstip (grijs), Word-export-knop,
            # verwijder-knop. De tijd-kolom krijgt ~20% van de breedte zodat
            # 'dd-mm-yyyy HH:MM' netjes past. `vertical_alignment="center"`
            # lijnt het grijze label op de verticale as van de knop uit. De
            # Word-kolom (📄) staat tussen tijd en verwijder, zoals gevraagd.
            col_btn, col_time, col_word, col_del = st.columns(
                [6, 2, 1, 1], vertical_alignment="center"
            )
            # Alleen de hoofdknop van de laatste analyse krijgt een geïdentificeerde
            # container (via key='dashboard_latest_analysis'); de CSS bovenaan de
            # pagina vindt deze container op basis van de `st-key-...`-klasse en
            # kleurt alleen deze specifieke knop oranje.
            btn_container = (
                col_btn.container(key="dashboard_latest_analysis")
                if is_latest
                else col_btn
            )
            with btn_container:
                st.button(
                    f"{format_title(title, congregation, sermon_date)}",
                    type="secondary",
                    key=item["id"],
                    use_container_width=True,
                    on_click=lambda id=id: set_analysis_id(id)
                )
            with col_time:
                # Bij een mislukte analyse vervangt een rode 'Mislukt'-badge het
                # grijze aanmaaktijdstip. De timestamp is in dat geval minder
                # relevant dan het signaal dat de analyse opnieuw gestart moet
                # worden; ze in elkaar plakken zou de kolom te druk maken.
                if heeft_fout:
                    st.markdown(
                        "<span style='color: #c62828; font-size: 0.9em;'>"
                        "⚠️ Mislukt</span>",
                        unsafe_allow_html=True,
                    )
                # Alleen tonen als we een aanmaaktijdstip hebben (uit API of
                # als fallback uit de titel). Voor custom titels zonder
                # HH:MM-suffix én zonder `created_at` blijft de kolom leeg.
                elif aanmaak_label:
                    st.markdown(
                        f"<span style='color: #888; font-size: 0.9em;'>{aanmaak_label}</span>",
                        unsafe_allow_html=True,
                    )
            with col_word:
                # Word-export: opent een popup-dialog die het document
                # opbouwt en als download aanbiedt. Zelfde interactiepatroon
                # als de verwijder-knop hiernaast (session_state + dialog).
                if st.button(
                    ":material/description:",
                    key=f"word_{item['id']}",
                    help="Exporteer als Word-document",
                ):
                    st.session_state["_pending_word_export"] = item
                    word_export_dialog()
            with col_del:
                # Verwijder-knop: sla het item op in session_state en open de bevestigingsdialoog.
                if st.button("✕", key=f"delete_{item['id']}", help="Verwijder analyse"):
                    st.session_state["_pending_delete_analysis"] = item
                    confirm_delete_analysis()

# Verberg de "Nieuwe analyse"-knop zodra de early-test-tokenlimiet is
# overschreden. Samen met het verdwijnen van de gelijknamige sidebar-link
# (zie src/utils/utils.render_sidebar) is dit de UI-consequentie van de
# oranje waarschuwing hierboven: de gebruiker kan geen nieuwe analyse
# starten tot een beheerder de limiet op UserPreferences heeft verhoogd.
if not _limiet_overschreden:
    new_analysis = st.button("Nieuwe analyse", type="primary")

    if new_analysis:
        st.switch_page(
            f"{st.session_state['page_navigation_dir']}/analyses/new_analysis.py"
        )

if "selected_analysis_id" in st.session_state:
    analysis_id = st.session_state.selected_analysis_id
    del st.session_state.selected_analysis_id
    # Navigeer alleen als het ID een geldig geheel getal is; een None-waarde
    # zou ?analysis_id=None in de URL produceren en de overzichtspagina laten crashen.
    if analysis_id is not None:
        st.switch_page(
            f'{st.session_state["page_navigation_dir"]}/analysis_results/overview.py',
            query_params={"analysis_id": analysis_id}
        )