from typing import Any
from concurrent.futures import ThreadPoolExecutor

import requests
import os
import json
import re
import time
from typing import Any

import streamlit as st
import requests

from src.api.agent_request import AgentRequest
# render_suggestions_trigger wordt lazy binnen render_sidebar() geïmporteerd;
# src.components.user_suggestions importeert zelf valideer_tekstinvoer uit
# deze module, dus een top-level import hier creëert een circular import
# die faalt omdat valideer_tekstinvoer pas verderop in dit bestand
# gedefinieerd wordt.

# Timeout (seconden) per POST naar /structured_scripture/. De backend-agent
# voert 2+N LLM-calls per lezing uit (boek-extractie + tekst per hoofdstuk +
# structurering); 180 s geeft voldoende ruimte voor langere hoofdstukken
# terwijl een echt hangende verbinding niet onbeperkt de UI blokkeert.
_STRUCTURED_SCRIPTURE_TIMEOUT_SECONDS = 180

# Maximum aantal gelijktijdige POSTs naar /structured_scripture/. Gelijk aan
# het aantal mogelijke lezingen (READING_TYPES, 4) zodat elke lezing parallel
# loopt in plaats van serieel. Hoger dan 4 voegt niets toe omdat het dialoog
# nooit meer dan vier lezingen toelaat.
_STRUCTURED_SCRIPTURE_MAX_WORKERS = 4

# Alle bijbelboeken in de Nederlandse volgorde — gebruikt in het eigen-lezingen-dialoogvenster.
BIBLE_BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numeri", "Deuteronomium", "Jozua", "Rechters", "Ruth",
    "1 Samuel", "2 Samuel", "1 Koningen", "2 Koningen", "1 Kronieken", "2 Kronieken", "Ezra",
    "Nehemia", "Ester", "Job", "Psalmen", "Spreuken", "Prediker", "Hooglied", "Jesaja",
    "Jeremia", "Klaagliederen", "Ezechiël", "Daniël", "Hosea", "Joël", "Amos", "Obadja",
    "Jona", "Micha", "Nahum", "Habakuk", "Sefanja", "Haggai", "Zacharia", "Maleachi",
    "Mattheüs", "Marcus", "Lucas", "Johannes", "Handelingen", "Romeinen",
    "1 Korintiërs", "2 Korintiërs", "Galaten", "Efeziërs", "Filippenzen", "Kolossenzen",
    "1 Tessalonicenzen", "2 Tessalonicenzen", "1 Timoteüs", "2 Timoteüs", "Titus", "Filemon",
    "Hebreeën", "Jakobus", "1 Petrus", "2 Petrus", "1 Johannes", "2 Johannes", "3 Johannes",
    "Judas", "Openbaring",
]

# Lezing-typen voor het eigen-lezingen-dialoogvenster.
READING_TYPES = ["Eerste lezing", "Tweede lezing", "Derde lezing", "Vierde lezing"]


def sanitize_cv(key: str) -> None:
    """Verwijder ongeldige tekens uit een hoofdstuk/verzen-veld.

    Toegestaan zijn alleen cijfers, ':', '-' en de letters 'a'/'b' (voor
    half-vers-aanduidingen zoals "5a"). Wordt als ``on_change``-callback
    gebruikt door zowel het eigen-lezingen-dialoog bij het aanmaken van
    een analyse, als de "Selectie instellen"-dialog op het Basis-tabblad
    — daarom centraal in utils zodat beide exact dezelfde whitelist hanteren.
    """
    raw = st.session_state.get(key, "")
    cleaned = "".join(c for c in raw if c.isdigit() or c in ":-ab")
    if cleaned != raw:
        st.session_state[key] = cleaned


def parse_original_scripture(s: str) -> tuple[str, str]:
    """Splits "Genesis 1:1-3" naar ("Genesis", "1:1-3").

    Boeknamen kunnen zelf cijfers bevatten ("1 Korintiërs"), dus de splitsing
    op de eerste spatie volstaat niet. We zoeken de langste prefix uit
    ``BIBLE_BOOKS`` die past — zo wordt "1 Korintiërs 13:4-7" correct
    gesplitst in ("1 Korintiërs", "13:4-7"). Bij geen match geven we een
    leeg boek terug; de aanroeper kan dan een fallback-waarschuwing tonen.
    """
    if not s:
        return "", ""
    for book in sorted(BIBLE_BOOKS, key=len, reverse=True):
        prefix = f"{book} "
        if s.startswith(prefix):
            return book, s[len(prefix):]
    return "", s


