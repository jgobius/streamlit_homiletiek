import requests
import streamlit as st
from streamlit_cookies_controller import CookieController

from src.api.jwthandler import JwtHandler
from src.api.handler import APIHandler

# Sleutel waaronder het refresh token in de browser-cookie wordt opgeslagen.
_COOKIE_KEY = "auth_refresh_token"

# CSS voor donker thema (oranje accent, donkere achtergronden).
_DARK_CSS = """<style>
:root {
    --primary-color: #FF8000;
    --background-color: #0E1117;
    --secondary-background-color: #262730;
    --text-color: #FAFAFA;
}
/* Hoofdachtergrond */
[data-testid="stApp"] {
    background-color: #0E1117;
    color: #FAFAFA;
}
/* Html/body — voorkomt witte flash bij overscroll-bounce (macOS) en
   witte ruimte rondom wanneer de app-root niet het hele scherm vult. */
html, body {
    background-color: #0E1117 !important;
}
/* Zijbalk */
[data-testid="stSidebar"] > div:first-child {
    background-color: #262730;
}
/* Bovenste balk */
[data-testid="stHeader"] {
    background-color: rgba(14, 17, 23, 0.9);
}
/* Secundaire knoppen */
[data-testid="stBaseButton-secondary"] {
    background-color: #262730 !important;
    color: #FAFAFA !important;
    border-color: #4A4A5A !important;
}
/* Primaire knoppen — actieve staat (oranje) en uitgeschakelde staat
   (leesbaar grijs). Standaard disabled werd bijna onzichtbaar. */
[data-testid="stBaseButton-primary"] {
    background-color: #FF8000 !important;
    color: #FFFFFF !important;
    border-color: #FF8000 !important;
}
[data-testid="stBaseButton-primary"] * {
    color: #FFFFFF !important;
}
[data-testid="stBaseButton-primary"]:disabled,
[data-testid="stBaseButton-primary"][disabled] {
    background-color: #3D3D4F !important;
    color: #B0B0C0 !important;
    border-color: #6A6A7A !important;
}
[data-testid="stBaseButton-primary"]:disabled *,
[data-testid="stBaseButton-primary"][disabled] * {
    color: #B0B0C0 !important;
}
/* Secundaire knoppen in uitgeschakelde staat — ook leesbaar houden. */
[data-testid="stBaseButton-secondary"]:disabled,
[data-testid="stBaseButton-secondary"][disabled] {
    background-color: #1A1C24 !important;
    color: #B0B0C0 !important;
    border-color: #6A6A7A !important;
}
[data-testid="stBaseButton-secondary"]:disabled *,
[data-testid="stBaseButton-secondary"][disabled] * {
    color: #B0B0C0 !important;
}
/* Selectiemenu — zichtbare container */
[data-baseweb="select"] > div:first-child {
    background-color: #262730 !important;
    border-color: #4A4A5A !important;
}
/* Selectiemenu — geselecteerde tekst (zowel span- als div-varianten). */
[data-baseweb="select"] span,
[data-baseweb="select"] div[value],
[data-baseweb="select"] div[role="combobox"] div {
    color: #FAFAFA !important;
}
/* Selectiemenu — open/close-chevron (baseweb icon) was te donker grijs. */
[data-baseweb="select"] [data-baseweb="icon"] svg,
[data-baseweb="select"] [data-baseweb="icon"] path,
[data-baseweb="select"] svg[title="open"] path,
[data-baseweb="select"] svg[title="Clear value"] path {
    fill: #FAFAFA !important;
}
/* Selectiemenu — dropdown lijst en opties. Streamlit rendert de opties
   via li[role="option"] binnen een virtueel gescrolde div; we dekken
   beide patronen (baseweb én role-based). */
[data-baseweb="menu"],
ul[role="listbox"],
[role="listbox"] {
    background-color: #262730 !important;
}
[data-baseweb="option"],
li[role="option"] {
    background-color: #262730 !important;
    color: #FAFAFA !important;
}
[data-baseweb="option"] *,
li[role="option"] * {
    color: #FAFAFA !important;
}
[data-baseweb="option"]:hover,
li[role="option"]:hover {
    background-color: #3D3D4F !important;
}
/* Geselecteerde optie krijgt oranje accent. */
li[role="option"][aria-selected="true"] {
    background-color: #3D3D4F !important;
}
li[role="option"][aria-selected="true"] * {
    color: #FF8000 !important;
}
/* Virtuele scroller (de div-wrapper rond de li-opties) — achtergrond
   moet ook donker zijn anders lekt wit door tussen de items. */
[data-baseweb="popover"] div[style*="overflow: auto"],
[data-baseweb="popover"] div[style*="will-change: transform"] {
    background-color: #262730 !important;
}
/* Hoofd-menu (hamburger rechtsboven) — dropdownmenu met Rerun/Settings/...
   Items zijn ul[role=option] met li/span inhoud; allen donker maken. */
[data-testid="stMainMenuList"],
[data-testid="stMainMenuList"] ul[role="option"],
[data-testid="stMainMenuList"] li,
[data-testid="stMainMenuList"] span {
    background-color: #262730 !important;
    color: #FAFAFA !important;
}
[data-testid="stMainMenuList"] ul[role="option"]:hover,
[data-testid="stMainMenuList"] ul[role="option"]:hover li,
[data-testid="stMainMenuList"] ul[role="option"]:hover span {
    background-color: #3D3D4F !important;
}
[data-testid="stMainMenuDivider"] {
    background-color: #6A6A7A !important;
    border-color: #6A6A7A !important;
}
/* Tekst-, getal- en datum-invoervelden */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stDateInput"] input,
[data-testid="stDateInput"] [data-baseweb="input"],
[data-testid="stDateInput"] [data-baseweb="input"] > div,
[data-testid="stTimeInput"] input {
    background-color: #262730 !important;
    color: #FAFAFA !important;
    border-color: #4A4A5A !important;
}
/* Datumkiezer (popover-kalender van st.date_input). De baseweb-kalender
   heeft geen eigen data-baseweb="calendar" attribuut op alle lagen;
   daarom targeten we via role/aria en de nav-knop labels. */
[data-baseweb="calendar"],
[data-baseweb="calendar"] > div,
[data-baseweb="datepicker"],
[data-baseweb="calendar-header"],
[role="grid"][aria-roledescription="Calendar month"],
[role="grid"][aria-roledescription="Calendar month"] [role="row"],
[role="gridcell"] {
    background-color: #262730 !important;
    color: #FAFAFA !important;
}
[data-baseweb="calendar"] *,
[role="gridcell"] > div {
    color: #FAFAFA !important;
    background-color: transparent !important;
}
/* Navigatie- en maand/jaar-knoppen in de kalenderheader. */
button[aria-label="Previous month."],
button[aria-label="Next month."],
button[aria-live="polite"] {
    background-color: transparent !important;
    color: #FAFAFA !important;
    border-color: transparent !important;
}
button[aria-label="Previous month."] svg,
button[aria-label="Next month."] svg,
button[aria-live="polite"] svg {
    fill: #FAFAFA !important;
}
button[aria-label="Previous month."]:disabled,
button[aria-label="Next month."]:disabled {
    color: #6A6A7A !important;
}
button[aria-label="Previous month."]:disabled svg,
button[aria-label="Next month."]:disabled svg {
    fill: #6A6A7A !important;
}
/* Weekdag-kopjes (Su Mo Tu We Th Fr Sa) — via alt-attribuut. */
div[alt="Sunday"],
div[alt="Monday"],
div[alt="Tuesday"],
div[alt="Wednesday"],
div[alt="Thursday"],
div[alt="Friday"],
div[alt="Saturday"] {
    background-color: #262730 !important;
    color: #FAFAFA !important;
}
/* Niet-beschikbare datums (buiten range/verleden) — doffer grijs. */
[role="gridcell"][aria-label*="Not available"],
[role="gridcell"][aria-label*="Not available"] > div {
    color: #6A6A7A !important;
}
/* Geselecteerde datum — oranje accent. */
[data-baseweb="calendar"] [aria-selected="true"],
[role="gridcell"][aria-label*="Selected"] {
    background-color: #FF8000 !important;
    color: #FFFFFF !important;
}
[data-baseweb="calendar"] [aria-selected="true"] *,
[role="gridcell"][aria-label*="Selected"] > div {
    color: #FFFFFF !important;
    background-color: transparent !important;
}
/* Hyperlinks in markdown — standaard donkerblauw, onleesbaar op dark bg.
   Uitgezonderd st.page_link dat al zijn eigen styling heeft. */
a:not([data-testid="stPageLink-NavLink"]),
a:not([data-testid="stPageLink-NavLink"]):visited {
    color: #58A6FF !important;
}
a:not([data-testid="stPageLink-NavLink"]):hover {
    color: #79BBFF !important;
}
/* Widget-labels (st.text_input, st.selectbox, st.number_input, ...) —
   labels boven invoervelden werden te dof grijs gerenderd. */
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label,
label[data-testid="stWidgetLabel"] {
    color: #FAFAFA !important;
}
/* Caption-tekst (st.caption) — standaard dof grijs, te donker tegen bg.
   Bijna wit zodat ook meerregelige captions in de sidebar (token-
   verbruik) en ⚠️-waarschuwingen goed leesbaar zijn. */
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p,
[data-testid="stCaptionContainer"] p *,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
small {
    color: #F5F5FA !important;
}
/* Meldingen (st.info/success/warning/error) — standaard lichtgekleurde
   achtergrond met donkere tekst, onleesbaar in donker thema.
   Zowel de buitencontainer (stAlertContainer) als de variantcontent
   krijgen dezelfde kleur zodat er geen twee-tonig blok ontstaat. */
[data-testid="stAlert"],
[data-testid="stNotification"] {
    color: #FAFAFA !important;
    background-color: transparent !important;
}
[data-testid="stAlert"] *,
[data-testid="stNotification"] * {
    color: #FAFAFA !important;
}
/* Info — uniform blauw. */
[data-testid="stAlert"]:has([data-testid="stAlertContentInfo"]) [data-testid="stAlertContainer"],
[data-testid="stAlertContentInfo"],
[data-testid="stNotificationContentInfo"] {
    background-color: #1A3A5A !important;
    border-color: #2D5A8A !important;
}
/* Success — uniform groen. */
[data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]) [data-testid="stAlertContainer"],
[data-testid="stAlertContentSuccess"],
[data-testid="stNotificationContentSuccess"] {
    background-color: #1A4A2A !important;
    border-color: #2D7A4A !important;
}
/* Warning — uniform geel/oker. */
[data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]) [data-testid="stAlertContainer"],
[data-testid="stAlertContentWarning"],
[data-testid="stNotificationContentWarning"] {
    background-color: #5A4A1A !important;
    border-color: #8A7A2D !important;
}
/* Error — uniform rood. */
[data-testid="stAlert"]:has([data-testid="stAlertContentError"]) [data-testid="stAlertContainer"],
[data-testid="stAlertContentError"],
[data-testid="stNotificationContentError"] {
    background-color: #5A1A2A !important;
    border-color: #8A2D4A !important;
}
/* Markdown-tekst expliciet wit zetten zodat geen enkele nested context
   (behalve alerts hierboven die zelf reeds wit gezet zijn) donkere
   tekst doorlekt. */
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4,
[data-testid="stMarkdownContainer"] h5,
[data-testid="stMarkdownContainer"] h6 {
    color: #FAFAFA !important;
}
/* Inline code (`...`) en code-blokken — standaard witte achtergrond. */
code {
    background-color: #2A2D3A !important;
    color: #FF8000 !important;
    border: 1px solid #4A4A5A !important;
}
pre,
pre code {
    background-color: #1A1C24 !important;
    color: #FAFAFA !important;
}
[data-testid="stCodeBlock"] {
    background-color: #1A1C24 !important;
}
/* Radio-knoppen (st.radio) en checkboxes — de buitencirkel/box werd
   fel wit. Zachter grijs zodat hij niet overstraalt op donker thema. */
label[data-baseweb="radio"] > div:first-child,
label[data-baseweb="checkbox"] > div:first-child {
    background-color: #3D3D4F !important;
    border-color: #6A6A7A !important;
}
/* Geselecteerde radio/checkbox houdt oranje accent — alleen de cirkel/
   box (eerste div van het label), niet de tekst-div die ná de input
   staat. Daarom geen ' input:checked + div'-selector: die zou de
   tekst-container oranje kleuren. */
label[data-baseweb="radio"][aria-checked="true"] > div:first-child,
label[data-baseweb="checkbox"][aria-checked="true"] > div:first-child {
    background-color: #FF8000 !important;
    border-color: #FF8000 !important;
}
/* Baseweb-kaart (section[data-baseweb=card]) — o.a. in het Streamlit
   Deploy-venster. Witte bg met lichte iconen was onleesbaar. */
section[data-baseweb="card"] {
    background-color: #1A1C24 !important;
    color: #FAFAFA !important;
    border: 1px solid #6A6A7A !important;
}
section[data-baseweb="card"] *:not(svg):not(path):not(img) {
    color: #FAFAFA !important;
}
/* Minimal button variant (bv. 'Learn more' in het Deploy-venster). */
[data-testid="stBaseButton-minimal"] {
    background-color: transparent !important;
    color: #FAFAFA !important;
    border-color: transparent !important;
}
[data-testid="stBaseButton-minimal"] * {
    color: #FAFAFA !important;
}
[data-testid="stBaseButton-minimal"]:hover {
    background-color: #3D3D4F !important;
}
/* Tooltip (hover) op knoppen / page_links — standaard wit. */
[data-baseweb="tooltip"],
[data-baseweb="tooltip"] > div,
[role="tooltip"] {
    background-color: #1A1C24 !important;
    color: #FAFAFA !important;
    border: 1px solid #6A6A7A !important;
}
[data-baseweb="tooltip"] *,
[role="tooltip"] * {
    color: #FAFAFA !important;
}
/* Cache-/running-status ('Running get_cached_data(...)') en spinners. */
[data-testid="stStatusWidget"],
[data-testid="stStatusWidget"] > div,
[data-testid="stSpinner"],
[data-testid="stSpinner"] > div,
[data-testid="stToolbar"] {
    background-color: #1A1C24 !important;
    color: #FAFAFA !important;
}
[data-testid="stStatusWidget"] *,
[data-testid="stSpinner"] * {
    color: #FAFAFA !important;
}
/* Code-span in de statusbanner (bv. get_cached_data(...)) houdt oranje
   tekst, maar achtergrond matcht de banner. */
[data-testid="stStatusWidget"] code,
[data-testid="stSpinner"] code {
    background-color: #262730 !important;
    color: #FF8000 !important;
    border-color: #4A4A5A !important;
}
[data-testid="stNumberInputStepDown"],
[data-testid="stNumberInputStepUp"] {
    background-color: #262730 !important;
    color: #FAFAFA !important;
    border-color: #4A4A5A !important;
}
[data-testid="stNumberInputStepDown"] svg,
[data-testid="stNumberInputStepUp"] svg {
    fill: #FAFAFA !important;
}
[data-testid="stNumberInputStepDown"]:hover,
[data-testid="stNumberInputStepUp"]:hover {
    background-color: #3D3D4F !important;
}
/* Placeholder-tekst in invoervelden — standaard te donker in donker thema. */
[data-testid="stTextInput"] input::placeholder,
[data-testid="stNumberInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder,
input::placeholder,
textarea::placeholder {
    color: #B0B0C0 !important;
    opacity: 1 !important;
}
/* Expanders — oud <details>/<summary>-patroon. Lichtere randkleur zodat de
   scheidingslijn tussen header en inhoud zichtbaar blijft op donkere bg. */
[data-testid="stExpander"] details {
    background-color: #262730 !important;
    border-color: #6A6A7A !important;
}
[data-testid="stExpander"] summary {
    background-color: #262730 !important;
    color: #FAFAFA !important;
    border-bottom: 1px solid #6A6A7A !important;
}
/* Expanders — nieuw div-gebaseerd patroon (headerblok is geen <summary> meer). */
[data-testid="stExpander"],
[data-testid="stExpander"] > div,
[data-testid="stExpander"] > div > div {
    background-color: #262730 !important;
    border-color: #6A6A7A !important;
}
[data-testid="stExpander"] [role="button"],
[data-testid="stExpanderHeader"],
[data-testid="stExpanderDetails"] {
    background-color: #262730 !important;
    color: #FAFAFA !important;
    border-bottom: 1px solid #6A6A7A !important;
}
[data-testid="stExpander"] p,
[data-testid="stExpander"] span,
[data-testid="stExpander"] svg {
    color: #FAFAFA !important;
    fill: #FAFAFA !important;
}
/* Formuliercontainers */
[data-testid="stForm"] {
    background-color: #1A1C24 !important;
    border-color: #4A4A5A !important;
}
/* Horizontale scheidingslijnen (st.divider en <hr>) — standaard te donker
   tegen de app-achtergrond, opgehelderd voor betere zichtbaarheid. */
hr,
[data-testid="stDivider"],
[data-testid="stHeadingDivider"] {
    border-color: #6A6A7A !important;
    background-color: #6A6A7A !important;
    color: #6A6A7A !important;
}
/* Dialoog-/modaal-venster (st.dialog) — standaard witte kaart wordt donker.
   Zichtbare lichte rand + schaduw zodat de buitenkant van het venster
   afsteekt tegen de donkere app-achtergrond. */
div[role="dialog"],
[data-testid="stDialog"],
[data-testid="stDialog"] > div {
    background-color: #1A1C24 !important;
    color: #FAFAFA !important;
    border: 1px solid #6A6A7A !important;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6) !important;
}
[data-testid="stDialog"] h1,
[data-testid="stDialog"] h2,
[data-testid="stDialog"] h3,
[data-testid="stDialog"] p,
[data-testid="stDialog"] label,
[data-testid="stDialog"] span {
    color: #FAFAFA !important;
}
/* Sluit-kruisje en andere iconen in dialoog zichtbaar houden op donkere
   achtergrond. De pictogrammen gebruiken vaak stroke: currentcolor, dus
   zowel fill/stroke expliciet zetten als color op de knop-ouder. */
[data-testid="stDialog"] button,
div[role="dialog"] button[aria-label="Close"],
div[role="dialog"] [data-testid="stDialogCloseButton"] {
    color: #FAFAFA !important;
}
[data-testid="stDialog"] button svg,
div[role="dialog"] button svg,
div[role="dialog"] [aria-label="Close"] svg {
    fill: #FAFAFA !important;
    stroke: #FAFAFA !important;
}
[data-testid="stDialog"] button svg path,
div[role="dialog"] button svg path {
    stroke: #FAFAFA !important;
}
/* Tabbladen (st.tabs) — inactieve tabs waren wit. */
[data-baseweb="tab-list"] {
    background-color: transparent !important;
    border-bottom: 1px solid #4A4A5A !important;
}
[data-baseweb="tab"] {
    background-color: #262730 !important;
    color: #FAFAFA !important;
}
[data-baseweb="tab"][aria-selected="true"] {
    background-color: #1A1C24 !important;
    color: #FF8000 !important;
}
/* Segmented control (st.segmented_control) — bv. Basis/Verdieping/Perspectieven/... */
[data-testid="stBaseButton-segmented_control"],
[data-testid="stBaseButton-segmented_controlActive"] {
    background-color: #262730 !important;
    color: #FAFAFA !important;
    border-color: #4A4A5A !important;
}
[data-testid="stBaseButton-segmented_control"] p,
[data-testid="stBaseButton-segmented_control"] span,
[data-testid="stBaseButton-segmented_controlActive"] p,
[data-testid="stBaseButton-segmented_controlActive"] span {
    color: #FAFAFA !important;
}
/* Actief segment krijgt oranje accent (matcht primaryColor). */
[data-testid="stBaseButton-segmented_controlActive"] {
    background-color: #1A1C24 !important;
    border-color: #FF8000 !important;
}
[data-testid="stBaseButton-segmented_controlActive"] p,
[data-testid="stBaseButton-segmented_controlActive"] span {
    color: #FF8000 !important;
}
/* Popover / info-knop (st.popover) — trigger en paneel. */
[data-testid="stPopover"] button,
[data-testid="stPopoverButton"],
button[data-testid="baseButton-headerNoPadding"] {
    background-color: #262730 !important;
    color: #FAFAFA !important;
    border-color: #4A4A5A !important;
}
[data-baseweb="popover"],
[data-baseweb="popover"] > div {
    background-color: #262730 !important;
    color: #FAFAFA !important;
}
/* Page-links (st.page_link) — actieve pagina toonde witte balk; tekst was te donker. */
a[data-testid="stPageLink-NavLink"] {
    color: #FAFAFA !important;
}
a[data-testid="stPageLink-NavLink"] span,
a[data-testid="stPageLink-NavLink"] p {
    color: #FAFAFA !important;
}
a[data-testid="stPageLink-NavLink"][aria-current="page"],
a[data-testid="stPageLink-NavLink"][data-current="true"] {
    background-color: #262730 !important;
}
a[data-testid="stPageLink-NavLink"][aria-current="page"] span,
a[data-testid="stPageLink-NavLink"][aria-current="page"] p,
a[data-testid="stPageLink-NavLink"][data-current="true"] span,
a[data-testid="stPageLink-NavLink"][data-current="true"] p {
    color: #FF8000 !important;
}
</style>"""

