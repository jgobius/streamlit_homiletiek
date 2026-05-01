import json
import re
import time
from datetime import datetime

import requests
import streamlit as st

from src.utils.utils import (
    redirect_to_login,
    get_data,
    get_cached_data,
    tel_woorden,
    toon_analysenaam,
    valideer_tekstinvoer,
    tokenlimiet_bereikt,
    woord_meervoud,
    # Notificatie-helpers: registreer een net gestarte analyse en rendert
    # het polling-fragment dat een toast toont zodra het resultaat in de
    # database verschijnt (zie src/utils/utils.py).
    registreer_lopende_analyse,
    render_analyse_voortgang_poller,
    # Voor de Opnieuw-knop op Bijbelteksten — deze hergebruikt dezelfde
    # gestructureerde-scraper-flow als 'Aanpassen' om scripture_json te
    # verversen vóór /original_scriptures/ wordt getriggerd.
    get_structured_scriptures,
    EIGEN_PREEK_MIN_WOORDEN as _EIGEN_PREEK_MIN_WOORDEN,
    EIGEN_PREEK_MAX_WOORDEN as _EIGEN_PREEK_MAX_WOORDEN,
)
from page_navigation.analysis_results.aanpassen_dialog import aanpassen_dialog
from page_navigation.analysis_results.selectie_instellen_dialog import (
    selectie_instellen_dialog,
)
from page_navigation.analysis_results.analyses.postille import postille
from page_navigation.analysis_results.analyses.bijbelteksten import bijbelteksten
from page_navigation.analysis_results.analyses.liturgisch_jaar import liturgisch_jaar
from page_navigation.analysis_results.analyses.liedsuggesties import liedsuggesties
from page_navigation.analysis_results.analyses.structuralistische_exegese import (
    structuralistische_exegese,
)
from page_navigation.analysis_results.analyses.commentaren import commentaren
from page_navigation.analysis_results.analyses.theologie import theologie
# Sociaal-maatschappelijk is verplaatst van Basis naar Verdieping; de dispatch
# loopt nu via verdieping._RENDERERS, dus in overview.py is geen directe import
# meer nodig.
# Waardenoriëntatie is verplaatst naar de Verdieping-tab als Tavily-analyse
# (parallel aan politieke_orientatie en gemeente_spiritualiteit). De renderer
# wordt vanuit verdieping.py:_RENDERERS aangeroepen, niet meer hier.
from page_navigation.analysis_results.analyses.geloofsorientatie import (
    geloofsorientatie,
)
# Interpretatieve synthese is verplaatst naar de Verdieping-tab als Tavily-analyse
# (parallel aan politieke_orientatie, waardenorientatie en gemeente_spiritualiteit).
# De renderer wordt vanuit verdieping.py:_RENDERERS aangeroepen, niet meer hier.
from page_navigation.analysis_results.analyses.wereldnieuws import wereldnieuws
from page_navigation.analysis_results.analyses.lokaal_nieuws import lokaal_nieuws
from page_navigation.analysis_results.analyses.representatieve_hoorders import (
    representatieve_hoorders,
)
from page_navigation.analysis_results.analyses.illustraties import illustraties
# Focus-en-functie is verhuisd van Verdieping naar Preekschetsen-tab; de
# renderer wordt nu direct vanuit de Preekschetsen-dispatch aangeroepen.
from page_navigation.analysis_results.analyses.focus_en_functie import (
    focus_en_functie as render_focus_en_functie,
)
from page_navigation.analysis_results.analyses.contextduiding import contextduiding
from page_navigation.analysis_results.analyses.verdieping import verdieping
from page_navigation.analysis_results.analyses.preekschets import preekschets
from page_navigation.analysis_results.analyses.feedback_analyse import feedback_analyse
from page_navigation.analysis_results.analyses.volledige_preek import volledige_preek
from src.components.user_feedback import render_analysis_footer
from src.api.agent_request import AgentRequest
# Tab-categorisatie (welke analyse-naam hoort bij welk tabblad) staat centraal
# in src.utils.analyse_tabs zodat zowel deze pagina als de Word-export
# (src.utils.word_export) dezelfde bron van waarheid gebruiken. We importeren
# met de bestaande underscore-namen zodat de lokale referenties verderop in
# dit bestand niet mee hoeven te veranderen.
from src.utils.analyse_tabs import (
    TAB_VOLGORDE as _TABS,
    _BASIS_ORDER,
    _PERSPECTIEVEN_NAMEN,
    _VERDIEPING_NAMEN,
    _GEBEDEN_NAMEN,
    _PREEKSCHETSEN_NAMEN,
    _PREEKSCHETS_HULPSTUKKEN,
    _PREEKSCHETSEN_TAB,
    _FEEDBACK_NAMEN,
    _ALL_NON_BASIS,
    heeft_preekschets_resultaten,
)