# Woordentelling-grenzen voor het 'Eigen preek'-invoerveld. Centraal in utils
# zodat zowel de dialog in overview.py als het bewerk-paneel in
# analysis_results/analyses/volledige_preek.py exact dezelfde limieten
# afdwingen; een prediker moet bij opslaan nooit een andere grens ervaren
# afhankelijk van waar hij bewerkt. Ondergrens voorkomt per ongeluk een
# bijna-leeg fragment; bovengrens is een ruime praktische limiet.
EIGEN_PREEK_MIN_WOORDEN = 500
EIGEN_PREEK_MAX_WOORDEN = 6000


def tel_woorden(tekst: str) -> int:
    """Tel het aantal woorden in een tekst.

    Een woord is elke aaneengesloten reeks niet-witruimte-tekens. Lege
    of None-invoer levert 0 op. Gebruikt door de 'Eigen preek'-dialoog
    voor min/max-validatie bij opslaan, zodat de telling consistent is
    op één plek en niet inline in meerdere callers wordt herhaald.
    """
    if not tekst:
        return 0
    return len(tekst.split())


# Regex-patronen die typische SQL-injectie-pogingen herkennen. We escapen
# niets aan de clientkant — de Django-backend gebruikt parameterized queries
# via het ORM — maar we weigeren invoer met duidelijk kwaadaardige patronen
# zodat sprekende foutmeldingen een poging direct aan de prediker laten zien
# in plaats van pas bij een obscure 400 of 500 van de backend. Hoofdletters
# worden in de check genormaliseerd (re.IGNORECASE).
_SQL_INJECTIE_PATRONEN: tuple[str, ...] = (
    # Commentaar-tekens die statement-afbrekers verbergen.
    r"--\s",
    r"--$",
    r"/\*",
    r"\*/",
    # Quote gevolgd door OR/AND met vergelijking: klassiek "' OR '1'='1".
    r"['\"]\s*(or|and)\s+['\"0-9]",
    # Statement-terminator + nieuw SQL-keyword.
    r";\s*(drop|delete|update|insert|select|alter|truncate|create|grant|exec)\b",
    # UNION-based injectie.
    r"\bunion\s+(all\s+)?select\b",
    # Typische SQL-Server extended stored procedures.
    r"\bxp_cmdshell\b",
    r"\bsp_executesql\b",
    # Hex-encoded payloads (bijv. 0x27 als quote).
    r"\b0x[0-9a-f]{6,}\b",
    # Systeemtabellen die in injectie-probes gebruikt worden.
    r"\binformation_schema\b",
    r"\bpg_sleep\b",
    r"\bwaitfor\s+delay\b",
)

# Eenmalig compileren zodat elke valideer_tekstinvoer()-aanroep niet
# opnieuw alle patronen hoeft te parsen.
_SQL_INJECTIE_REGEX = re.compile(
    "|".join(_SQL_INJECTIE_PATRONEN),
    flags=re.IGNORECASE,
)


def bevat_sql_injectie(tekst: str) -> bool:
    """Detecteer of een tekst een verdacht SQL-injectie-patroon bevat.

    Dit is een extra waarschuwingslaag bovenop de ORM-bescherming van
    de backend; Django's ORM escapet parameters al, maar een frontend-
    check laat een poging direct zien aan de prediker en voorkomt dat
    onzin-invoer tot bij de database-layer komt. False-positives
    worden geaccepteerd — de getroffen tekens (;, --, UNION SELECT,
    quote+OR) horen in gewone invoervelden simpelweg niet thuis.
    """
    if not tekst:
        return False
    return _SQL_INJECTIE_REGEX.search(tekst) is not None