# CSS voor licht thema (oranje accent, witte achtergronden).
_LIGHT_CSS = """<style>
:root {
    --primary-color: #FF8000;
    --background-color: #FFFFFF;
    --secondary-background-color: #F0F2F6;
    --text-color: #31333F;
}
</style>"""


def _inject_theme_css() -> None:
    """Injecteer CSS voor het huidige thema op basis van de voorkeur in session_state."""
    dark = st.session_state.get('dark_mode', False)
    st.markdown(_DARK_CSS if dark else _LIGHT_CSS, unsafe_allow_html=True)


def _hydrate_user_preferences() -> None:
    """Laad de UI-voorkeuren van de ingelogde gebruiker in session_state.

    Wordt één keer per sessie aangeroepen, direct na inloggen of na het
    herstellen van een sessie uit de refresh-token-cookie. Faalt het verzoek
    (bijv. backend niet bereikbaar of endpoint nog niet uitgerold), dan valt
    dark_mode terug op False zodat de app gewoon licht blijft.
    """
    handler = st.session_state.get('api_handler')
    if not handler:
        return
    try:
        prefs = handler.get('api/user-preferences/')
    except requests.exceptions.RequestException:
        # Endpoint niet beschikbaar of netwerkfout — val terug op licht thema.
        st.session_state['dark_mode'] = False
        return
    if isinstance(prefs, dict):
        st.session_state['dark_mode'] = bool(prefs.get('dark_mode', False))
    else:
        st.session_state['dark_mode'] = False