# Paginascoped CSS: geef de "... toevoegen"-expanders in de zijbalk een
# subtiele oranje rand zodat ze opvallen tussen de grijze analyse-knoppen,
# maar veel minder prominent zijn dan de actieve analyse (die gebruikt
# rgba(255,128,0,0.12) + solid oranje rand + oranje tekst). Alleen de rand
# wordt oranje getint; de achtergrond blijft de standaardkleur van het
# thema, zodat de expander niet begint te concurreren met de geselecteerde
# analyse. De styling haakt aan op de `st-key-sidebar_toevoegen_<tab>`
# CSS-klasse die st.container(key=...) automatisch genereert, zodat alleen
# déze expanders de oranje rand krijgen en andere sidebar-expanders
# (Kerkdienstanalyses, Gemeenten, Account) onaangetast blijven. De
# selectors voor `details`, `> div` en `> div > div` dekken zowel het oude
# <details>/<summary>-patroon als het nieuwe div-gebaseerde patroon van
# Streamlit, en winnen qua specificiteit van de themaregels in main.py
# (die geen extra class-prefix hebben).
st.markdown(
    """
    <style>
    [class*="st-key-sidebar_toevoegen_"] [data-testid="stExpander"],
    [class*="st-key-sidebar_toevoegen_"] [data-testid="stExpander"] details,
    [class*="st-key-sidebar_toevoegen_"] [data-testid="stExpander"] > div,
    [class*="st-key-sidebar_toevoegen_"] [data-testid="stExpander"] > div > div {
        border-color: rgba(255, 128, 0, 0.45) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Categorisatie van analyse-types per tabblad ---
REANALYSIS_LOCK_TIMEOUT_SECONDS = 30

# Woordentelling-grenzen voor het 'Eigen preek'-dialoog worden geïmporteerd
# uit src.utils.utils zodat deze dialog en de bewerk-view in
# analyses/volledige_preek.py dezelfde waarden delen (DRY). Korte alias-import
# hierboven houdt lokale referenties ongewijzigd.

# Korte titelvelden in het 'Eigen preek'-dialoog: beperkte woordruimte zodat
# een titel/ondertitel een titel blijft en niet ontaardt in vrije tekst of
# geplakte analyses.
_EIGEN_PREEK_MAX_WOORDEN_TITEL = 30

# Tab-categorisatie (_PERSPECTIEVEN_NAMEN, _VERDIEPING_NAMEN, _GEBEDEN_NAMEN,
# _PREEKSCHETSEN_NAMEN, _FEEDBACK_NAMEN, _PREEKSCHETS_HULPSTUKKEN,
# _PREEKSCHETSEN_TAB, _ALL_NON_BASIS, _TABS/TAB_VOLGORDE, _BASIS_ORDER) wordt
# bovenaan geïmporteerd uit src.utils.analyse_tabs — zie die module voor
# inhoudelijke toelichting (waarom bepaalde analyses van Basis naar Verdieping
# zijn verhuisd, etc.). Gedupliceerde inline-definities zijn bewust
# verwijderd zodat er één bron van waarheid is voor deze groepering.


def _basis_sort_key(name: str) -> int:
    # Postille krijgt altijd een hoog getal zodat het gegarandeerd onderaan staat,
    # ook als er onbekende analysetypes uit de API komen.
    if name == "postille":
        return 9999
    try:
        return _BASIS_ORDER.index(name)
    except ValueError:
        # Onbekend type: achteraan, maar vóór postille
        return len(_BASIS_ORDER)


def _deps_ok(at: dict, latest: dict) -> tuple[bool, list[str]]:
    """Geeft (True, []) als alle vereiste analyses aanwezig zijn, anders (False, [display namen])."""
    deps = at.get("depends_on") or []
    ontbrekend = []
    for dep in deps:
        dep_name = dep.get("name") if isinstance(dep, dict) else dep
        dep_label = dep.get("front_end_name") if isinstance(dep, dict) else dep_name
        if dep_name and dep_name not in latest:
            # Pas de weergavenaam-override defensief toe; bij sommige API-payloads
            # ontbreekt `front_end_name` op de dep en valt het label terug op de
            # snake_case `name` ('volledige_preek'). `toon_analysenaam` mapt die
            # alsnog naar de gewenste UI-naam.
            ontbrekend.append(toon_analysenaam(dep_label or dep_name))
    return (len(ontbrekend) == 0, ontbrekend)


def _reanalysis_is_locked(lock_key: str) -> bool:
    lock_time = st.session_state.get(lock_key)
    if lock_time is None:
        return False
    if time.time() - lock_time > REANALYSIS_LOCK_TIMEOUT_SECONDS:
        del st.session_state[lock_key]
        return False
    return True


def _release_reanalysis_lock(lock_key: str) -> None:
    st.session_state.pop(lock_key, None)


def _deps_ok(at: dict, latest: dict) -> tuple[bool, list[str]]:
    """Geeft (True, []) als alle vereiste analyses aanwezig zijn, anders (False, [display namen])."""
    deps = at.get("depends_on") or []
    missing = []
    for dep in deps:
        dep_name = dep.get("name") if isinstance(dep, dict) else dep
        dep_label = dep.get("front_end_name") if isinstance(dep, dict) else dep_name
        if dep_name and dep_name not in latest:
            # Pas de weergavenaam-override defensief toe; bij sommige API-payloads
            # ontbreekt `front_end_name` op de dep en valt het label terug op de
            # snake_case `name` ('volledige_preek'). `toon_analysenaam` mapt die
            # alsnog naar de gewenste UI-naam.
            missing.append(toon_analysenaam(dep_label or dep_name))
    return (len(missing) == 0, missing)


def _trigger_bijbelteksten_refresh(analysis_id: int, at: dict, lock_key: str) -> None:
    """Re-run de bijbelteksten-renderer mét frisse scripture_json.

    Bijbelteksten is geen LLM-analyse maar een mechanische verzen-match
    (zie homiletiek_agent/src/original_scriptures/tools.py): het leest de
    eerder gegenereerde scripture_json en koppelt verzen tegen de DB.
    Routeren via /single_analysis/ is daarom dubbel fout — dat endpoint
    laadt de Dummy-AgentInstruction die aan AnalysisType 'bijbelteksten'
    hangt en stuurt 'dummy text' als prompt naar het LLM, wat onzin
    oplevert. Bovendien zou het de gehallucineerde scripture_json laten
    staan, dus zelfs een correct routered single_analysis-call zou de
    oude fout hergebruiken.

    Deze helper repliceert de relevante stappen uit de 'Aanpassen'-dialog
    (page_navigation/analysis_results/selectie_instellen_dialog.py:419-545)
    voor het geval waarin niets aan de lezingen wijzigt:

    1) Voor `use_calendar=False` halen we de huidige
       `original_scripture`-strings uit scripture_json en draaien voor
       elk daarvan de `structured_scripture/`-pijplijn opnieuw. Sinds de
       deterministische NBV21/HSV-scraper (homiletiek_agent feature
       branch) levert dat voor die vertalingen schone tekst zonder
       hallucinaties; voor andere vertalingen blijft het oude Tavily-pad.
    2) Patch het nieuwe scripture_json terug op de SermonAnalysis.
    3) Trigger /original_scriptures/ zodat de bijbelteksten-AnalysisResult
       opnieuw geschreven wordt op basis van de verse scripture_json.

    Voor `use_calendar=True` slaan we stap 1+2 over: scripture_json wordt
    in dat geval niet gebruikt (de agent leest dan uit `liturgy`), dus
    enkel /original_scriptures/ triggeren is voldoende.
    """
    st.session_state[lock_key] = time.time()

    handler = st.session_state.get("api_handler")
    if handler is None:
        _release_reanalysis_lock(lock_key)
        st.error("API-verbinding niet beschikbaar; log opnieuw in.")
        return

    try:
        sermon_analysis = handler.get(f"api/sermon-analyses/{analysis_id}/") or {}
    except requests.exceptions.RequestException as exc:
        _release_reanalysis_lock(lock_key)
        st.error(f"Kon de analyse-gegevens niet ophalen: {exc}")
        return

    use_calendar = bool(sermon_analysis.get("use_calendar"))

    # Stap 1+2: alleen bij eigen lezingen. Bij kalender-lezingen laat
    # de agent de inhoud uit `liturgy` lopen; scripture_json mag dan leeg
    # of verouderd blijven.
    if not use_calendar:
        # Tokenlimiet-check: get_structured_scriptures() doet één
        # agent-call per lezing (Tavily + LLM-parse, eventueel met
        # deterministische scraper als voorhoede). Dit is dezelfde
        # check als in selectie_instellen_dialog.py vlak vóór de
        # vergelijkbare aanroep.
        if tokenlimiet_bereikt():
            _release_reanalysis_lock(lock_key)
            st.error(
                "Je tokenlimiet is bereikt. Het herladen van bijbelteksten "
                "vereist een AI-aanroep en is daarom geblokkeerd."
            )
            return

        scripture_json = sermon_analysis.get("scripture_json") or []
        scripture_refs: list[str] = [
            (entry.get("original_scripture") or "").strip()
            for entry in scripture_json
            if isinstance(entry, dict) and (entry.get("original_scripture") or "").strip()
        ]
        if not scripture_refs:
            # Geen lezingen om te verversen — niets te doen, gewoon
            # door naar /original_scriptures/ zodat de bestaande
            # scripture_json (mogelijk leeg) opnieuw verwerkt wordt.
            pass
        else:
            bible_version_obj = sermon_analysis.get("bible_version") or {}
            bible_version_str = (
                bible_version_obj.get("version")
                if isinstance(bible_version_obj, dict)
                else None
            )

            with st.status("Bijbelteksten opnieuw structureren (kan even duren)..."):
                try:
                    nieuwe_scripture_json = get_structured_scriptures(
                        scriptures=scripture_refs,
                        bible_version=bible_version_str,
                        language="nl",
                    )
                except Exception as exc:
                    _release_reanalysis_lock(lock_key)
                    st.error(f"Lezingen structureren mislukte: {exc}")
                    return

            # Lege output blokkeren — anders zou de Bijbelteksten-tab
            # daarna stilletjes leeg blijven. Zelfde defensie als in
            # selectie_instellen_dialog.py:456.
            lege = [
                entry.get("original_scripture") or "(onbekende lezing)"
                for entry in nieuwe_scripture_json
                if not any(
                    (s.get("verses") or [])
                    for s in (entry.get("scriptures") or [])
                )
            ]
            if lege:
                _release_reanalysis_lock(lock_key)
                st.error(
                    "Geen bijbeltekst gevonden voor: "
                    + ", ".join(f"'{t}'" for t in lege)
                    + ". Probeer het later nog eens."
                )
                return

            try:
                handler.patch(
                    f"api/sermon-analyses/{analysis_id}/",
                    data={"scripture_json": nieuwe_scripture_json},
                )
            except requests.exceptions.HTTPError as exc:
                _release_reanalysis_lock(lock_key)
                st.error(f"Opslaan van scripture_json mislukt: {exc}")
                return

    # Stap 3: trigger /original_scriptures/ — de mechanische verse-match
    # die als AnalysisResult van type 'bijbelteksten' weggeschreven wordt.
    try:
        agent_request.post(
            endpoint="original_scriptures/",
            payload={"sermon_analysis_id": analysis_id},
            timeout=120,
        )
        st.session_state["analysis_data_dirty"] = True
        registreer_lopende_analyse(analysis_id, at["name"], at["front_end_name"])
        st.toast(
            f"'{at['front_end_name']}' wordt opnieuw opgehaald. "
            "Ververs de pagina over enkele seconden."
        )
    except requests.exceptions.HTTPError as exc:
        _release_reanalysis_lock(lock_key)
        st.error(f"Fout bij het triggeren van bijbelteksten: {exc}")
    except Exception as exc:
        _release_reanalysis_lock(lock_key)
        st.error(f"Fout: {exc}")


def _trigger_analysis(analysis_id: int, at: dict, lock_key: str) -> None:
    """Stuur een verzoek naar de agent om een analyse uit te voeren."""
    # Bijbelteksten is geen LLM-analyse: routeer naar de speciale helper
    # die scripture_json ververst en /original_scriptures/ aanroept i.p.v.
    # /single_analysis/. Zie _trigger_bijbelteksten_refresh voor de reden.
    if at.get("name") == "bijbelteksten":
        _trigger_bijbelteksten_refresh(analysis_id, at, lock_key)
        return

    st.session_state[lock_key] = time.time()
    try:
        # AgentRequest.post injecteert de Bearer-header en voert raise_for_status
        # zelf uit; de daaropvolgende .raise_for_status() is voor backwards-
        # compatibiliteit met de oude inline-implementatie en een no-op zodra
        # de wrapper al heeft geslaagd.
        # Timeout op 120s: het endpoint is fire-and-forget en hoort snel te
        # antwoorden, maar de single-worker FastAPI-agent kan zijn event loop
        # tijdelijk bezet hebben door een lopende analyse met synchrone I/O.
        # 30s bleek daarbij in de praktijk te kort; 120s geeft genoeg marge.
        response = agent_request.post(
            endpoint="single_analysis/",
            payload={
                "sermon_analysis_id": analysis_id,
                "analysis_type_id": at["id"],
            },
            timeout=120,
        )
        response.raise_for_status()
        # Invalideer de sessiecache zodat een volgende rerun (bv. tab-klik)
        # de nieuwe analyse ophaalt zodra de agent klaar is, zonder dat de
        # gebruiker hoeft te hard-refreshen.
        st.session_state["analysis_data_dirty"] = True
        # Registreer de net gestarte analyse zodat de poller een tweede toast
        # toont ('... is klaar. Ververs het menu.') zodra het resultaat in de
        # DB verschijnt. Doen we direct na de succesvolle POST, zodat we
        # zeker weten dat de agent bezig is.
        registreer_lopende_analyse(analysis_id, at["name"], at["front_end_name"])
        st.toast(
            f"'{at['front_end_name']}' wordt uitgevoerd. Ververs de pagina over enkele minuten."
        )
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 409:
            st.warning(e.response.json().get("detail", "Al gestart, wacht even."))
            # Bij 409 ('al gestart') is er sowieso een lopende analyse —
            # registreer ook dan zodat de gebruiker alsnog een voltooi-toast
            # krijgt. Idempotent: dezelfde sleutel overschrijft een eventuele
            # eerdere entry zonder dubbele toasts te genereren.
            registreer_lopende_analyse(
                analysis_id, at["name"], at["front_end_name"]
            )
        else:
            _release_reanalysis_lock(lock_key)
            st.error(f"Fout: {e}")
    except Exception as e:
        _release_reanalysis_lock(lock_key)
        st.error(f"Fout: {e}")


def _trigger_preekschets(analysis_id: int, at: dict, lock_key: str) -> None:
    """Stuur een verzoek naar de agent om een preekschets uit te voeren (met opgeslagen selectie)."""
    st.session_state[lock_key] = time.time()
    try:
        selectie = st.session_state.get(f"preek_selectie_{analysis_id}", {})
        kernteksten = selectie.get("kernteksten", [])
        focus_optie = selectie.get("focus_optie")
        selected_perspectieven = selectie.get("perspectieven", {})
        selected_illustraties = selectie.get("illustraties", [])
        selected_hoorders = selectie.get("hoorders", [])
        # Fallback naar lege dict als de dialoog nog niet is opgeslagen — de
        # backend verwacht een dict-vorm en defaultt intern naar alles-uit.
        selected_exegese_commentaar = selectie.get("exegese_commentaar", {}) or {}
        # AgentRequest zorgt voor de Bearer-header; raw requests.post() zou
        # de agent (na verify_jwt) een 401 opleveren.
        # Timeout op 120s: zie toelichting in _trigger_analysis — preekschets-
        # kickoffs liepen met de default 30s soms over bij een drukke agent.
        response = agent_request.post(
            endpoint="run_single_analysis/",
            payload={
                "sermon_analysis_id": int(analysis_id),
                "analysis_type_name": at["name"],
                "core_text": kernteksten,
                "focus_optie": focus_optie,
                "selected_perspectieven": selected_perspectieven,
                "selected_illustraties": selected_illustraties,
                "selected_hoorders": selected_hoorders,
                "selected_exegese_commentaar": selected_exegese_commentaar,
            },
            timeout=120,
        )
        response.raise_for_status()
        # Invalideer de sessiecache zodat een volgende rerun (bv. tab-klik)
        # de nieuwe preekschets ophaalt zodra de agent klaar is, zonder dat
        # de gebruiker hoeft te hard-refreshen.
        st.session_state["analysis_data_dirty"] = True
        # Registreer de gestarte preekschets-run zodat de poller een
        # voltooi-toast toont zodra het resultaat in de DB verschijnt
        # (zelfde patroon als _trigger_analysis hierboven).
        registreer_lopende_analyse(
            int(analysis_id), at["name"], at["front_end_name"]
        )
        st.toast(
            f"'{at['front_end_name']}' wordt uitgevoerd. Ververs de pagina over enkele minuten."
        )
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 409:
            st.warning(e.response.json().get("detail", "Al gestart, wacht even."))
            # Bij 409 ('al gestart') ook registreren — er loopt sowieso een
            # analyse waarvan we de voltooiing willen melden.
            registreer_lopende_analyse(
                int(analysis_id), at["name"], at["front_end_name"]
            )
        else:
            _release_reanalysis_lock(lock_key)
            st.error(f"Fout: {e}")
    except Exception as e:
        _release_reanalysis_lock(lock_key)
        st.error(f"Fout: {e}")


def _render_preekschets_result(selected_preek: dict, latest: dict) -> None:
    """Dispatch op basis van aanwezigheid preek_onderdelen in result."""
    result = selected_preek.get("result", {})
    if isinstance(result, dict) and result.get("preek_onderdelen"):
        # Type-naam meegeven zodat preekschets() de juiste renderer kiest
        # (bv. Lowry/Buttrick hebben eigen schema, geen preek_onderdelen).
        preekschets(
            selected_preek,
            analysis_type_name=selected_preek["analysis_type"]["name"],
        )
    else:
        postille(selected_preek, latest_results=latest)


redirect_to_login()

agent_request = AgentRequest()

# Haal analysis_id op uit query-params of session_state.
# Converteer naar int zodat de string "None" (bijv. bij een foute navigatie) niet
# per ongeluk de guard hieronder passeert — "None" is truthy als string.
_raw_id = st.query_params.get("analysis_id") or st.session_state.get(
    "current_analysis_id"
)
try:
    analysis_id = int(_raw_id)
except (TypeError, ValueError):
    analysis_id = None

# Initialiseer het actieve tabblad vroeg zodat de zijbalk dit kan gebruiken vóór het gecachte blok.
if "current_tab" not in st.session_state:
    st.session_state["current_tab"] = "Basis"
current_tab = st.session_state.get("current_tab", "Basis")

with st.sidebar:
    st.page_link(
        label="< Terug",
        page=f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py",
    )

if not analysis_id:
    st.warning(
        "Geen analyse geselecteerd. Ga terug naar het overzicht en selecteer een analyse."
    )
    st.stop()

st.session_state["current_analysis_id"] = analysis_id

# Polling-fragment: rendert geen zichtbare UI, maar her-runt elke 15s en
# toont een toast zodra een gestarte analyse klaar is in de database. We
# plaatsen het in de sidebar omdat die DOM-positie stabiel blijft tussen
# tab-wissels in de hoofdcontent — een fragment direct in de hoofdcontent
# verloor na een tab-klik soms zijn run_every-cyclus.
with st.sidebar:
    render_analyse_voortgang_poller()

_data_cache_key = f"overview_data_{analysis_id}"
_cached_entry = st.session_state.get(_data_cache_key)
# Behandel een lege analysis_results-cache als niet-gecached. Zo wordt de
# Bijbelteksten-stap (die in de achtergrond via /original_scriptures/ draait)
# automatisch zichtbaar zodra de volgende rerun plaatsvindt (een tab-klik,
# een button, enz.), zonder dat de gebruiker hard hoeft te refreshen.
# Zodra er resultaten zijn blijft de cache sticky.
def _normaliseer_front_end_namen(items: list) -> None:
    """Strip implementatiemarkeringen (bv. ' (Tavily)') uit weergavenamen.

    We muteren de API-response in-place direct na het ophalen zodat álle
    downstream renderers (sidebar-knoppen, paginatitel, bevestigingsdialogen,
    toast-berichten) automatisch de opgeschoonde naam gebruiken. Zonder
    deze centralisatie zou elk displaypunt apart een wrapper-call nodig
    hebben — dat is foutgevoelig en divergeert snel. De `name`-sleutel
    blijft onaangetast; alleen de user-facing `front_end_name` wordt
    aangepast. `toon_analysenaam` is idempotent dus meermaals toepassen
    is veilig (bv. bij herbenutting van de sessiecache).
    """
    for it in items or []:
        at = it.get("analysis_type") if isinstance(it, dict) and "analysis_type" in it else it
        if isinstance(at, dict) and at.get("front_end_name"):
            at["front_end_name"] = toon_analysenaam(at["front_end_name"])
        if isinstance(at, dict):
            for dep in at.get("depends_on") or []:
                if isinstance(dep, dict) and dep.get("front_end_name"):
                    dep["front_end_name"] = toon_analysenaam(dep["front_end_name"])


if (
    st.session_state.pop("analysis_data_dirty", False)
    or _cached_entry is None
    or not _cached_entry.get("analysis_results")
):
    try:
        _fresh_results = get_data(
            f"api/analysis-results?sermon_analysis_id={analysis_id}"
        )
        # Normaliseer weergavenamen meteen na het ophalen, vóór caching,
        # zodat elke latere lezer de opgeschoonde versie ziet.
        _normaliseer_front_end_namen(_fresh_results)
        st.session_state[_data_cache_key] = {
            "analysis_results": _fresh_results,
            "sermon_analysis": get_data(f"api/sermon-analyses/{analysis_id}/"),
        }
    except requests.exceptions.HTTPError as e:
        # Verouderde analysis_id in sessie (bijv. na wisselen van omgeving): stuur terug naar dashboard.
        if e.response is not None and e.response.status_code == 404:
            st.session_state.pop("current_analysis_id", None)
            st.switch_page(
                f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py"
            )
            st.stop()
        raise
_cached_data = st.session_state[_data_cache_key]
analysis_results = _cached_data["analysis_results"]
sermon_analysis = _cached_data["sermon_analysis"]

if sermon_analysis:
    st.session_state["extra_context"] = sermon_analysis.get("extra_context", "")
    church = sermon_analysis.get("church", {})
    st.session_state["church_place"] = (
        church.get("place", "") if isinstance(church, dict) else ""
    )
    st.session_state["church_name"] = (
        church.get("name", "") if isinstance(church, dict) else ""
    )
    # Hydrateer de preekschets-selectie uit het SermonAnalysis-record zodat
    # de voorganger na uitloggen/inloggen (of vanaf een andere browser) zijn
    # eerdere keuze terugvindt. We overschrijven session_state alléén als er
    # nog geen selectie in het geheugen staat; anders zou een net-opgeslagen
    # selectie tijdens dezelfde sessie weer weggegooid kunnen worden door een
    # oudere server-snapshot uit de cache.
    _selectie_key = f"preek_selectie_{analysis_id}"
    if _selectie_key not in st.session_state:
        _opgeslagen = sermon_analysis.get("preekschets_selectie") or {}
        if _opgeslagen:
            st.session_state[_selectie_key] = _opgeslagen

# Houd per analysis_type alleen de nieuwste (hoogste id).
latest: dict[str, dict] = {}
for r in analysis_results:
    name = r["analysis_type"]["name"]
    if name not in latest or r["id"] > latest[name]["id"]:
        latest[name] = r

summary = list(latest.values())

# Herbereken _ALL_NON_BASIS hier binnen de body zodat het overeenkomt met de
# module-scope definitie hierboven (beide moeten synchroon blijven — dubbele
# definitie is legacy, maar aanpassen hier bewaart de oorspronkelijke structuur).
_ALL_NON_BASIS = (
    _PERSPECTIEVEN_NAMEN
    | _VERDIEPING_NAMEN
    | _PREEKSCHETSEN_TAB
    | _GEBEDEN_NAMEN
    | _FEEDBACK_NAMEN
)

analyse_summary = sorted(
    [r for r in summary if r["analysis_type"]["name"] not in _ALL_NON_BASIS],
    key=lambda r: _basis_sort_key(r["analysis_type"]["name"]),
)
# Verdieping t/m Feedback: volgorde via het `order`-veld uit de API (vastgelegd in de init-scripts).
# Basis gebruikt een handmatige _BASIS_ORDER omdat de gewenste volgorde daar afwijkt van de API-order.
_order_key = lambda r: r["analysis_type"].get("order", 99)
verdiep_summary = sorted(
    [r for r in summary if r["analysis_type"]["name"] in _VERDIEPING_NAMEN],
    key=_order_key,
)
perspect_summary = sorted(
    [r for r in summary if r["analysis_type"]["name"] in _PERSPECTIEVEN_NAMEN],
    key=_order_key,
)
# Preekschets-tab gebruikt de uitgebreide set (incl. focus_en_functie en
# illustraties); de selectie-lock onderscheid tussen echte schetsen en
# hulpstukken gebeurt pas in de sidebar-render.
preek_summary = sorted(
    [r for r in summary if r["analysis_type"]["name"] in _PREEKSCHETSEN_TAB],
    key=_order_key,
)
gebed_summary = sorted(
    [r for r in summary if r["analysis_type"]["name"] in _GEBEDEN_NAMEN],
    key=_order_key,
)
feedback_summary = sorted(
    [r for r in summary if r["analysis_type"]["name"] in _FEEDBACK_NAMEN],
    key=_order_key,
)

if "all_analysis_types_cache" not in st.session_state:
    _fresh_types = get_data("api/analysis-types/")
    # Normaliseer weergavenamen ook voor het "toevoegen"-menu en afhankelijkheidslabels,
    # zodat zowel bestaande als nog te maken analyses dezelfde opgeschoonde naam tonen.
    _normaliseer_front_end_namen(_fresh_types)
    st.session_state["all_analysis_types_cache"] = _fresh_types
all_analysis_types = st.session_state["all_analysis_types_cache"]
missing_types = sorted(
    [
        at
        for at in all_analysis_types
        if at.get("front_end_name") and at["name"] not in latest
    ],
    key=lambda x: x.get("order", 99),
)
analyse_missing = sorted(
    [at for at in missing_types if at["name"] not in _ALL_NON_BASIS],
    key=lambda at: _basis_sort_key(at["name"]),
)
verdiep_missing = [at for at in missing_types if at["name"] in _VERDIEPING_NAMEN]
perspect_missing = [at for at in missing_types if at["name"] in _PERSPECTIEVEN_NAMEN]
# preek_missing gebruikt de uitgebreide tab-set zodat ook focus_en_functie en
# illustraties via de 'Preekonderdeel toevoegen'-expander aangeboden worden.
preek_missing = [at for at in missing_types if at["name"] in _PREEKSCHETSEN_TAB]
gebed_missing = [at for at in missing_types if at["name"] in _GEBEDEN_NAMEN]
feedback_missing = [at for at in missing_types if at["name"] in _FEEDBACK_NAMEN]

# feedback_nav_* excludeert volledige_preek — die wordt apart via een dialoog beheerd
feedback_nav_summary = [
    r for r in feedback_summary if r["analysis_type"]["name"] != "volledige_preek"
]
feedback_nav_missing = [
    at for at in feedback_missing if at["name"] != "volledige_preek"
]

# Validate selected IDs for each tab
if "selected_analysis_id" not in st.session_state or st.session_state[
    "selected_analysis_id"
] not in {r["id"] for r in analyse_summary}:
    st.session_state["selected_analysis_id"] = (
        analyse_summary[0]["id"] if analyse_summary else None
    )

if "selected_verdiep_id" not in st.session_state or st.session_state[
    "selected_verdiep_id"
] not in {r["id"] for r in verdiep_summary}:
    st.session_state["selected_verdiep_id"] = (
        verdiep_summary[0]["id"] if verdiep_summary else None
    )

if "selected_perspect_id" not in st.session_state or st.session_state[
    "selected_perspect_id"
] not in {r["id"] for r in perspect_summary}:
    st.session_state["selected_perspect_id"] = (
        perspect_summary[0]["id"] if perspect_summary else None
    )

if "selected_preek_id" not in st.session_state or st.session_state[
    "selected_preek_id"
] not in {r["id"] for r in preek_summary}:
    st.session_state["selected_preek_id"] = (
        preek_summary[0]["id"] if preek_summary else None
    )

if "selected_gebed_id" not in st.session_state or st.session_state[
    "selected_gebed_id"
] not in {r["id"] for r in gebed_summary}:
    st.session_state["selected_gebed_id"] = (
        gebed_summary[0]["id"] if gebed_summary else None
    )

if "selected_feedback_id" not in st.session_state or st.session_state[
    "selected_feedback_id"
] not in {r["id"] for r in feedback_nav_summary}:
    st.session_state["selected_feedback_id"] = (
        feedback_nav_summary[0]["id"] if feedback_nav_summary else None
    )

# --- Sidebar block 2: tab-conditional analysis buttons ---
# Zodra de early-test-tokenlimiet overschreden is, verbergen we alle
# "… toevoegen"-expanders zodat er geen nieuwe LLM-calls meer getriggerd
# kunnen worden. Navigatie naar bestaande resultaten blijft gewoon werken.
_limiet_overschreden = tokenlimiet_bereikt()
with st.sidebar:
    if current_tab == "Basis":
        for r in analyse_summary:
            label = r["analysis_type"]["front_end_name"]
            is_selected = r["id"] == st.session_state["selected_analysis_id"]
            btn_type = "primary" if is_selected else "secondary"
            if st.button(
                label, key=f"nav_{r['id']}", use_container_width=True, type=btn_type
            ):
                st.session_state["selected_analysis_id"] = r["id"]
                st.session_state["current_tab"] = current_tab
                st.rerun()

        if analyse_missing and not _limiet_overschreden:
            # Wikkel de expander in een st.container met een unieke key zodat
            # de paginascoped CSS bovenaan dit bestand hem via de automatisch
            # gegenereerde `st-key-sidebar_toevoegen_basis`-klasse subtiel
            # oranje kan kleuren. Bij overschreden tokenlimiet verbergen we
            # de hele expander (zie ook de andere vijf tabs verderop).
            with st.container(key="sidebar_toevoegen_basis"), st.expander("Analyse toevoegen"):
                for at in analyse_missing:
                    _add_lock_key = f"analysis_add_lock_{analysis_id}_{at['name']}"
                    _add_locked = _reanalysis_is_locked(_add_lock_key)
                    _ok, _ontbr = _deps_ok(at, latest)
                    _label = (
                        f"🔒 {at['front_end_name']}"
                        if not _ok
                        else at["front_end_name"]
                    )
                    _help = ("Vereist eerst: " + ", ".join(_ontbr)) if not _ok else None
                    if st.button(
                        _label,
                        key=f"add_{at['name']}",
                        use_container_width=True,
                        disabled=_add_locked or not _ok,
                        help=_help,
                    ):
                        _trigger_analysis(int(analysis_id), at, _add_lock_key)

    elif current_tab == "Verdieping":
        for r in verdiep_summary:
            label = r["analysis_type"]["front_end_name"]
            is_selected = r["id"] == st.session_state["selected_verdiep_id"]
            btn_type = "primary" if is_selected else "secondary"
            if st.button(
                label, key=f"vnav_{r['id']}", use_container_width=True, type=btn_type
            ):
                st.session_state["selected_verdiep_id"] = r["id"]
                st.session_state["current_tab"] = current_tab
                st.rerun()

        # Verberg de expander zodra alle verdiepingsanalyses aanwezig zijn:
        # er valt dan niets meer toe te voegen. Zodra de gebruiker er één
        # verwijdert, komt het type weer in `verdiep_missing` en verschijnt
        # de expander automatisch terug. Container-key zorgt dat de
        # paginascoped CSS deze expander subtiel oranje kleurt. Bij
        # overschreden tokenlimiet verbergen we de expander in zijn geheel.
        if verdiep_missing and not _limiet_overschreden:
            with st.container(key="sidebar_toevoegen_verdieping"), st.expander("Verdieping toevoegen"):
                for at in verdiep_missing:
                    _add_lock_key = f"analysis_add_lock_{analysis_id}_{at['name']}"
                    _add_locked = _reanalysis_is_locked(_add_lock_key)
                    _ok, _ontbr = _deps_ok(at, latest)
                    _label = (
                        f"🔒 {at['front_end_name']}" if not _ok else at["front_end_name"]
                    )
                    _help = ("Vereist eerst: " + ", ".join(_ontbr)) if not _ok else None
                    if st.button(
                        _label,
                        key=f"vadd_{at['name']}",
                        use_container_width=True,
                        disabled=_add_locked or not _ok,
                        help=_help,
                    ):
                        _trigger_analysis(int(analysis_id), at, _add_lock_key)

    elif current_tab == "Perspectieven":
        for r in perspect_summary:
            label = r["analysis_type"]["front_end_name"]
            is_selected = r["id"] == st.session_state["selected_perspect_id"]
            btn_type = "primary" if is_selected else "secondary"
            if st.button(
                label, key=f"pnav_{r['id']}", use_container_width=True, type=btn_type
            ):
                st.session_state["selected_perspect_id"] = r["id"]
                st.session_state["current_tab"] = current_tab
                st.rerun()

        # Verberg de expander zodra alle perspectieven aanwezig zijn: er valt
        # dan niets meer toe te voegen. Zodra de gebruiker er één verwijdert,
        # komt het type weer in `perspect_missing` en verschijnt de expander
        # automatisch terug. Container-key zorgt dat de paginascoped CSS deze
        # expander subtiel oranje kleurt. Bij overschreden tokenlimiet
        # verbergen we de expander in zijn geheel.
        if perspect_missing and not _limiet_overschreden:
            with st.container(key="sidebar_toevoegen_perspectieven"), st.expander("Perspectief toevoegen"):
                for at in perspect_missing:
                    _add_lock_key = f"analysis_add_lock_{analysis_id}_{at['name']}"
                    _add_locked = _reanalysis_is_locked(_add_lock_key)
                    _ok, _ontbr = _deps_ok(at, latest)
                    _label = (
                        f"🔒 {at['front_end_name']}" if not _ok else at["front_end_name"]
                    )
                    _help = ("Vereist eerst: " + ", ".join(_ontbr)) if not _ok else None
                    if st.button(
                        _label,
                        key=f"padd_{at['name']}",
                        use_container_width=True,
                        disabled=_add_locked or not _ok,
                        help=_help,
                    ):
                        _trigger_analysis(int(analysis_id), at, _add_lock_key)

    elif current_tab == "Preekschetsen":
        for r in preek_summary:
            label = r["analysis_type"]["front_end_name"]
            is_selected = r["id"] == st.session_state["selected_preek_id"]
            btn_type = "primary" if is_selected else "secondary"
            if st.button(
                label, key=f"pknav_{r['id']}", use_container_width=True, type=btn_type
            ):
                st.session_state["selected_preek_id"] = r["id"]
                st.session_state["current_tab"] = current_tab
                st.rerun()

        # Verberg de expander zodra alle preekschets-types aanwezig zijn:
        # er valt dan niets meer toe te voegen. Zodra de gebruiker er één
        # verwijdert, komt het type weer in `preek_missing` en verschijnt
        # de expander automatisch terug. Container-key zorgt dat de
        # paginascoped CSS deze expander subtiel oranje kleurt. Bij
        # overschreden tokenlimiet verbergen we de expander in zijn geheel.
        if preek_missing and not _limiet_overschreden:
            # Label "Preekonderdeel toevoegen" i.p.v. "Preekschets toevoegen":
            # de expander biedt naast preekschetsen ook hulpstukken (focus &
            # functie, homiletische illustraties) aan, die geen preekschets
            # in strikte zin zijn. "Preekonderdeel" is dekkender voor de hele
            # set zonder de afzonderlijke types onnodig op te splitsen.
            with st.container(key="sidebar_toevoegen_preekschetsen"), st.expander("Preekonderdeel toevoegen"):
                _preek_ready = st.session_state.get(
                    f"preek_selectie_{analysis_id}", {}
                ).get("opgeslagen", False)
                for at in preek_missing:
                    _add_lock_key = f"analysis_add_lock_{analysis_id}_{at['name']}"
                    _add_locked = _reanalysis_is_locked(_add_lock_key)
                    _ok, _ontbr = _deps_ok(at, latest)
                    # Hulpstukken (focus_en_functie, illustraties) zijn geen
                    # preekschets en vereisen géén opgeslagen kernteksten/perspectieven-
                    # selectie. Ze worden via de reguliere analyse-trigger uitgevoerd,
                    # zodat ze ook zonder voorbereide selectie kunnen starten.
                    _is_hulpstuk = at["name"] in _PREEKSCHETS_HULPSTUKKEN
                    if _is_hulpstuk:
                        if not _ok:
                            _label = f"🔒 {at['front_end_name']}"
                            _help = "Vereist eerst: " + ", ".join(_ontbr)
                        else:
                            _label = at["front_end_name"]
                            _help = None
                        _disabled = _add_locked or not _ok
                    else:
                        if not _preek_ready:
                            _label = f"🔒 {at['front_end_name']}"
                            _help = "Stel eerst de selectie in via 'Selectie instellen'."
                        elif not _ok:
                            _label = f"🔒 {at['front_end_name']}"
                            _help = "Vereist eerst: " + ", ".join(_ontbr)
                        else:
                            _label = at["front_end_name"]
                            _help = None
                        _disabled = _add_locked or not _preek_ready or not _ok
                    if st.button(
                        _label,
                        key=f"pkadd_{at['name']}",
                        use_container_width=True,
                        disabled=_disabled,
                        help=_help,
                    ):
                        if _is_hulpstuk:
                            _trigger_analysis(int(analysis_id), at, _add_lock_key)
                        else:
                            _trigger_preekschets(int(analysis_id), at, _add_lock_key)

    elif current_tab == "Gebeden":
        for r in gebed_summary:
            label = r["analysis_type"]["front_end_name"]
            is_selected = r["id"] == st.session_state["selected_gebed_id"]
            btn_type = "primary" if is_selected else "secondary"
            if st.button(
                label, key=f"gbnav_{r['id']}", use_container_width=True, type=btn_type
            ):
                st.session_state["selected_gebed_id"] = r["id"]
                st.session_state["current_tab"] = current_tab
                st.rerun()

        # Verberg de expander zodra alle gebeden aanwezig zijn: er valt
        # dan niets meer toe te voegen. Zodra de gebruiker er één
        # verwijdert, komt het type weer in `gebed_missing` en verschijnt
        # de expander automatisch terug. Container-key zorgt dat de
        # paginascoped CSS deze expander subtiel oranje kleurt. Bij
        # overschreden tokenlimiet verbergen we de expander in zijn geheel.
        if gebed_missing and not _limiet_overschreden:
            with st.container(key="sidebar_toevoegen_gebeden"), st.expander("Gebed toevoegen"):
                for at in gebed_missing:
                    _add_lock_key = f"analysis_add_lock_{analysis_id}_{at['name']}"
                    _add_locked = _reanalysis_is_locked(_add_lock_key)
                    _ok, _ontbr = _deps_ok(at, latest)
                    _label = (
                        f"🔒 {at['front_end_name']}" if not _ok else at["front_end_name"]
                    )
                    _help = ("Vereist eerst: " + ", ".join(_ontbr)) if not _ok else None
                    if st.button(
                        _label,
                        key=f"gbadd_{at['name']}",
                        use_container_width=True,
                        disabled=_add_locked or not _ok,
                        help=_help,
                    ):
                        _trigger_analysis(int(analysis_id), at, _add_lock_key)

    elif current_tab == "Feedback":
        # Feedback-analysen navigatie
        for r in feedback_nav_summary:
            label = r["analysis_type"]["front_end_name"]
            is_selected = r["id"] == st.session_state["selected_feedback_id"]
            btn_type = "primary" if is_selected else "secondary"
            if st.button(
                label, key=f"fbnav_{r['id']}", use_container_width=True, type=btn_type
            ):
                st.session_state["selected_feedback_id"] = r["id"]
                st.session_state["current_tab"] = current_tab
                st.rerun()

        # Verberg de expander zodra alle feedback-types aanwezig zijn: er
        # valt dan niets meer toe te voegen. Zodra de gebruiker er één
        # verwijdert, komt het type weer in `feedback_nav_missing` en
        # verschijnt de expander automatisch terug. Container-key zorgt
        # dat de paginascoped CSS deze expander subtiel oranje kleurt.
        # Bij overschreden tokenlimiet verbergen we de expander in zijn geheel.
        if feedback_nav_missing and not _limiet_overschreden:
            with st.container(key="sidebar_toevoegen_feedback"), st.expander("Feedback toevoegen"):
                for at in feedback_nav_missing:
                    _add_lock_key = f"analysis_add_lock_{analysis_id}_{at['name']}"
                    _add_locked = _reanalysis_is_locked(_add_lock_key)
                    _ok, _ontbr = _deps_ok(at, latest)
                    _label = (
                        f"🔒 {at['front_end_name']}" if not _ok else at["front_end_name"]
                    )
                    _help = ("Vereist eerst: " + ", ".join(_ontbr)) if not _ok else None
                    if st.button(
                        _label,
                        key=f"fbadd_{at['name']}",
                        use_container_width=True,
                        disabled=_add_locked or not _ok,
                        help=_help,
                    ):
                        _trigger_analysis(int(analysis_id), at, _add_lock_key)

# Ververs-knop onderaan de zijbalk: invalideert zowel de per-analyse sessiecache
# (`overview_data_{analysis_id}`) als de globale get_cached_data-cache. Zo worden
# extern gestarte analyses (bv. liedsuggesties via de agent) én wijzigingen in
# referentie-data (liedboeken, liturgie) zichtbaar zonder dat de gebruiker hoeft
# uit te loggen of de server opnieuw moet starten.
with st.sidebar:
    if st.button("🔄 Ververs", use_container_width=True, key="sidebar_refresh"):
        st.session_state["analysis_data_dirty"] = True
        # Wis ook de get_cached_data-cache (liedboeken, bijbelvertalingen,
        # liturgie, e.d.). De TTL van 60s vangt dit normaal automatisch op,
        # maar een expliciete klik moet direct effect hebben.
        get_cached_data.clear()
        # Behoud het actieve tabblad expliciet — zonder deze regel valt het
        # segmented_control bij een rerun terug op "Basis". Alle andere zijbalk-
        # knoppen hergebruiken dit patroon om dezelfde reden.
        st.session_state["current_tab"] = current_tab
        st.rerun()

# --- Dialogs ---


@st.dialog("Analyse-element verwijderen")
def confirm_delete_result(result: dict) -> None:
    """Bevestigingsdialoog voor het permanent verwijderen van een analyseresultaat."""
    label = result["analysis_type"]["front_end_name"]
    st.write(
        f"Weet je zeker dat je **'{label}'** wilt verwijderen? "
        "Dit kan niet ongedaan worden gemaakt."
    )
    # Placeholder bovenaan zodat een eventuele foutmelding zichtbaar blijft
    # boven de knoppen, ook als de dialoog opnieuw wordt gerenderd.
    _error_slot = st.empty()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ja, verwijderen", type="primary", use_container_width=True):
            try:
                handler = st.session_state["api_handler"]
                # sermon_analysis_id is vereist als query-parameter door de DRF-viewset
                # (zie analysis_result/views.py:AnalysisResultViewSet.get_queryset).
                sermon_analysis_id = result["sermon_analysis"]["id"]
                analysis_type_id = result["analysis_type"]["id"]
                # De overzichtspagina toont per analyse-type alleen het meest recente
                # resultaat; door eerdere 'Opnieuw'-runs kunnen er meerdere records
                # zijn. We verwijderen daarom alle records voor dit (sermon_analysis,
                # analysis_type)-paar, anders duikt de vorige versie meteen weer op.
                #
                # Preekschetsen hebben zware gekoppelde AnalysisRun-records (agent_messages
                # kan megabytes groot zijn); cascade-delete kan lang duren, dus 120s timeout.
                with st.spinner("Bezig met verwijderen..."):
                    alle_records = handler.get(
                        "api/analysis-results/",
                        params={
                            "sermon_analysis_id": sermon_analysis_id,
                            "analysis_type_id": analysis_type_id,
                        },
                    )
                    verwijderde_ids: list[int] = []
                    for rec in alle_records or []:
                        handler.delete(
                            f"api/analysis-results/{rec['id']}/"
                            f"?sermon_analysis_id={sermon_analysis_id}",
                            timeout=120,
                        )
                        verwijderde_ids.append(rec["id"])
                # Ruim lokale selectie-state op voor het zojuist verwijderde resultaat,
                # zodat de tab niet blijft wijzen naar een id dat niet meer bestaat.
                for _key in (
                    "selected_analysis_id",
                    "selected_verdiep_id",
                    "selected_perspect_id",
                    "selected_preek_id",
                    "selected_gebed_id",
                    "selected_feedback_id",
                ):
                    if st.session_state.get(_key) == result["id"]:
                        st.session_state.pop(_key, None)
                # Markeer de cache als vervuild zodat de overzichtspagina ververst.
                st.session_state["analysis_data_dirty"] = True
                st.toast("Analyse verwijderd.")
                st.rerun()
            except Exception as e:
                # Toon de volledige fout (incl. HTTP-respons als die er is) zodat
                # stille backend-fouten (bv. 500, timeout) niet onzichtbaar blijven.
                resp_text = ""
                resp = getattr(e, "response", None)
                if resp is not None:
                    try:
                        resp_text = f" — status {resp.status_code}: {resp.text[:500]}"
                    except Exception:
                        resp_text = ""
                _error_slot.error(f"Fout bij verwijderen: {e}{resp_text}")
    with col2:
        if st.button("Annuleren", use_container_width=True):
            st.rerun()


@st.dialog("Informatie")
def show_analysis_info(result: dict) -> None:
    """Toon de beschrijving van een analyse-type in een modale dialoog.

    Vervangt de voormalige st.popover-trigger: die bleef tijdens een Streamlit-
    rerun helder gekleurd terwijl de rest van de pagina dimt, waardoor de
    Informatie-knop visueel door het grijze waas heen stak. Een reguliere
    knop + dialog dimt wél consistent met de andere actieknoppen.
    """
    _desc = result["analysis_type"].get("description") or ""
    _titel = result["analysis_type"].get("front_end_name") or "Informatie"
    st.subheader(_titel)
    st.markdown(_desc)
    if st.button("Sluiten", use_container_width=True):
        st.rerun()


@st.dialog("Analyse opnieuw uitvoeren")
def confirm_rerun_analysis(result: dict) -> None:
    """Bevestigingsdialoog voor het opnieuw uitvoeren van een analyse via de agent.

    Dispatcht op preekschets vs. standaard-analyse zodat het lock-mechanisme
    en de juiste endpoint van het bestaande trigger-helperpaar hergebruikt worden.
    """
    at = result["analysis_type"]
    front_end_name = at["front_end_name"]
    st.write(
        f"Weet je zeker dat je **'{front_end_name}'** opnieuw wilt uitvoeren? "
        "Dit kan enkele minuten duren."
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ja, opnieuw uitvoeren", type="primary", use_container_width=True):
            # Hergebruik dezelfde lock-key-conventie als de 'Analyse toevoegen'-knoppen,
            # zodat dubbele triggers (toevoegen én rerun) elkaar ook blokkeren.
            lock_key = f"analysis_add_lock_{result['sermon_analysis']['id']}_{at['name']}"
            if at["name"] in _PREEKSCHETSEN_NAMEN:
                # Preekschetsen hebben een opgeslagen selectie nodig (kernteksten,
                # focus-en-functie, perspectieven, illustraties, hoorders).
                _trigger_preekschets(int(result["sermon_analysis"]["id"]), at, lock_key)
            else:
                _trigger_analysis(int(result["sermon_analysis"]["id"]), at, lock_key)
            st.rerun()
    with col2:
        if st.button("Annuleren", use_container_width=True):
            st.rerun()


def _render_titel_en_actieknoppen(result: dict, key_prefix: str) -> None:
    """Render de titel (front_end_name) gevolgd door de vier actieknoppen.

    Gebundeld zodat alle tabs dezelfde volgorde hanteren: titel → knoppen →
    scheidingslijn → inhoud. De afsluitende st.divider() wordt hier centraal
    gerenderd zodat elke analyse (over alle tabbladen heen) exact dezelfde kop
    heeft; individuele renderers mogen geen eigen leading divider meer tekenen.
    """
    st.title(result["analysis_type"]["front_end_name"])
    _render_actieknoppen(result, key_prefix)
    st.divider()


def _render_actieknoppen(result: dict, key_prefix: str) -> None:
    """Render de vier actieknoppen (Verwijder / Opnieuw / Aanpassen / ℹ️) onder een analysetitel.

    key_prefix voorkomt sleutelbotsingen tussen tabbladen (bv. 'basis', 'verdieping').

    Wanneer de early-test-tokenlimiet overschreden is, verdwijnt "Opnieuw"
    (de enige actieknop hier die een LLM-call triggert via
    confirm_rerun_analysis). "Verwijder" en "Aanpassen" blijven zichtbaar
    omdat die alleen op de DB werken; "ℹ️" toont enkel een beschrijving.
    """
    _toon_opnieuw = not tokenlimiet_bereikt()
    col_del, col_rerun, col_ctx, col_info = st.columns([3, 3, 3, 1])
    with col_del:
        if st.button("Verwijder", icon="🗑️", key=f"{key_prefix}_del"):
            confirm_delete_result(result)
    if _toon_opnieuw:
        with col_rerun:
            if st.button("Opnieuw", icon="🔄", key=f"{key_prefix}_rerun"):
                confirm_rerun_analysis(result)
    with col_ctx:
        if st.button("Aanpassen", icon="✏️", key=f"{key_prefix}_ctx"):
            aanpassen_dialog(result)
    with col_info:
        # Informatie-knop als reguliere st.button + @st.dialog in plaats van
        # st.popover. Reden: de popover-trigger wordt buiten Streamlits rerun-
        # overlay gerenderd en blijft daardoor helder terwijl de rest van de
        # pagina dimt. Een gewone knop dimt wél consistent met de andere drie.
        _desc = result["analysis_type"].get("description")
        if _desc:
            if st.button("ℹ️", key=f"{key_prefix}_info"):
                show_analysis_info(result)


@st.dialog("Selectie van input voor preekschetsen", width="large")
def preekschets_selectie_dialog(
    analysis_id: int, latest: dict, perspect_summary: list
) -> None:
    """Popup voor het instellen en opslaan van de preekschets-input selectie."""

    # Haal eerder opgeslagen selectie op. Streamlit ruimt widget-state op zodra
    # een @st.dialog sluit, dus zonder deze her-hydratatie staan alle velden leeg
    # bij een volgend openen. We lezen één keer uit en geven per widget een default.
    _saved = st.session_state.get(f"preek_selectie_{analysis_id}", {})
    _saved_kernteksten: set[str] = set(_saved.get("kernteksten", []))
    _saved_focus_optie = _saved.get("focus_optie")
    _saved_perspectieven: dict[str, list] = _saved.get("perspectieven", {}) or {}
    _saved_illustraties: set[int] = set(_saved.get("illustraties", []))
    _saved_hoorders: set[str] = set(_saved.get("hoorders", []))
    # Theologie + Commentaren samen: dict met keys 'theology' (lijst
    # notie-namen) en 'commentaries' (lijst identifiers, zie hieronder).
    _saved_exegese: dict[str, list] = _saved.get("exegese_commentaar", {}) or {}
    _saved_theology: set[str] = set(_saved_exegese.get("theology", []) or [])
    _saved_commentaries: set[str] = set(_saved_exegese.get("commentaries", []) or [])

    # -- Focus-en-functie --
    focus = latest.get("focus_en_functie", {})
    focus_result = focus.get("result", {}) if focus else {}
    opties = focus_result.get("opties", []) if isinstance(focus_result, dict) else []

    st.subheader("Focus-en-functie")
    focus_optie_value = None
    if opties:
        optie_labels = [
            f"Optie {o.get('nummer', i + 1)}: {o.get('korte_titel', '')}"
            for i, o in enumerate(opties)
        ]
        # Voorselecteer het eerder opgeslagen nummer, indien nog aanwezig in de opties.
        _saved_idx = next(
            (i for i, o in enumerate(opties) if o.get("nummer") == _saved_focus_optie),
            None,
        )
        keuze = st.radio(
            "Focus-en-functie optie",
            options=optie_labels,
            index=_saved_idx,
            label_visibility="collapsed",
            key=f"dlg_focus_radio_{analysis_id}",
        )
        if keuze:
            idx = optie_labels.index(keuze)
            focus_optie_value = opties[idx].get("nummer")
    else:
        st.caption("*Focus-en-functie nog niet beschikbaar*")

    st.divider()

    # -- Kerntekst(en) --
    # `bijbelteksten.result` is sinds de lijst-refactor een list van lezing-entries
    # (elk met 'reference' en 'verses'). Zie analyses/bijbelteksten.py voor de reden:
    # Postgres jsonb bewaart object-key-volgorde niet, list-volgorde wél.
    #
    # `reference` kan het volledige perikoop-bereik bevatten, bv. "Lucas 24,13-35"
    # of "Lucas 24:13-35". We strippen de versbereik-suffix zodat elk afzonderlijk
    # vers als `Lucas 24:33` wordt getoond — anders krijg je lelijke labels zoals
    # `Lucas 24,13-35:33` die óók in de prompt belanden en door het LLM worden
    # overgenomen. De backend doet exact dezelfde normalisatie; wijzig ze samen.
    bijbel = latest.get("bijbelteksten", {})
    bijbel_result = bijbel.get("result") if bijbel else None
    verzen = []
    if isinstance(bijbel_result, list):
        for scripture in bijbel_result:
            if not isinstance(scripture, dict):
                continue
            raw_ref = (scripture.get("reference") or "").rstrip(".").strip()
            # Knip vanaf de eerste ':' of ',' zodat alleen 'Boek Hoofdstuk' overblijft.
            book_chapter = re.split(r"[:,]", raw_ref, maxsplit=1)[0].strip()
            for verse in scripture.get("verses", []) or []:
                number = verse.get("number", "")
                text = (verse.get("modern_text") or "").strip()
                verzen.append({"ref": f"{book_chapter}:{number}", "text": text})

    st.subheader("Kerntekst(en)")
    selected_refs = []
    if verzen:
        for v in verzen:
            ref = v["ref"]
            preview = v["text"][:110] + ("…" if len(v["text"]) > 110 else "")
            label = f"**{ref}** — {preview}"
            if st.checkbox(
                label,
                value=ref in _saved_kernteksten,
                key=f"dlg_kt_{analysis_id}_{ref}",
            ):
                selected_refs.append(ref)
    else:
        st.caption("*Bijbelteksten nog niet beschikbaar*")

    st.divider()

    # -- Exegese & Commentaren (Theologie + Commentaren samen, max 5) --
    # De structuralistische exegese wordt altijd automatisch geïnjecteerd en
    # hoort dus níét in deze selectielijst. Voor de overige analyses mag de
    # prediker maximaal 5 onderdelen aanvinken — gecombineerd over Theologie
    # (noties) en Commentaren (exegeses + reflectie-lijnen). De telling werkt
    # identiek aan de perspectieven-limiet: we inventariseren eerst de items
    # en tellen hoeveel checkboxes momenteel aanstaan, zodat we boven de
    # limiet verder aanvinken kunnen blokkeren.
    _MAX_EXEGESE_SELECTIE = 5

    def _lees_json_result(raw: object) -> dict:
        """Parseer een dict-result; accepteer ook een string (LLM-JSON in ```-blok)."""
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
                if cleaned.endswith("```"):
                    cleaned = cleaned[: cleaned.rfind("```")]
            try:
                parsed = json.loads(cleaned)
                return parsed if isinstance(parsed, dict) else {}
            except (json.JSONDecodeError, ValueError):
                return {}
        return {}

    theology_data = latest.get("theology", {}) or {}
    theology_result = _lees_json_result(theology_data.get("result"))
    noties: list[dict] = (
        theology_result.get("theologische_analyse", {}).get("noties", []) or []
    )

    commentaries_data = latest.get("commentaries", {}) or {}
    commentaries_result = _lees_json_result(commentaries_data.get("result"))

    # Bouw eerst de lijst van commentaar-items (id, label) zodat zowel de
    # pre-telling als de render dezelfde keys gebruiken.
    comm_items: list[tuple[str, str]] = []
    for _sleutel, _veld in (
        ("exegese_eerste_lezing", "Eerste lezing"),
        ("exegese_evangelielezing", "Evangelielezing"),
    ):
        _blok = commentaries_result.get(_sleutel) or {}
        if isinstance(_blok, dict) and (_blok.get("tekst") or _blok.get("korte_samenvatting")):
            _schrift = (_blok.get("schriftgedeelte") or "").strip()
            _titel = (_blok.get("titel") or "").strip()
            _label = f"{_veld}" + (f" — {_schrift}" if _schrift else "")
            if _titel:
                _label += f" ({_titel})"
            comm_items.append((_sleutel, _label))

    _reflectie = commentaries_result.get("reflectie") or {}
    if isinstance(_reflectie, dict):
        for _idx, _lijn in enumerate(_reflectie.get("theologische_lijnen", []) or []):
            if isinstance(_lijn, str) and _lijn.strip():
                _preview = _lijn.strip()[:110] + ("…" if len(_lijn.strip()) > 110 else "")
                comm_items.append((f"reflectie:{_idx}", f"Theologische lijn — {_preview}"))
        _hp = _reflectie.get("homiletische_potentie")
        if isinstance(_hp, str) and _hp.strip():
            _preview = _hp.strip()[:110] + ("…" if len(_hp.strip()) > 110 else "")
            comm_items.append(("reflectie:homiletische_potentie", f"Homiletische potentie — {_preview}"))

    selected_theology: list[str] = []
    selected_commentaries: list[str] = []

    if noties or comm_items:
        st.subheader("Exegese & Commentaren")
        st.caption(
            "De structuralistische exegese wordt standaard volledig meegegeven. "
            "Kies hieronder aanvullend maximaal "
            f"**{_MAX_EXEGESE_SELECTIE}** onderdelen uit Theologie en/of Commentaren."
        )

        # Tel aangevinkte checkboxes vóór de eerste rerun-stabilisatie: check
        # session_state, val anders terug op de opgeslagen selectie. Zelfde
        # patroon als bij de perspectieven-telling hierboven.
        _ex_aangevinkt = 0
        for _notie in noties:
            _naam = _notie.get("naam", "")
            if not _naam:
                continue
            _key = f"dlg_theo_{analysis_id}_{_naam}"
            if _key in st.session_state:
                if st.session_state[_key]:
                    _ex_aangevinkt += 1
            elif _naam in _saved_theology:
                _ex_aangevinkt += 1
        for _cid, _ in comm_items:
            _key = f"dlg_comm_{analysis_id}_{_cid}"
            if _key in st.session_state:
                if st.session_state[_key]:
                    _ex_aangevinkt += 1
            elif _cid in _saved_commentaries:
                _ex_aangevinkt += 1

        _ex_limiet_bereikt = _ex_aangevinkt >= _MAX_EXEGESE_SELECTIE
        st.caption(
            f"Aangevinkt: **{_ex_aangevinkt}/{_MAX_EXEGESE_SELECTIE}**."
        )

        # -- Theologische noties --
        if noties:
            with st.expander("Theologie — noties", expanded=bool(_saved_theology)):
                for _notie in noties:
                    _naam = _notie.get("naam", "")
                    if not _naam:
                        continue
                    _type = _notie.get("type", "")
                    _samenvatting = (_notie.get("korte_samenvatting") or "").strip()
                    _preview = (_samenvatting[:110] + "…") if len(_samenvatting) > 110 else _samenvatting
                    _label = f"**{_naam}** — _{_type}_" + (f"  ·  {_preview}" if _preview else "")
                    _key = f"dlg_theo_{analysis_id}_{_naam}"
                    _is_aan = st.session_state.get(_key, _naam in _saved_theology)
                    _disabled = _ex_limiet_bereikt and not _is_aan
                    if st.checkbox(
                        _label,
                        value=_naam in _saved_theology,
                        key=_key,
                        disabled=_disabled,
                    ):
                        selected_theology.append(_naam)

        # -- Commentaar-onderdelen --
        if comm_items:
            with st.expander("Commentaren — onderdelen", expanded=bool(_saved_commentaries)):
                for _cid, _label in comm_items:
                    _key = f"dlg_comm_{analysis_id}_{_cid}"
                    _is_aan = st.session_state.get(_key, _cid in _saved_commentaries)
                    _disabled = _ex_limiet_bereikt and not _is_aan
                    if st.checkbox(
                        _label,
                        value=_cid in _saved_commentaries,
                        key=_key,
                        disabled=_disabled,
                    ):
                        selected_commentaries.append(_cid)

        st.divider()

    # -- Perspectieven --
    # Globale max: de gebruiker mag in totaal maximaal 5 perspectief-onderdelen
    # aanvinken over alle perspectieven heen. We tellen aan het begin van de
    # render hoeveel checkboxes momenteel aangevinkt staan (via session_state)
    # en gebruiken die telling om verder aanvinken te blokkeren zodra 5 bereikt is.
    _MAX_PERSPECTIEF_SELECTIE = 5
    selected_perspectieven: dict[str, list] = {}
    if perspect_summary:
        st.subheader("Perspectieven")

        # Bouw eerst een lijst van (perspectief, analyses) zodat we de widget-keys
        # alvast kennen en kunnen tellen hoeveel checkboxes nu aan staan.
        _perspect_blocks: list[tuple[dict, list, set]] = []
        for perspect in perspect_summary:
            name = perspect["analysis_type"]["name"]
            result = perspect.get("result", {})
            if isinstance(result, str):
                cleaned = result.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[-1]
                    if cleaned.endswith("```"):
                        cleaned = cleaned[: cleaned.rfind("```")]
                try:
                    result = json.loads(cleaned)
                except (json.JSONDecodeError, ValueError):
                    result = {}
            analyses = result.get("analyses", []) if isinstance(result, dict) else []
            if not analyses:
                continue
            _saved_per_perspect = set(_saved_perspectieven.get(name, []) or [])
            _perspect_blocks.append((perspect, analyses, _saved_per_perspect))

        # Tel huidige aangevinkte checkboxes. Bij de eerste render (voor een
        # checkbox nog niet in session_state zit) valt de telling terug op
        # de eerder opgeslagen selectie — zo voorkomen we dat de limiet bij
        # het openen van de dialoog klopt vóór de eerste rerun.
        _huidige_aangevinkt = 0
        for perspect, analyses, _saved in _perspect_blocks:
            name = perspect["analysis_type"]["name"]
            for item in analyses:
                nummer = item.get("nummer", "")
                key = f"dlg_perspect_{analysis_id}_{name}_{nummer}"
                if key in st.session_state:
                    if st.session_state[key]:
                        _huidige_aangevinkt += 1
                elif nummer in _saved:
                    _huidige_aangevinkt += 1

        _limiet_bereikt = _huidige_aangevinkt >= _MAX_PERSPECTIEF_SELECTIE
        st.caption(
            f"Maximaal {_MAX_PERSPECTIEF_SELECTIE} onderdelen over alle "
            f"perspectieven heen — nu aangevinkt: "
            f"**{_huidige_aangevinkt}/{_MAX_PERSPECTIEF_SELECTIE}**."
        )

        for perspect, analyses, _saved_per_perspect in _perspect_blocks:
            name = perspect["analysis_type"]["name"]
            front_end_name = perspect["analysis_type"]["front_end_name"]
            # Expander open tonen als dit perspectief eerder onderdelen geselecteerd had.
            with st.expander(front_end_name, expanded=bool(_saved_per_perspect)):
                selected_onderdelen = []
                for item in analyses:
                    nummer = item.get("nummer", "")
                    titel = item.get("titel", "")
                    label = f"{nummer}. {titel}" if nummer else titel
                    key = f"dlg_perspect_{analysis_id}_{name}_{nummer}"
                    # Een checkbox is uitgeschakeld zodra de globale limiet is
                    # bereikt, tenzij hij al aangevinkt staat (dan mag de
                    # gebruiker hem nog uitzetten).
                    _is_aangevinkt = st.session_state.get(key, nummer in _saved_per_perspect)
                    _disabled = _limiet_bereikt and not _is_aangevinkt
                    if st.checkbox(
                        label,
                        value=nummer in _saved_per_perspect,
                        key=key,
                        disabled=_disabled,
                    ):
                        selected_onderdelen.append(nummer)
                selected_perspectieven[name] = selected_onderdelen
        st.divider()

    # -- Illustraties --
    selected_illustraties: list[int] = []
    illustraties_data = latest.get("illustraties", {})
    illustraties_result = (
        illustraties_data.get("result", {}) if illustraties_data else {}
    )
    illustraties_lijst = (
        illustraties_result.get("illustraties", [])
        if isinstance(illustraties_result, dict)
        else []
    )
    if illustraties_lijst:
        st.subheader("Illustraties")
        for ill in illustraties_lijst:
            nummer = ill.get("nummer", 0)
            titel = ill.get("titel", "")
            ill_type = ill.get("metadata", {}).get("type", "")
            label = f"#{nummer} — {titel}" + (f"  ({ill_type})" if ill_type else "")
            if st.checkbox(
                label,
                value=nummer in _saved_illustraties,
                key=f"dlg_ill_{analysis_id}_{nummer}",
            ):
                selected_illustraties.append(nummer)
        st.divider()

    # -- Representatieve aanwezigen --
    # Leest uit `representatieve_aanwezigen` (Preekschetsen-tab). Valt terug
    # op de oude `representatieve_hoorders`-naam als die nog bestaat, zodat
    # eerder aangemaakte analyses niet stilzwijgend verdwijnen uit de dialoog.
    selected_hoorders: list[str] = []
    hoorders_data = latest.get("representatieve_aanwezigen") or latest.get(
        "representatieve_hoorders", {}
    )
    hoorders_result = hoorders_data.get("result", {}) if hoorders_data else {}
    personas = (
        hoorders_result.get("personas", []) if isinstance(hoorders_result, dict) else []
    )
    if personas:
        st.subheader("Representatieve aanwezigen")
        for persona in personas:
            naam_obj = persona.get("naam", {})
            voornaam = naam_obj.get("voornaam", "")
            achternaam = naam_obj.get("achternaam", "")
            volledige_naam = f"{voornaam} {achternaam}".strip()
            leeftijd = persona.get("leeftijd", "")
            label = f"👤 {volledige_naam}" + (f" ({leeftijd})" if leeftijd else "")
            if st.checkbox(
                label,
                value=volledige_naam in _saved_hoorders,
                key=f"dlg_hoorder_{analysis_id}_{volledige_naam}",
            ):
                selected_hoorders.append(volledige_naam)
        st.divider()

    # -- Opslaan --
    # Focus-en-functie is alleen verplicht als de analyse al beschikbaar is.
    _focus_beschikbaar = bool(opties)
    _kan_opslaan = bool(selected_refs) and (
        not _focus_beschikbaar or focus_optie_value is not None
    )
    if not selected_refs:
        st.warning("Selecteer minimaal één kerntekst.")
    if _focus_beschikbaar and focus_optie_value is None:
        st.warning("Selecteer een focus-en-functie optie.")
    if st.button(
        "Opslaan", type="primary", use_container_width=True, disabled=not _kan_opslaan
    ):
        _nieuwe_selectie = {
            "kernteksten": selected_refs,
            "focus_optie": focus_optie_value,
            "perspectieven": selected_perspectieven,
            "illustraties": selected_illustraties,
            "hoorders": selected_hoorders,
            # Gecombineerde Theologie + Commentaren selectie (max 5);
            # de agent splitst dit weer uit via `selected_exegese_commentaar`.
            "exegese_commentaar": {
                "theology": selected_theology,
                "commentaries": selected_commentaries,
            },
            "opgeslagen": True,
        }
        # Persisteer de selectie op de backend zodat hij een login-cyclus
        # overleeft. We schrijven eerst naar de server en pas daarna naar
        # session_state: als de PATCH faalt, blijft de oude selectie zichtbaar
        # en krijgt de voorganger een foutmelding i.p.v. stille dataverlies.
        try:
            st.session_state["api_handler"].patch(
                f"api/sermon-analyses/{analysis_id}/",
                data={"preekschets_selectie": _nieuwe_selectie},
            )
        except requests.exceptions.HTTPError as exc:
            st.error(f"Opslaan mislukt: {exc}. Probeer het opnieuw.")
            st.stop()
        st.session_state[f"preek_selectie_{analysis_id}"] = _nieuwe_selectie
        # Gooi de per-analyse datacache weg zodat de volgende rerun het
        # bijgewerkte sermon_analysis (inclusief preekschets_selectie) uit
        # de backend haalt; zo blijft de hydratie-logica in overview.py in
        # sync bij een harde refresh.
        st.session_state.pop(f"overview_data_{analysis_id}", None)
        st.rerun()


@st.dialog("Eigen preek invoeren", width="large")
def volledige_preek_dialog(
    analysis_id: int,
    latest: dict,
    all_analysis_types: list,
    sermon_analysis: dict,
) -> None:
    """Dialoog voor het invoeren of bewerken van de volledige preektekst."""
    existing = latest.get("volledige_preek")
    existing_result = existing.get("result", {}) if existing else {}
    if not isinstance(existing_result, dict):
        existing_result = {}

    titel = existing_result.get("titel", "")
    ondertitel = existing_result.get("ondertitel", "")
    preektekst = existing_result.get("preektekst", "")

    st.caption(
        "Voer de preektekst in (kopieer/plak uit tekstverwerker of schrijf direct)."
    )

    new_titel = st.text_input(
        "Titel", value=titel, placeholder="bijv. Het brood dat leven geeft", max_chars=200
    )
    new_ondertitel = st.text_input(
        "Ondertitel",
        value=ondertitel,
        placeholder="bijv. Johannes 6:35 — preek gehouden op 30 maart 2025",
        max_chars=300,
    )
    new_preektekst = st.text_area(
        "Preektekst",
        value=preektekst,
        height=500,
        placeholder="Plak hier de volledige uitgeschreven preektekst...",
    )

    # Live woordentelling zodat de gebruiker tijdens het plakken/typen ziet of
    # de invoer binnen de min/max-grenzen valt. De feitelijke validatie vindt
    # plaats bij Opslaan; hier wordt het veld dus niet leeggemaakt of beperkt.
    _aantal_woorden = tel_woorden(new_preektekst)
    st.caption(
        f"Aantal woorden: {_aantal_woorden} "
        f"(minimaal {_EIGEN_PREEK_MIN_WOORDEN}, maximaal {_EIGEN_PREEK_MAX_WOORDEN})"
    )

    # Radio voor de feedback-context-keuze. De voorganger kiest welke extra
    # context (Bijbelteksten en/of preekschets-materiaal) door de feedback-
    # prompts mag worden meegelezen. De derde optie (incl. preekschets) is
    # alleen beschikbaar als er ook daadwerkelijk preekschets-resultaten of
    # een opgeslagen selectie bestaan; anders zou hij naar lege injecties
    # leiden. De keuze geldt voor toekomstige feedback-runs op deze preek;
    # bestaande feedback-resultaten blijven ongewijzigd staan.
    _preekschets_beschikbaar = heeft_preekschets_resultaten(
        latest, sermon_analysis
    )
    _ctx_label_naar_waarde: dict[str, str] = {
        "Geen extra context": "geen",
        "Alleen Bijbelteksten": "bijbelteksten",
    }
    if _preekschets_beschikbaar:
        _ctx_label_naar_waarde["Bijbelteksten + Preekschets-materiaal"] = (
            "bijbelteksten_preekschets"
        )
    _ctx_opties: list[str] = list(_ctx_label_naar_waarde.keys())
    _huidige_keuze = (
        sermon_analysis.get("feedback_context_keuze") or "bijbelteksten"
    )
    # Als de huidige opgeslagen keuze niet (meer) in de zichtbare opties zit
    # — bv. preekschets-keuze maar inmiddels geen preekschets-context meer
    # beschikbaar — vallen we terug op 'Alleen Bijbelteksten' als veilige default.
    _huidig_label = next(
        (l for l, v in _ctx_label_naar_waarde.items() if v == _huidige_keuze),
        "Alleen Bijbelteksten",
    )
    _ctx_keuze_label = st.radio(
        "Welke context mag in de feedback-prompts worden meegelezen?",
        _ctx_opties,
        index=_ctx_opties.index(_huidig_label) if _huidig_label in _ctx_opties else 1,
        help=(
            "Bijbelteksten zijn altijd beschikbaar omdat elke kerkdienst-"
            "analyse de Schriftlezingen heeft. Preekschets-materiaal "
            "(perspectieven, representatieve hoorders, kernteksten, "
            "focus/functie en illustraties) is alleen bruikbaar als je de "
            "Preekschetsen-tab eerder hebt gedraaid."
        ),
        key=f"feedback_ctx_radio_{analysis_id}",
    )
    _gekozen_feedback_ctx: str = _ctx_label_naar_waarde[_ctx_keuze_label]

    _kan_opslaan = bool(new_preektekst.strip())
    if st.button(
        "Opslaan", type="primary", use_container_width=True, disabled=not _kan_opslaan
    ):
        # Valideer titel en ondertitel op woorden + SQL-injectie vóór we
        # doorgaan met de preektekst-checks; zo krijgt de prediker een
        # gerichte foutmelding per veld.
        for waarde, veld in ((new_titel, "Titel"), (new_ondertitel, "Ondertitel")):
            ok_titel, fout_titel = valideer_tekstinvoer(
                waarde,
                max_woorden=_EIGEN_PREEK_MAX_WOORDEN_TITEL,
                veldnaam=veld,
            )
            if not ok_titel:
                st.error(fout_titel)
                return

        # Valideer de woordentelling vóór opslaan. Bij overschrijding van de
        # grenzen tonen we een foutmelding en keren we terug zonder het veld
        # leeg te maken — Streamlit's dialog-rerun behoudt de widget-state.
        if _aantal_woorden < _EIGEN_PREEK_MIN_WOORDEN:
            # woord_meervoud() voorkomt grammaticaal foutieve uitvoer als
            # "1 woorden"; de grenzen zijn altijd >1 maar we gebruiken de
            # helper consistent voor beide getallen.
            st.error(
                f"De preektekst bevat {_aantal_woorden} "
                f"{woord_meervoud(_aantal_woorden)}; "
                f"minimaal {_EIGEN_PREEK_MIN_WOORDEN} "
                f"{woord_meervoud(_EIGEN_PREEK_MIN_WOORDEN)} vereist."
            )
            return
        if _aantal_woorden > _EIGEN_PREEK_MAX_WOORDEN:
            st.error(
                f"De preektekst bevat {_aantal_woorden} "
                f"{woord_meervoud(_aantal_woorden)}; "
                f"maximaal {_EIGEN_PREEK_MAX_WOORDEN} "
                f"{woord_meervoud(_EIGEN_PREEK_MAX_WOORDEN)} toegestaan."
            )
            return
        # Aanvullende SQL-injectie-check op de preektekst zelf. De woorden-
        # telling hierboven bewaakt de lengte; deze check weigert expliciete
        # injectie-patronen zonder de legitieme preekinhoud te raken.
        ok_preek_sql, fout_preek_sql = valideer_tekstinvoer(
            new_preektekst,
            max_woorden=_EIGEN_PREEK_MAX_WOORDEN,
            veldnaam="Preektekst",
        )
        if not ok_preek_sql:
            st.error(fout_preek_sql)
            return

        updated = {
            **existing_result,
            "titel": new_titel,
            "ondertitel": new_ondertitel,
            "preektekst": new_preektekst,
        }
        try:
            handler = st.session_state["api_handler"]
            if existing:
                # Bestaande preektekst bijwerken via PATCH.
                handler.patch(
                    f"api/analysis-results/{existing['id']}/?sermon_analysis_id={analysis_id}",
                    data={"result": updated},
                )
            else:
                # Nieuwe preektekst aanmaken via POST.
                vp_at = next(
                    (x for x in all_analysis_types if x["name"] == "volledige_preek"),
                    None,
                )
                if not vp_at:
                    st.error("Analyse-type 'volledige_preek' niet gevonden.")
                    return
                handler.post(
                    "api/analysis-results/",
                    data={
                        "analysis_type": vp_at["id"],
                        "sermon_analysis": analysis_id,
                        # Stuur een lege prompt mee omdat het backend-model dit veld
                        # verplicht opslaat, ook voor handmatig ingevoerde preekteksten.
                        "prompt": {},
                        "result": updated,
                    },
                )
            # Persisteer de feedback-context-keuze op de SermonAnalysis zelf,
            # niet op het analyse-resultaat. Reden: de keuze geldt voor
            # alle (toekomstige) feedback-runs op deze preek en moet een
            # logout/login-cyclus overleven; SermonAnalysis is daarvoor de
            # juiste home, want het Read-Serializer-veld
            # feedback_context_keuze wordt door de agent-pipeline gelezen.
            # Alleen patchen als de keuze daadwerkelijk veranderd is, om
            # onnodige writes naar de DB te voorkomen.
            if _gekozen_feedback_ctx != _huidige_keuze:
                handler.patch(
                    f"api/sermon-analyses/{analysis_id}/",
                    data={"feedback_context_keuze": _gekozen_feedback_ctx},
                )
            st.toast("Preektekst opgeslagen.")
            # Markeer de cache als vervuild zodat de pagina opnieuw laadt.
            st.session_state["analysis_data_dirty"] = True
            st.rerun()
        except Exception as e:
            st.error(f"Fout bij opslaan: {e}")


# --- Tabbladnavigatie ---
st.segmented_control(
    "Tabblad",
    _TABS,
    key="current_tab",
    label_visibility="collapsed",
)
# Herlaad na de widget-render zodat de widget-waarde van deze render gebruikt wordt.
current_tab = st.session_state.get("current_tab", "Basis")

# Subtiele context-regel onder de tabbladen: plaats van de gemeente +
# datum van viering, zodat de voorganger in één oogopslag ziet welke
# kerkdienst hij/zij voor zich heeft. We bouwen de regel alleen op als
# beide velden bekend zijn; ontbreekt er één, dan tonen we wat er wél is
# (geen lege placeholder of streepje). Lichtgrijze, kleine tekst (#8a8a8a)
# zodat de regel niet concurreert met titels of actieknoppen.
_plaats = st.session_state.get("church_place", "")
_sermon_date_iso = sermon_analysis.get("sermon_date") if sermon_analysis else None
try:
    _datum_str = (
        datetime.strptime(_sermon_date_iso, "%Y-%m-%d").strftime("%d-%m-%Y")
        if _sermon_date_iso
        else ""
    )
except (ValueError, TypeError):
    _datum_str = ""

_context_delen: list[str] = []
if _plaats:
    _context_delen.append(_plaats)
if _datum_str:
    _context_delen.append(f"datum van viering: {_datum_str}")
if _context_delen:
    st.markdown(
        f"<div style='color:#8a8a8a; font-size:0.85em; margin-top:-0.5rem; "
        f"margin-bottom:0.75rem;'>{', '.join(_context_delen)}</div>",
        unsafe_allow_html=True,
    )

# Als er nog geen resultaten zijn, komt dat bijna altijd door één van twee situaties:
# (1) de analyse is net aangemaakt en de bijbelteksten worden op de achtergrond opgehaald,
# (2) er staat wel data in de database maar de sessie-cache is nog niet ververst.
# De tekst moet daarom beide gevallen dekken en gebruikers expliciet naar de
# Ververs-knop in de zijbalk verwijzen in plaats van "bijbelteksten wordt geanalyseerd"
# te beweren alsof dat altijd waar is.
if not analysis_results:
    st.info(
        "Er zijn nog geen analyseresultaten zichtbaar. "
        "Als u net een analyse heeft aangemaakt, worden de bijbelteksten op de "
        "achtergrond opgehaald — dit kan even duren. "
        "Klik op '🔄 Ververs' in de zijbalk om opnieuw op te halen."
    )
    st.stop()

# --- Hoofdinhoud per tabblad ---
if current_tab == "Basis":
    # "Selectie instellen"-knop boven aan het Basis-tabblad. De knop hoort
    # bij de hele SermonAnalysis (lezingen + liedbundels), niet bij één
    # specifieke renderer; daarom plaatsen we hem buiten de
    # selected_analysis-tak zodat hij ook zichtbaar is als er nog geen
    # Basis-resultaat (bv. bijbelteksten) beschikbaar is. Layout (kolom 7:3,
    # rechts uitgelijnd) is identiek aan de Preekschetsen-knop verderop.
    _, _btn_col = st.columns([7, 3])
    with _btn_col:
        if st.button(
            "Selectie instellen",
            icon="🎯",
            use_container_width=True,
            key="basis_selectie_instellen",
        ):
            selectie_instellen_dialog(
                int(analysis_id),
                sermon_analysis,
                get_cached_data("api/song-books/"),
            )

    selected_analysis = next(
        (
            r
            for r in analyse_summary
            if r["id"] == st.session_state["selected_analysis_id"]
        ),
        None,
    )
    if not selected_analysis:
        # Er zijn wél resultaten, maar niet in het Basis-tabblad. Dat kan komen doordat
        # de bijbelteksten-stap nog loopt, of doordat alleen andere tabs al entries
        # hebben. De melding is neutraler dan voorheen en verwijst naar de Ververs-knop.
        st.info(
            "Nog geen Basis-analyses beschikbaar. "
            "Klik op '🔄 Ververs' in de zijbalk om recente resultaten op te halen, "
            "of kies een ander tabblad."
        )
        st.stop()

    analysis_type_name = selected_analysis.get("analysis_type", {}).get("name", "")

    # Titel en actieknoppen (Verwijder / Opnieuw / Aanpassen / ℹ️) direct boven de analyse.
    _render_titel_en_actieknoppen(selected_analysis, key_prefix="basis")

    if analysis_type_name == "postille":
        postille(selected_analysis)
    elif analysis_type_name == "bijbelteksten":
        bijbelteksten(selected_analysis)
    elif analysis_type_name == "liturgisch_jaar":
        liturgisch_jaar(selected_analysis)
    elif analysis_type_name == "liedsuggesties":
        liedsuggesties(selected_analysis)
    elif analysis_type_name == "structuralistische_exegese":
        structuralistische_exegese(selected_analysis)
    elif analysis_type_name == "commentaries":
        commentaren(selected_analysis)
    elif analysis_type_name == "theology":
        theologie(selected_analysis)
    elif analysis_type_name == "geloofsorientatie":
        geloofsorientatie(selected_analysis)
    elif analysis_type_name == "representatieve_hoorders":
        representatieve_hoorders(selected_analysis)
    elif analysis_type_name == "wereldnieuws":
        wereldnieuws(selected_analysis)
    elif analysis_type_name == "lokaal_nieuws":
        lokaal_nieuws(selected_analysis)
    elif analysis_type_name == "contextduiding":
        contextduiding(selected_analysis)

    # Toon feedback- en prompt-debugknop onder elke Basis-analyse.
    if selected_analysis:
        render_analysis_footer(
            analysis=selected_analysis,
            handler=st.session_state["api_handler"],
            key_prefix="basis",
        )

elif current_tab == "Verdieping":
    selected_verdiep = next(
        (
            r
            for r in verdiep_summary
            if r["id"] == st.session_state["selected_verdiep_id"]
        ),
        None,
    )
    if not verdiep_summary:
        st.info("Nog geen verdieping beschikbaar.")
    elif selected_verdiep:
        # Titel + actieknoppen, daarna dispatcht de generieke verdieping-renderer
        # op basis van het analyse-type (bv. gebeden_profetisch → render_gebeden).
        _render_titel_en_actieknoppen(selected_verdiep, key_prefix="verdieping")
        verdieping(
            selected_verdiep,
            analysis_type_name=selected_verdiep["analysis_type"]["name"],
        )
        render_analysis_footer(
            analysis=selected_verdiep,
            handler=st.session_state["api_handler"],
            key_prefix="verdieping",
        )

elif current_tab == "Perspectieven":
    selected_perspect = next(
        (
            r
            for r in perspect_summary
            if r["id"] == st.session_state["selected_perspect_id"]
        ),
        None,
    )
    if not perspect_summary:
        st.info("Nog geen perspectieven beschikbaar.")
    elif selected_perspect:
        _render_titel_en_actieknoppen(selected_perspect, key_prefix="perspectieven")
        contextduiding(selected_perspect)
        # Ook perspectieven krijgen de feedback- en prompt-debugknop onderaan.
        render_analysis_footer(
            analysis=selected_perspect,
            handler=st.session_state["api_handler"],
            key_prefix="perspectieven",
        )

elif current_tab == "Preekschetsen":
    selected_preek = next(
        (r for r in preek_summary if r["id"] == st.session_state["selected_preek_id"]),
        None,
    )
    # Knop om de kerntekst- en focus-en-functie-selectie in te stellen of te wijzigen.
    # Vereist is dat de dialog al gedefinieerd is (zie boven).
    _, btn_col = st.columns([7, 3])
    with btn_col:
        if st.button("Selectie instellen", icon="🎯", use_container_width=True):
            preekschets_selectie_dialog(int(analysis_id), latest, perspect_summary)
    if not preek_summary:
        st.info("Nog geen preekschetsen beschikbaar.")
    elif selected_preek:
        # Actieknoppen boven de preekschets; 'Selectie instellen' blijft als aparte knop erboven.
        _render_titel_en_actieknoppen(selected_preek, key_prefix="preekschets")
        _preek_type_name = selected_preek["analysis_type"]["name"]
        # De Preekschetsen-tab bevat naast de daadwerkelijke schetsen ook twee
        # hulpstukken die de predikant als invoer kan gebruiken (focus-en-functie,
        # illustraties). Zij hebben hun eigen renderer en horen niet via de
        # preekschets()-dispatch te lopen.
        if _preek_type_name == "focus_en_functie":
            render_focus_en_functie(selected_preek)
        elif _preek_type_name == "illustraties":
            illustraties(selected_preek)
        elif _preek_type_name == "representatieve_aanwezigen":
            # Representatieve aanwezigen is een hulpstuk onder Preekschetsen:
            # levert vijf persona's die als input dienen voor de preekschets-
            # selectie (checkboxes in preekschets_selectie_dialog). De schema-
            # indeling is identiek aan de oude representatieve_hoorders-analyse,
            # dus we hergebruiken die renderer.
            representatieve_hoorders(selected_preek)
        else:
            # Type-naam doorgeven zodat preekschets() de juiste renderer kiest —
            # Lowry/Buttrick hebben een eigen schema, alle auteurs-preekschetsen
            # vallen terug op het generieke preek_onderdelen-schema.
            preekschets(
                selected_preek,
                analysis_type_name=_preek_type_name,
            )
        # Ontbrak voorheen voor preekschetsen (bv. Noordmans): nu ook hier de feedback- en debug-knoppen.
        render_analysis_footer(
            analysis=selected_preek,
            handler=st.session_state["api_handler"],
            key_prefix="preekschets",
        )

elif current_tab == "Gebeden":
    selected_gebed = next(
        (
            r
            for r in gebed_summary
            if r["id"] == st.session_state["selected_gebed_id"]
        ),
        None,
    )
    if not gebed_summary:
        st.info("Nog geen gebeden beschikbaar.")
    elif selected_gebed:
        # Dezelfde layout als Verdieping: titel + actieknoppen, daarna de
        # generieke verdieping-dispatcher die render_gebeden uit _RENDERERS kiest.
        _render_titel_en_actieknoppen(selected_gebed, key_prefix="gebeden")
        verdieping(
            selected_gebed,
            analysis_type_name=selected_gebed["analysis_type"]["name"],
        )
        render_analysis_footer(
            analysis=selected_gebed,
            handler=st.session_state["api_handler"],
            key_prefix="gebeden",
        )

elif current_tab == "Feedback":
    selected_feedback = next(
        (
            r
            for r in feedback_nav_summary
            if r["id"] == st.session_state["selected_feedback_id"]
        ),
        None,
    )
    # Knop rechts uitlijnen via kolommen, consistent met andere actieknoppen.
    _, btn_col = st.columns([7, 3])
    with btn_col:
        if st.button("Eigen preek invoeren", icon="✏️", use_container_width=True):
            volledige_preek_dialog(
                int(analysis_id), latest, all_analysis_types, sermon_analysis
            )
    _vp = latest.get("volledige_preek")
    if _vp:
        # Toon de opgeslagen titel als bevestiging dat er al een preektekst is.
        _vp_titel = (
            _vp.get("result", {}).get("titel", "")
            if isinstance(_vp.get("result"), dict)
            else ""
        )
        if _vp_titel:
            st.caption(f"Opgeslagen: {_vp_titel[:50]}")
    if not feedback_nav_summary:
        if not latest.get("volledige_preek"):
            st.info("Voer eerst een preektekst in via de knop hierboven.")
        else:
            st.info("Voeg feedbackanalyses toe via 'Feedback toevoegen' in de zijbalk.")
    elif selected_feedback:
        # Actieknoppen boven de feedback-analyse; 'Eigen preek invoeren' blijft erboven staan.
        _render_titel_en_actieknoppen(selected_feedback, key_prefix="feedback")
        feedback_analyse(selected_feedback)
        # Ook onder feedback-analyses de feedback- en prompt-debugknop tonen.
        render_analysis_footer(
            analysis=selected_feedback,
            handler=st.session_state["api_handler"],
            key_prefix="feedback",
        )