# Patronen voor prompt-injectie: pogingen om het LLM-gedrag te overschrijven
# door expliciete "negeer voorgaande instructies"-zinnen, system-prompt-
# manipulatie, role-switching en bekende jailbreak-namen (DAN, developer
# mode). Velden die richting de agent-pipeline gaan (extra_context, preek-
# tekst, suggesties, aanpassen_dialog) zijn het gevoeligst. De patronen
# zijn bewust specifiek — generieke woorden als 'ignore' of 'negeer'
# blokkeren zonder qualifier zou te veel legitieme tekst raken. Aanpakken
# van false-negatives mag alleen door nieuwe patronen toe te voegen na
# een echt voorbeeld, niet preventief breder maken.
_PROMPT_INJECTIE_PATRONEN: tuple[str, ...] = (
    # Expliciete instructie-negatie (EN). Qualifiers (all/the/above/previous/
    # prior/earlier/your/my/these/any) mogen in willekeurige volgorde en
    # aantal voorkomen; bindend is de combinatie van werkwoord + doelwoord.
    r"\bignore\s+(?:(?:all|the|above|previous|prior|earlier|your|my|these|any)\s+)*(?:instructions?|prompt|rules|guidelines|directives)\b",
    r"\bdisregard\s+(?:(?:all|the|above|previous|prior|earlier|your|my|these|any)\s+)*(?:instructions?|prompt|rules|guidelines|directives)\b",
    # 'forget' vereist een doelwoord dat instructie-/prompt-gerelateerd is;
    # alleen 'forget everything' zou legitieme preektekst kunnen zijn en
    # vang ik daarom niet generiek. Andere injectie-patronen dekken de
    # 'forget everything and act as DAN'-constructie via het jailbreak-deel.
    r"\bforget\s+(?:(?:everything|all|the|your|my|these|any|previous|prior|above|earlier)\s+)+(?:instructions?|prompt|rules|guidelines|directives|system(?:\s+prompt)?)\b",
    # Idem, Nederlandse varianten. Qualifiers (alle/de/bovenstaande/voorgaande/
    # vorige/je/mijn/deze/eerdere) mogen flexibel meedoen, maar het patroon
    # eist altijd dat er een instructie-doelwoord volgt om false-positives
    # op normale preektekst ('vergeet de voorgaande kerkdienst') te vermijden.
    r"\bnegeer\s+(?:(?:alle|de|bovenstaande|voorgaande|vorige|je|mijn|deze|eerdere)\s+)*(?:instructies|prompt|regels|richtlijnen|systeemprompt)\b",
    r"\bvergeet\s+(?:(?:alle|alles|de|je|deze|mijn|eerdere|voorgaande|bovenstaande|vorige)\s+)+(?:instructies|prompt|regels|richtlijnen|systeem|systeemprompt)\b",
    # 'Nieuwe instructies:' — vaak een voorloper op injectie.
    r"\bnew\s+instructions?\s*:",
    r"\bnieuwe\s+instructies?\s*:",
    # System-prompt-manipulatie.
    r"\bsystem\s+prompt\b",
    r"\bsysteem[-\s]?prompt\b",
    r"\boverride\s+(the\s+)?(system|instructions?)\b",
    # Role-switching, alleen met een qualifier die niet in gewone tekst
    # voorkomt (unrestricted, jailbreak, developer, admin, evil).
    r"\byou\s+are\s+(now\s+)?(an?\s+)?(unrestricted|developer|admin|evil|jailbreak|dan)\b",
    r"\bact\s+as\s+(if\s+|though\s+)?(you\s+are\s+)?(an?\s+)?(unrestricted|developer|admin|evil|jailbreak|dan)\b",
    # Expliciete jailbreak-namen.
    r"\bDAN\s+mode\b",
    r"\bdeveloper\s+mode\b",
    r"\bjailbreak(en|ing)?\b",
    # ChatML / special tokens — horen nooit in gebruikersinvoer.
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"<\|system\|>",
    r"<\|user\|>",
    r"<\|assistant\|>",
    # Bracketed prompt-injectie-markers.
    r"\[\[?\s*(SYSTEM|INSTRUCTION|PROMPT)\s*\]\]?",
)

_PROMPT_INJECTIE_REGEX = re.compile(
    "|".join(_PROMPT_INJECTIE_PATRONEN),
    flags=re.IGNORECASE,
)