st.session_state['page_navigation_dir'] = 'page_navigation'


def _try_restore_session(controller: CookieController) -> bool:
    """Herstel api_handler vanuit een opgeslagen refresh token cookie. Geeft True terug als herstel lukte."""
    try:
        refresh_token = controller.get(_COOKIE_KEY)
    except TypeError:
        # Cookies zijn nog niet geladen op de eerste render — wacht op volgende render.
        return False
    if not refresh_token:
        return False
    try:
        jwt_handler = JwtHandler.from_refresh_token(
            refresh_token=refresh_token,
            base_url=st.secrets["API_BASE_URL"],
            access_endpoint="/api/token/",
            refresh_endpoint="/api/token/refresh/",
        )
        st.session_state['api_handler'] = APIHandler(
            base_url=st.secrets["API_BASE_URL"],
            jwt_handler=jwt_handler,
        )
        return True
    except Exception:
        # Verwijder ongeldige cookie zodat de gebruiker opnieuw kan inloggen.
        controller.remove(_COOKIE_KEY)
        return False


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


def _render_token_usage_sidebar() -> None:
    # Toon het tokenverbruik van de huidige analyse in de sidebar.
    handler = st.session_state.get('api_handler')
    if not handler:
        return
    analysis_id = st.session_state.get('current_analysis_id')
    endpoint = f"api/token-usage/?sermon_analysis_id={analysis_id}" if analysis_id else "api/token-usage/"
    try:
        usage = handler.get(endpoint)
    except requests.exceptions.HTTPError:
        # Endpoint nog niet beschikbaar in deze omgeving; sidebar stilletjes overslaan.
        return
    if not isinstance(usage, dict):
        return
    total_input, total_output, total_cost = _calc_token_totals(usage)
    with st.sidebar:
        st.divider()
        st.caption(
            f"Tokens huidige analyse: {total_input:,} in / {total_output:,} uit  \n"
            f"Kosten huidige analyse: €{total_cost:.2f}"
        )