def bevat_prompt_injectie(tekst: str) -> bool:
    """Detecteer of een tekst een verdacht prompt-injectie-patroon bevat.

    Vrije-tekstvelden in de app (extra_context, preektekst, suggesties,
    bewerk-JSON) belanden in de agent-prompts van homiletiek_agent. Een
    kwaadaardige of slordige plak-actie kan het LLM proberen te sturen
    ("negeer voorgaande instructies..."). Deze check weigert de bekende
    frases vóór ze de prompt bereiken. Het is een lichte eerste laag;
    voor meer zekerheid is llm-guard beschikbaar als zwaardere optie,
    maar die brengt torch + transformers als dependency mee.
    """
    if not tekst:
        return False
    return _PROMPT_INJECTIE_REGEX.search(tekst) is not None


def valideer_tekstinvoer(
    tekst: str,
    max_woorden: int,
    veldnaam: str,
    min_woorden: int = 0,
    verplicht: bool = False,
) -> tuple[bool, str]:
    """Valideer vrije tekstinvoer op lengte (woorden) en SQL-injectie-patronen.

    Eén centrale validator zodat alle invoervelden dezelfde regels en
    foutmeldingen gebruiken. Returned (ok, foutmelding): bij ok=True is
    foutmelding leeg. De caller toont de foutmelding met st.error() en
    breekt de submit af.

    Args:
        tekst: De ingevoerde waarde (kan None/leeg zijn).
        max_woorden: Bovenlimiet voor het aantal woorden (inclusief).
        veldnaam: Menselijke naam voor in de foutmelding, bv. "Voornaam".
        min_woorden: Ondergrens; 0 betekent geen ondergrens voor woorden.
        verplicht: Wanneer True mag het veld niet leeg zijn na strip().
    """
    tekst_strip = (tekst or "").strip()
    if verplicht and not tekst_strip:
        return False, f"{veldnaam} mag niet leeg zijn."
    if not tekst_strip:
        # Lege optionele invoer is geldig; skip verdere checks.
        return True, ""
    aantal = tel_woorden(tekst_strip)
    if min_woorden and aantal < min_woorden:
        return False, f"{veldnaam} bevat {aantal} woord(en); minimaal {min_woorden}."
    if aantal > max_woorden:
        return False, f"{veldnaam} bevat {aantal} woord(en); maximaal {max_woorden} toegestaan."
    if bevat_sql_injectie(tekst_strip):
        return False, f"{veldnaam} bevat tekens die niet zijn toegestaan (verdacht patroon)."
    if bevat_prompt_injectie(tekst_strip):
        return False, (
            f"{veldnaam} bevat een zin die lijkt op een poging om de AI-instructies "
            "te overschrijven. Herschrijf de tekst in normale zinnen."
        )
    return True, ""


# Handmatige overrides voor weergavenamen die in de gedeelde productie-DB
# anders zijn opgeslagen dan we ze in de UI willen tonen. Door dit hier
# centraal te mappen hoeven we de DB niet te muteren voor wat puur een
# label-kwestie is; alle plekken die via `toon_analysenaam` renderen
# (sidebar-menu, paginatitel, afhankelijkheidslabels) krijgen dezelfde naam.
_WEERGAVENAAM_OVERRIDE: dict[str, str] = {
    "Theologie": "Theologische inzichten",
}


def toon_analysenaam(name: str) -> str:
    """Verwijder technische toolmarkeringen uit de weergavenaam van een analyse.

    De backend gebruikt `front_end_name` soms met een suffix als " (Tavily)"
    om interne varianten te onderscheiden. Voor de prediker is die
    implementatie-detail ruis. We strippen het alleen aan het eind en
    negeren hoofdletters, zodat toekomstige varianten (bv. "(Perplexity)")
    later met hetzelfde patroon kunnen. Na het strippen passen we een
    optionele override toe zodat specifieke DB-labels (bv. "Theologie")
    in de UI als gerichter alternatief ("Theologische inzichten") verschijnen.
    """
    if not name:
        return name
    schoon = re.sub(r"\s*\((?:Tavily)\)\s*$", "", name, flags=re.IGNORECASE)
    return _WEERGAVENAAM_OVERRIDE.get(schoon, schoon)


def clean_md(text: str) -> str:
    """Normaleer LLM-gegenereerde markdown voor robuuste Streamlit-weergave.

    Herstelt:
    - Letterlijke \\n escape-sequences naar echte newlines
    - ** tekst ** (spaties binnen bold-markers) naar **tekst**
    """
    if not text:
        return text
    text = text.replace("\\n", "\n")
    text = re.sub(r'\*\*[ \t]+(\S)', r'**\1', text)
    text = re.sub(r'(\S)[ \t]+\*\*', r'\1**', text)
    return text


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
        
def get_data(endpoint:str) -> Any:
    """
    Retrieve data from the API using the specified endpoint.
    This function uses the API handler stored in Streamlit's session state
    to fetch data from the given endpoint.
    Args:
        endpoint (str): The API endpoint path or identifier to fetch data from.
    Returns:
        Any: The data retrieved from the API endpoint.
    Raises:
        KeyError: If 'api_handler' is not found in session state.
        Exception: Any exceptions raised by the underlying API handler's get method.
    """
    
    data = st.session_state['api_handler'].get(endpoint)
    return data

# TTL (in seconden) voor referentie-data die via get_cached_data opgehaald wordt
# (liedboeken, bijbelvertalingen, roosterlezingen, e.d.). Een korte TTL zorgt
# ervoor dat wijzigingen op de backend binnen een minuut automatisch zichtbaar
# worden zonder dat de gebruiker handmatig hoeft te verversen. De handmatige
# Ververs-knop in de zijbalk roept daarnaast get_cached_data.clear() aan voor
# een directe invalidatie.
_CACHED_DATA_TTL_SECONDS = 60


@st.cache_data(ttl=_CACHED_DATA_TTL_SECONDS)
def get_cached_data(endpoint:str) -> Any:
    """
    Retrieve cached data from the specified endpoint.
    Args:
        endpoint (str): The API endpoint to fetch data from.
    Returns:
        Any: The data retrieved from the specified endpoint.
    """

    return get_data(endpoint)