def _render_cumulative_token_usage_sidebar() -> None:
    # Toon het cumulatieve tokenverbruik van de ingelogde gebruiker in de sidebar.
    handler = st.session_state.get('api_handler')
    if not handler:
        return
    try:
        usage = handler.get("api/token-usage/cumulative/")
    except requests.exceptions.HTTPError:
        # Endpoint nog niet beschikbaar in deze omgeving; sidebar stilletjes overslaan.
        return
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
    # Stel paginatitel en favicon in (oranje kruis-icoon).
    st.set_page_config(page_icon="static/favicon.png")
    # Initialiseer de cookie controller en sla hem op in session_state zodat
    # andere pagina's hem kunnen ophalen zonder hem opnieuw te initialiseren.
    controller = CookieController()
    st.session_state['cookie_controller'] = controller

    # Injecteer thema-CSS direct na het initialiseren van de controller, nog vóór
    # eventuele st.stop() in de sessie-herstel-logica hieronder. De voorkeur zit
    # in session_state['dark_mode'] en wordt na login gevuld vanuit het backend-
    # endpoint /api/user-preferences/ (zie _hydrate_user_preferences). Op de
    # eerste render vóór login is dark_mode afwezig — dan toont Streamlit het
    # standaard lichte thema, wat acceptabel is voor de kortstondige login-flash.
    _inject_theme_css()

    # Schrijf een pending refresh token naar de cookie zodra de controller gereed is.
    # Dit token wordt door login.py klaargezet na een succesvolle login.
    pending = st.session_state.get('_pending_refresh_token')
    if pending:
        try:
            controller.set(_COOKIE_KEY, pending)
            st.session_state.pop('_pending_refresh_token')
        except TypeError:
            pass  # controller nog niet gereed — volgende render probeert het opnieuw

    if 'api_handler' not in st.session_state:
        if not _try_restore_session(controller):
            # st.stop() stopt Python maar de browser verwerkt de render nog,
            # waardoor de cookie controller JS kan draaien en data terugstuurt.
            # Die component-callback triggert de volgende render mét cookies.
            # Begrens tot 1 poging zodat er geen oneindige lus ontstaat als er geen cookie is.
            attempts = st.session_state.get('_restore_attempts', 0)
            if attempts < 1:
                st.session_state['_restore_attempts'] = attempts + 1
                st.stop()

    # Verwijder de teller zodra we ingelogd zijn.
    if 'api_handler' in st.session_state:
        st.session_state.pop('_restore_attempts', None)
        # Haal de persoonlijke UI-voorkeur (dark_mode) op uit de backend zodra de
        # gebruiker is ingelogd. Dit gebeurt maar één keer per sessie: daarna
        # leeft de waarde in session_state en wordt hij bij wijziging via de
        # toggle ook naar de backend teruggeschreven (zie _sla_thema_voorkeur_op
        # in src/utils/utils.py). Na het ophalen renderen we het thema opnieuw
        # zodat de donkere CSS direct op de eerste post-login render zichtbaar is.
        if 'dark_mode' not in st.session_state:
            _hydrate_user_preferences()
            _inject_theme_css()

    welcome_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/welcome.py", title='Welcome')
    login_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/login.py", title='Inloggen')
    logout_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/logout.py", title='Uitloggen')
    register_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/register.py", title='Registreren')
    dashboard_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py", title='Overzicht kerkdienstanalyses')
    # settings_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/settings.py", title='Instellingen')
    new_analysis_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/analyses/new_analysis.py", title='Nieuwe kerkdienstanalyse')
    liturgisch_jaar_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/analysis_results/liturgisch_jaar.py", title='Liturgisch jaar')
    church_overview_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/churches/churches_overview.py", title='Overzicht gemeenten')
    new_church_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/churches/new_church.py", title='Nieuwe gemeente')

    analysis_overview_page = st.Page(page=f"{st.session_state['page_navigation_dir']}/analysis_results/overview.py", title='Analyse overzicht')

    pages = [dashboard_page, new_analysis_page, liturgisch_jaar_page, church_overview_page, new_church_page, analysis_overview_page, logout_page]

    if 'api_handler' not in st.session_state:
        pg = st.navigation([welcome_page, login_page, register_page, dashboard_page], position='hidden')
        pg.run()
    else:
        pg = st.navigation(pages, position='hidden')
        pg.run()
        # Toon tokenverbruik van de huidige analyse op de analyse-overzichtspagina.
        if pg == analysis_overview_page:
            _render_token_usage_sidebar()
        # Toon cumulatief tokenverbruik op de hoofdpagina (dashboard).
        if pg == dashboard_page:
            _render_cumulative_token_usage_sidebar()

if __name__ == "__main__":
    main()