def _fetch_single_structured_scripture(
    scripture: str,
    bible_version: str,
    language: str,
    auth_headers: dict[str, str],
) -> tuple[str, dict[str, Any] | None, str | None]:
    """Haal één gestructureerde lezing op bij de agent-backend.

    Aparte helper zodat ThreadPoolExecutor per lezing één POST kan afvuren.
    Geeft een tuple terug (scripture, data, foutmelding) zodat de caller
    volgorde én fouten per lezing kan rapporteren zonder dat een fout in
    één lezing de andere parallelle calls afbreekt.

    auth_headers wordt door de hoofdthread vooraf gesnapshot via
    AgentRequest.auth_header(); zo voorkomen we dat een JwtHandler-refresh
    binnen een worker-thread parallel met andere workers race-condities
    geeft op het gedeelde token.
    """
    data: dict[str, str] = {
        "scripture_data": scripture,
        "bible_version": bible_version,
        "language": language,
    }
    try:
        response = requests.post(
            url=f"{os.environ.get('API_AGENT_URL').rstrip('/')}/structured_scripture/",
            json=data,
            headers=auth_headers,
            timeout=_STRUCTURED_SCRIPTURE_TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout:
        return scripture, None, f"Timeout na {_STRUCTURED_SCRIPTURE_TIMEOUT_SECONDS}s"
    except requests.exceptions.RequestException as exc:
        return scripture, None, str(exc)

    if response.status_code == 200:
        return scripture, response.json(), None
    return scripture, None, response.text


def get_structured_scriptures(scriptures: list[str], bible_version: str, language: str) -> list[dict[str, Any]]:
    """Fetch and structure scripture data from an API for given scripture references.

    Parallelle uitvoer: elke lezing wordt via een ThreadPoolExecutor
    tegelijk opgevraagd zodat de totale duur gelijk is aan de traagste
    lezing in plaats van de som. De volgorde van de resultaten komt
    overeen met de inputvolgorde, omdat `executor.map` de iteratie in
    volgorde oplevert — de UI toont lezingen dan in de juiste liturgische
    volgorde. Elke POST heeft een harde timeout (_STRUCTURED_SCRIPTURE_TIMEOUT_SECONDS)
    zodat een hangende backend-call de Streamlit-rerun niet onbeperkt blokkeert.

    Args:
        scriptures: Lezingsreferenties (bv. ["Mattheüs 5:1-10", "Psalm 23"]).
        bible_version: Bijbelvertaling-aanduiding voor de backend.
        language: Taalcode voor de teruggeleverde tekst.

    Returns:
        Lijst met gestructureerde lezingen (alleen succesvolle responses).
        Mislukte lezingen worden zichtbaar als foutmelding in de UI en
        overgeslagen in de output.
    """
    # Voortgangsregels in de omringende st.status-context — laten staan omdat
    # de caller in new_analysis.py hier zijn status uit opbouwt.
    st.write(scriptures)
    st.write(bible_version)

    structured_scripture_data: list[dict[str, Any]] = []

    if not scriptures:
        return structured_scripture_data

    # max_workers wordt begrensd op het aantal lezingen zodat we geen
    # lege threads aanmaken voor minder dan 4 lezingen.
    max_workers = min(_STRUCTURED_SCRIPTURE_MAX_WORKERS, len(scriptures))

    # Snapshot de Bearer-headers één keer in de hoofdthread. JwtHandler.token
    # is een @property die bij verlopen token een refresh kan triggeren; dat
    # mag niet vanuit meerdere worker-threads tegelijk gebeuren.
    auth_headers = AgentRequest().auth_header()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(
            lambda s: _fetch_single_structured_scripture(
                s, bible_version, language, auth_headers
            ),
            scriptures,
        )

        for scripture, data, error in results:
            if error is not None:
                st.write(f"Fout bij ophalen van '{scripture}': {error}")
                continue
            if data is not None:
                structured_scripture_data.append(data)

    return structured_scripture_data


def save_scriptures(scriptures: list[dict[str, Any]]) -> None:
    """
    Save a list of scripture dictionaries to a JSON file.
    This function creates a temporary directory if it doesn't exist and writes
    the provided scriptures data to a JSON file at 'temp/scriptures.json'.
    Args:
        scriptures: A list of dictionaries containing scripture data, where each
                   dictionary can have string keys and values of any type.
    Returns:
        None
    """
    
    os.makedirs("temp", exist_ok=True)
    
    with open("temp/scriptures.json", "w") as f:
        json.dump(scriptures, f)

@st.cache_data  
def load_scriptures() -> list[dict[str, Any]] | None:
    """
    Load scriptures data from a JSON file.
    Reads scripture data from a local JSON file located at 'temp/scriptures.json'
    and returns it as a list of dictionaries.
    Returns:
        list[dict[str, Any]] | None: A list of dictionaries containing scripture data,
            or None if the file cannot be read or parsed.
    Raises:
        FileNotFoundError: If the 'temp/scriptures.json' file does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
        IOError: If an error occurs while reading the file.
    """
    
    with open("temp/scriptures.json", "r") as f:
        return json.load(f)
    
    
def _sla_thema_voorkeur_op() -> None:
    """Sla de thema-voorkeur op via de backend zodat die over apparaten volgt."""
    # Lees de toggle-waarde en synchroniseer naar de voorkeur-key. De widget gebruikt
    # '_dark_mode_toggle' als key zodat 'dark_mode' zelf geen widget-key is; Streamlit
    # wist widget-keys bij paginanavigatie als het widget niet meer gerenderd wordt
    # (bijv. bij navigatie naar overview.py, waar render_sidebar() niet wordt aangeroepen).
    donker = bool(st.session_state.get('_dark_mode_toggle', False))
    st.session_state['dark_mode'] = donker
    # Persisteer naar de backend via /api/user-preferences/. Bij netwerkfouten of
    # wanneer de backend het endpoint nog niet heeft uitgerold laten we de wijziging
    # stilletjes alleen in session_state staan; de UI reageert dan wel, maar de
    # voorkeur gaat verloren bij volgende sessie. Dat is acceptabel omdat deze
    # backend-rollout gekoppeld is aan deze frontend-feature.
    handler = st.session_state.get('api_handler')
    if handler:
        try:
            handler.patch('api/user-preferences/', {'dark_mode': donker})
        except requests.exceptions.RequestException:
            pass


def render_sidebar():
    
    with st.sidebar:
        
        with st.expander("Kerkdienstanalyses"):
            st.page_link(label="Overzicht kerkdienstanalyses", page=f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py")
            # Verberg de "Nieuwe kerkdienstanalyse"-link zodra de early-test-
            # tokenlimiet overschreden is; de gebruiker kan dan geen nieuwe
            # analyse meer starten totdat een beheerder de limiet aanpast.
            if not tokenlimiet_bereikt():
                st.page_link(label="Nieuwe kerkdienstanalyse", page=f"{st.session_state['page_navigation_dir']}/analyses/new_analysis.py")
            
        with st.expander("Gemeenten"):
            st.page_link(label="Overzicht gemeenten", page=f"{st.session_state['page_navigation_dir']}/churches/churches_overview.py")
            st.page_link(label="Nieuwe gemeente", page=f"{st.session_state['page_navigation_dir']}/churches/new_church.py")
            
        with st.expander("Account"):
            st.page_link(label="Uitloggen", page=f"{st.session_state['page_navigation_dir']}/logout.py")
            st.page_link(label="Wachtwoord resetten", page=f"{st.session_state['page_navigation_dir']}/reset_password.py")
            # Gebruik '_dark_mode_toggle' als widget-key zodat de voorkeur-key 'dark_mode'
            # geen widget-key is. Streamlit wist widget-keys bij paginanavigatie wanneer
            # het widget niet meer gerenderd wordt (overview.py heeft geen render_sidebar()),
            # waardoor de donker-thema-instelling anders verloren ging bij het openen van
            # een analyse. value= initialiseert de toggle vanuit 'dark_mode' zodat de
            # zichtbare stand overeenkomt met de actieve voorkeur na een paginawissel.
            st.toggle(
                "Donker thema",
                key="_dark_mode_toggle",
                value=st.session_state.get('dark_mode', False),
                on_change=_sla_thema_voorkeur_op,
            )

        # Toon de suggesties-knop als de gebruiker ingelogd is (api_handler beschikbaar).
        if "api_handler" in st.session_state:
            # Lazy import om circular import met user_suggestions -> utils te vermijden.
            from src.components.user_suggestions import render_suggestions_trigger
            render_suggestions_trigger(st.session_state["api_handler"])


# Hoe lang één `haal_cumulatief_tokenverbruik_op()`-resultaat hergebruikt
# wordt in dezelfde Streamlit-sessie. Korte TTL (30 s) zodat de oranje
# melding en de verborgen "Nieuwe analyse"-knoppen snel reageren op een
# aanpassing in Django admin of een zojuist voltooide analyse, terwijl de
# sidebar niet bij elke pagina-render opnieuw een roundtrip maakt.
_TOKENVERBRUIK_CACHE_TTL_SECONDS = 30
_TOKENVERBRUIK_CACHE_KEY = "_tokenverbruik_cache"


def haal_cumulatief_tokenverbruik_op() -> tuple[int, int, float, int, int, float] | None:
    """Haalt cumulatief tokenverbruik + per-user tokenlimiet op bij de backend.

    Roept ``GET /api/token-usage/cumulative/`` aan (zie backend
    ``analysis_result.views.TokenUsageView``). Het endpoint levert in de
    cumulatieve variant een object terug met de vorm
    ``{"usage": {<model>: {"input_tokens": N, "output_tokens": N}, ...},
      "limits": {"max_input_tokens": N, "max_output_tokens": N,
                 "budget_eur": F}}``.

    De kosten worden op basis van ``st.secrets['model_prices']`` berekend
    (prijs per 1M tokens). De limieten worden door de backend uit
    ``UserPreferences`` gehaald zodat ze per gebruiker via Django admin
    overruled kunnen worden.

    Het resultaat wordt in ``st.session_state`` gecachet (TTL uit
    ``_TOKENVERBRUIK_CACHE_TTL_SECONDS``) zodat zowel het dashboard als de
    sidebar hem op dezelfde render kunnen aanroepen zonder dubbele
    roundtrips. We gebruiken geen ``@st.cache_data`` omdat de data per
    ingelogde gebruiker verschilt en Streamlit's cache globaal is.

    Returnt ``(total_input, total_output, total_cost, max_input_tokens,
    max_output_tokens, budget_eur)`` of ``None`` als de API-handler
    ontbreekt, het endpoint niet bereikbaar is, of het antwoord onverwacht
    gevormd is. ``None`` laat de aanroepende pagina stilletjes verdergaan
    zonder foutmelding.
    """
    nu = time.time()
    cached = st.session_state.get(_TOKENVERBRUIK_CACHE_KEY)
    if cached is not None:
        expires_at, value = cached
        if nu < expires_at:
            return value

    handler = st.session_state.get('api_handler')
    if not handler:
        return None
    try:
        payload = handler.get("api/token-usage/cumulative/")
    except requests.exceptions.HTTPError:
        # Endpoint niet bereikbaar in deze omgeving — laat de pagina
        # gewoon laden zonder waarschuwing.
        return None
    if not isinstance(payload, dict):
        return None

    # De backend retourneert `usage` en `limits` als aparte velden. Als een
    # oudere backend nog de platte dict-vorm terugstuurt, laten we de
    # waarschuwing achterwege — er is dan geen betrouwbare limiet beschikbaar.
    usage = payload.get("usage")
    limits = payload.get("limits")
    if not isinstance(usage, dict) or not isinstance(limits, dict):
        return None

    model_prices = st.secrets.get("model_prices", {})
    fallback_model = st.secrets.get("CURRENT_MODEL", "")
    total_input = 0
    total_output = 0
    total_cost = 0.0
    for model, counts in usage.items():
        inp = counts.get("input_tokens", 0) or 0
        out = counts.get("output_tokens", 0) or 0
        # Val terug op de prijzen van het huidige model als het gebruikte
        # model niet in de prijstabel voorkomt; ontbreken beide, dan is de
        # kosten-bijdrage 0 en zien we alleen token-aantallen.
        prices = model_prices.get(model) or model_prices.get(fallback_model, {})
        total_input += inp
        total_output += out
        total_cost += (inp / 1_000_000) * prices.get("input_eur", 0.0)
        total_cost += (out / 1_000_000) * prices.get("output_eur", 0.0)

    max_input = int(limits.get("max_input_tokens", 0) or 0)
    max_output = int(limits.get("max_output_tokens", 0) or 0)
    budget_eur = float(limits.get("budget_eur", 0) or 0)
    result = (total_input, total_output, total_cost, max_input, max_output, budget_eur)
    st.session_state[_TOKENVERBRUIK_CACHE_KEY] = (
        nu + _TOKENVERBRUIK_CACHE_TTL_SECONDS,
        result,
    )
    return result


def tokenlimiet_bereikt() -> bool:
    """Geeft terug of het cumulatieve verbruik de per-user limiet heeft overschreden.

    Hergebruikt de gecachete waarde van ``haal_cumulatief_tokenverbruik_op()``
    zodat een sidebar- én dashboard-aanroep binnen dezelfde render samen
    maximaal één roundtrip veroorzaken. Bij ontbrekende data (endpoint
    onbereikbaar, niet ingelogd) retourneert ``False`` — de default is
    "limiet niet bereikt" zodat de UI niet onterecht knoppen verbergt.
    """
    info = haal_cumulatief_tokenverbruik_op()
    if info is None:
        return False
    total_input, total_output, _cost, max_input, max_output, _budget = info
    return (total_input > max_input) or (total_output > max_output)


def render_analysis_results_sidebar(analysis_results: list[dict[str, Any]]) -> None:
    
    
    
    with st.sidebar:
        st.switch_page(f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py")
        
        st.page_link(label="Overzicht preekanalyses", page=f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py")
        st.page_link(label="Analyse overzicht", page=f"{st.session_state['page_navigation_dir']}/analysis_results/overview.py", query_params={"analysis_id": analysis_results[0]['id']})
