"""Batch-runner voor analyses zonder gebruikerskeuzes.

Draait een set analyses voor één SermonAnalysis serieel via de bestaande
REST-endpoints van homiletiek (Django-backend) en homiletiek_agent (FastAPI).
Dependencies worden automatisch toegevoegd; preekschets- en feedback-types
worden weggelaten omdat die per definitie selectie-input van de gebruiker
vereisen die niet zinvol via een CLI is in te vullen.

Gebruik:
    python -m scripts.batch_run_analyses --sermon-id 123
    python -m scripts.batch_run_analyses --sermon-id 123 --dry-run
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from collections import defaultdict, deque
from pathlib import Path
from time import sleep, time
from typing import Any

import questionary
import questionary.prompts.common as _questionary_common
import requests

# Monkey-patch de selectie-indicators in questionary 2.1.1: de defaults
# ('●' en '○') verschillen op veel terminals nauwelijks van elkaar in
# kleur of vorm, waardoor onduidelijk is welke regels door spatie zijn
# aangezet. '[X]' versus '[ ]' is textueel ondubbelzinnig en blijft ook
# leesbaar op terminals zonder kleur. We patchen specifiek
# `questionary.prompts.common` (waar de constanten via `from … import`
# zijn gebonden); aanpassen op `questionary.constants` heeft geen effect
# omdat de naam in common.py al lokaal gebonden is.
_questionary_common.INDICATOR_SELECTED = "[X]"
_questionary_common.INDICATOR_UNSELECTED = "[ ]"

# Maak imports vanuit de streamlit_homiletiek-repo werkend wanneer dit script
# wordt gedraaid als `python -m scripts.batch_run_analyses` (dan zit de repo
# al in sys.path) maar ook als `python scripts/batch_run_analyses.py`.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

# Laad streamlit_homiletiek/.env (project-conventie) zodat API_BASE_URL,
# API_USERNAME, API_PASSWORD én de prod-varianten HEROKU_API_BASE_URL /
# HEROKU_API_AGENT_URL via dezelfde plek beschikbaar zijn als waar de
# rest van het project ze leest. `override=False` zodat een expliciete
# shell-export voorrang houdt boven het bestand.
_DOTENV_PATH = _REPO_ROOT / ".env"
if _DOTENV_PATH.exists():
    load_dotenv(_DOTENV_PATH, override=False)

from src.api.jwthandler import JwtHandler  # noqa: E402

# Endpoints op de Django-backend voor het ophalen van analysetypes,
# bestaande resultaten en de status van de sermon zelf.
#
# /api/analysis-types/ gebruikt depth=3 en serialiseert recursief over
# de self-M2M `depends_on` — bij 60+ types loopt dat over de Heroku-30s-
# timeout heen (H12). De /slim/-action geeft alleen wat we hier nodig
# hebben (id, name, depends_on als id-list, group als string) en is
# meetbaar binnen 2s. We vallen bij een 404 terug op de volledige
# endpoint zodat het script óók werkt tegen oudere backends die /slim/
# nog niet hebben.
_ANALYSIS_TYPES_PATH: str = "/api/analysis-types/slim/"
_ANALYSIS_TYPES_FALLBACK_PATH: str = "/api/analysis-types/"
_ANALYSIS_RESULTS_PATH: str = "/api/analysis-results/"
_SERMON_ANALYSES_PATH: str = "/api/sermon-analyses/"

# JWT-endpoints van de Django-backend (zelfde als die de Streamlit-app gebruikt).
_JWT_ACCESS_PATH: str = "/api/token/"
_JWT_REFRESH_PATH: str = "/api/token/refresh/"

# Endpoint op de agent voor het starten van één analyse op id.
# /single_analysis/ is de id-gebaseerde variant zonder gebruikersinput; bij
# een 409 zit het slot al vol (Redis-lock per (sermon, type)).
_SINGLE_ANALYSIS_PATH: str = "/single_analysis/"

# Defaults — kunnen via CLI of env worden overschreven. Localhost-poorten
# komen overeen met de README van homiletiek + homiletiek_agent.
_DEFAULT_API_BASE_URL: str = "http://127.0.0.1:8000"
_DEFAULT_AGENT_URL: str = "http://127.0.0.1:8080"

# Polling-intervallen. 10s is een redelijk compromis tussen responsiveness
# en backend-load; Streamlit pollt op 15s.
_POLL_INTERVAL_SECONDS: int = 10
_POLL_TIMEOUT_SECONDS: int = 30 * 60  # harde cap per analyse: 30 min
_SLOT_RETRY_DELAY_SECONDS: int = 5
_SLOT_RETRY_MAX: int = 3

# Naam-patronen voor analyses die gebruikerskeuzes vereisen en dus uit de
# CLI-batch worden geweerd. Komen overeen met de groepen die in Streamlit
# een dialog tonen voordat ze gestart kunnen worden:
# - preek_*               → preekschets_selectie (kerntekst, focus, ...)
# - feedback_*            → feedback_context_keuze + handmatige volledige_preek
# - volledige_preek       → handmatig ingevuld door voorganger
# - homiletische_lowry /  → ook preekschets-agents in substitute.py
#   homiletische_buttrick   (zie _HOMILETISCHE_STRUCTUUR_TEMPLATES). Ze
#                           gebruiken kerntekst_selectie, focus_en_functie_selectie
#                           en perspectieven_selectie en falen zonder die
#                           UI-input.
_USER_CHOICE_PREFIXES: tuple[str, ...] = ("preek_", "feedback_")
_USER_CHOICE_NAMES: frozenset[str] = frozenset(
    {
        "volledige_preek",
        "homiletische_lowry",
        "homiletische_buttrick",
    }
)

# Interne types die automatisch worden gevuld bij het aanmaken van een
# SermonAnalysis (of door de base-analysis-flow) en niet via /single_analysis/
# moeten worden getriggerd. Worden uit het menu gefilterd; als ze als
# dependency opduiken en nog niet gevuld zijn, aborteert het script met
# een melding.
# - bijbelteksten / bible_book / chapter_text / scripture: gevuld door
#   /original_scriptures/ en /structured_scripture/ tijdens het aanmaken
#   van de SermonAnalysis.
# - base_analysis / base_analysis_creatief / base_analysis_perspectief_creatief:
#   ondersteunende analyses die door andere modules worden geactiveerd en
#   niet zelfstandig in de UI worden aangeboden.
_INTERNAL_AUXILIARY_NAMES: frozenset[str] = frozenset(
    {
        "bijbelteksten",
        "bible_book",
        "chapter_text",
        "scripture",
        "base_analysis",
        "base_analysis_creatief",
        "base_analysis_perspectief_creatief",
        # brueggemann_methode_selector is alleen een opstap-analyse voor
        # preek_brueggemann_poet (die wegens kerntekst-selectie uit de batch
        # is geweerd). Geen enkele batch-eligible analyse hangt ervan af, dus
        # de "auxiliary missing"-abort-tak wordt nooit getriggerd; toevoegen
        # hier filtert hem uit het menu.
        "brueggemann_methode_selector",
    }
)

# Standaard aangevinkte analyses bij start van het menu — de "core
# productie-set" die voor zo goed als elke preekvoorbereiding nuttig is.
# Perspectieven (14 stuks) blijven default uit omdat ze duur en extra
# zijn; gebeden_dialogisch/profetisch/eenvoudig zijn varianten naast het
# standaard 'gebeden'. brueggemann_methode_selector is een interne hulp-
# analyse die alleen zin heeft als opstap naar preek_brueggemann_poet
# (die uit de batch is geweerd) en blijft daarom default uit.
_DEFAULT_CHECKED_NAMES: frozenset[str] = frozenset(
    {
        # Basis
        "structuralistische_exegese",
        # Postille gebruikt in substitute.py een minimale substitutietak
        # zonder kerntekst-selectie (alleen $voorbeeld_preken) en is dus
        # batch-veilig, ondanks dat het een preekschets-type is.
        "postille",
        # Verdieping (alle 10)
        "kunst_cultuur",
        "gemeente_spiritualiteit",
        "politieke_orientatie",
        "waardenorientatie",
        "interpretatieve_synthese",
        "kindermoment",
        "wetslezing",
        "kalender",
        "bezinningsmoment",
        "poezie_meertalig",
        # SermonOutline-subset zonder kerntekst-selectie
        "representatieve_aanwezigen",
        "illustraties",
        "focus_en_functie",
        # Standaard gebed
        "gebeden",
    }
)


def _is_user_choice_required(at: dict[str, Any]) -> bool:
    """Geeft True als de analyse user-input vereist en uit de batch moet."""
    name: str = at["name"]
    if name in _USER_CHOICE_NAMES:
        return True
    return any(name.startswith(prefix) for prefix in _USER_CHOICE_PREFIXES)


def _extract_dep_ids(depends_on_field: Any) -> list[int]:
    """Pak `depends_on`-IDs uit ongeacht of DRF ze als ints of dicts levert.

    De `AnalysisTypeSerializer` gebruikt `depth=3`, dus dependencies komen als
    geneste objecten. Defensief blijven werken als de serializer ooit naar
    pure id-lists overstapt.
    """
    if not depends_on_field:
        return []
    result: list[int] = []
    for entry in depends_on_field:
        if isinstance(entry, int):
            result.append(entry)
        elif isinstance(entry, dict) and "id" in entry:
            result.append(int(entry["id"]))
    return result


def _load_secrets_toml(path: Path) -> dict[str, str]:
    """Lees URL-keys uit .streamlit/secrets.toml zonder de toml-lib hard te eisen.

    Streamlit zelf vereist `tomli`/`tomllib` al — vanaf Python 3.11 zit er een
    native `tomllib` in stdlib. We falen stil terug op een lege dict als het
    bestand er niet is, zodat het script in een schone dev-omgeving zonder
    secrets.toml ook werkt.
    """
    if not path.exists():
        return {}
    try:
        import tomllib
    except ModuleNotFoundError:
        return {}
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    return {k: v for k, v in data.items() if isinstance(v, str)}


def _resolve_urls(args: argparse.Namespace) -> tuple[str, str]:
    """Resolveer de Django- en agent-URL.

    Voorrangsvolgorde:
    1. Expliciete CLI-flag (--api-url / --agent-url) wint altijd.
    2. Met --prod lezen we HEROKU_API_BASE_URL en HEROKU_API_AGENT_URL.
       Als die niet gezet zijn (in env of .env), abort met een instructie
       hoe ze toe te voegen — beter dan stilletjes terugvallen op localhost.
    3. Anders: env API_BASE_URL > secrets.toml > localhost-default.
    """
    secrets = _load_secrets_toml(_REPO_ROOT / ".streamlit" / "secrets.toml")

    if args.prod:
        api_url = args.api_url or os.environ.get("HEROKU_API_BASE_URL")
        agent_url = args.agent_url or os.environ.get("HEROKU_API_AGENT_URL")
        if not api_url or not agent_url:
            ontbrekend = []
            if not api_url:
                ontbrekend.append("HEROKU_API_BASE_URL")
            if not agent_url:
                ontbrekend.append("HEROKU_API_AGENT_URL")
            raise SystemExit(
                "✗ --prod gevraagd, maar de volgende variabelen ontbreken: "
                f"{', '.join(ontbrekend)}.\n"
                f"  Voeg deze toe aan {_DOTENV_PATH}:\n"
                "    HEROKU_API_BASE_URL=https://<homiletiek>.herokuapp.com\n"
                "    HEROKU_API_AGENT_URL=https://<homiletiek-agent>.herokuapp.com"
            )
    else:
        api_url = (
            args.api_url
            or os.environ.get("API_BASE_URL")
            or secrets.get("API_BASE_URL")
            or _DEFAULT_API_BASE_URL
        )
        agent_url = (
            args.agent_url
            or os.environ.get("API_AGENT_URL")
            or secrets.get("API_AGENT_URL")
            or _DEFAULT_AGENT_URL
        )
    return api_url.rstrip("/"), agent_url.rstrip("/")


def _auth_headers(jwt: JwtHandler) -> dict[str, str]:
    """Standaard Authorization+Content-Type-headers; token wordt automatisch ververst."""
    return {
        "Authorization": f"Bearer {jwt.token}",
        "Content-Type": "application/json",
    }


def _get(url: str, jwt: JwtHandler, params: dict[str, Any] | None = None) -> Any:
    """GET met JWT en duidelijke foutmelding bij HTTP-fout."""
    response = requests.get(url, headers=_auth_headers(jwt), params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def _post(url: str, jwt: JwtHandler, data: dict[str, Any]) -> requests.Response:
    """POST met JWT; geeft de raw response terug zodat de aanroeper 409 kan onderscheiden."""
    return requests.post(url, headers=_auth_headers(jwt), json=data, timeout=30)


def _fetch_all_analysis_types(api_url: str, jwt: JwtHandler) -> list[dict[str, Any]]:
    """Haal alle AnalysisTypes op van de Django-backend.

    Probeert eerst /slim/ (snel, geen depth=3-recursie). Bij 404 valt
    het terug op de volledige endpoint — handig als het script tegen
    een backend draait waar de slim-action nog niet is uitgerold.
    """
    try:
        return _get(f"{api_url}{_ANALYSIS_TYPES_PATH}", jwt)
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            print(
                "  /slim/ niet beschikbaar op deze backend, "
                "val terug op /api/analysis-types/ (kan traag zijn)..."
            )
            return _get(f"{api_url}{_ANALYSIS_TYPES_FALLBACK_PATH}", jwt)
        raise


def _fetch_completed_type_ids(
    api_url: str, jwt: JwtHandler, sermon_id: int
) -> set[int]:
    """Set van AnalysisType-ids waarvoor al een (niet-soft-deleted) resultaat bestaat."""
    rows = _get(
        f"{api_url}{_ANALYSIS_RESULTS_PATH}",
        jwt,
        params={"sermon_analysis_id": sermon_id},
    )
    completed: set[int] = set()
    for row in rows:
        at = row.get("analysis_type")
        if isinstance(at, dict):
            completed.add(int(at["id"]))
        elif isinstance(at, int):
            completed.add(at)
    return completed


def _fetch_sermon_status(api_url: str, jwt: JwtHandler, sermon_id: int) -> str:
    """Lees `SermonAnalysis.status` ('draft' of 'error')."""
    data = _get(f"{api_url}{_SERMON_ANALYSES_PATH}{sermon_id}/", jwt)
    return str(data.get("status", "draft"))


def _result_exists(
    api_url: str, jwt: JwtHandler, sermon_id: int, type_id: int
) -> bool:
    """Bestaat er een actief AnalysisResult voor deze combinatie?"""
    rows = _get(
        f"{api_url}{_ANALYSIS_RESULTS_PATH}",
        jwt,
        params={"sermon_analysis_id": sermon_id, "analysis_type_id": type_id},
    )
    return bool(rows)


def _build_index(types: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Maak een lookup van id → AnalysisType-dict voor snelle dependency-resolutie."""
    return {int(at["id"]): at for at in types}


def _expand_with_deps(
    selected_ids: set[int],
    by_id: dict[int, dict[str, Any]],
) -> set[int]:
    """DFS-expand de selectie met alle transitieve dependencies.

    Preek/feedback-types zouden niet in de dependency-keten van een
    selecteerbare analyse mogen voorkomen. Komen ze toch tegen: harde fout,
    dan zit er iets mis in de DB-config en moet de gebruiker dat eerst
    oplossen voordat de batch betrouwbaar kan draaien.
    """
    expanded: set[int] = set()
    stack: list[int] = list(selected_ids)
    while stack:
        type_id = stack.pop()
        if type_id in expanded:
            continue
        expanded.add(type_id)
        at = by_id.get(type_id)
        if at is None:
            raise RuntimeError(
                f"Dependency met id={type_id} ontbreekt in /api/analysis-types/."
            )
        if _is_user_choice_required(at):
            raise RuntimeError(
                f"Dependency '{at['name']}' (id={type_id}) vereist gebruikersinput "
                f"en kan niet automatisch worden gedraaid."
            )
        for dep_id in _extract_dep_ids(at.get("depends_on")):
            if dep_id not in expanded:
                stack.append(dep_id)
    return expanded


def _topological_order(
    selected_ids: set[int],
    by_id: dict[int, dict[str, Any]],
) -> list[int]:
    """Kahn's algorithm; tiebreaker `order` voor stabiele volgorde tussen lagen."""
    in_degree: dict[int, int] = {tid: 0 for tid in selected_ids}
    edges_out: dict[int, list[int]] = defaultdict(list)
    for tid in selected_ids:
        for dep_id in _extract_dep_ids(by_id[tid].get("depends_on")):
            if dep_id in selected_ids:
                edges_out[dep_id].append(tid)
                in_degree[tid] += 1

    # Kahn met sorted-init zodat de uitvoervolgorde reproduceerbaar is en
    # zinvolle types (lager `order`) eerst komen binnen één laag.
    ready: deque[int] = deque(
        sorted(
            (tid for tid, deg in in_degree.items() if deg == 0),
            key=lambda t: (by_id[t].get("order", 0), by_id[t]["name"]),
        )
    )
    result: list[int] = []
    while ready:
        tid = ready.popleft()
        result.append(tid)
        # Nieuwe ready-kandidaten direct gesorteerd toevoegen, anders pikt
        # Kahn ze in willekeurige insertion-order op.
        nieuwe: list[int] = []
        for nxt in edges_out[tid]:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                nieuwe.append(nxt)
        for tid_new in sorted(
            nieuwe,
            key=lambda t: (by_id[t].get("order", 0), by_id[t]["name"]),
        ):
            ready.append(tid_new)

    if len(result) != len(selected_ids):
        cyclus = selected_ids - set(result)
        namen = ", ".join(by_id[t]["name"] for t in cyclus)
        raise RuntimeError(f"Cyclus in dependencies gedetecteerd: {namen}")
    return result


def _filter_selectable(types: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Lijst van AnalysisTypes die in het CLI-menu mogen verschijnen."""
    out: list[dict[str, Any]] = []
    for at in types:
        if _is_user_choice_required(at):
            continue
        if at["name"] in _INTERNAL_AUXILIARY_NAMES:
            continue
        out.append(at)
    return out


def _group_label(at: dict[str, Any]) -> str:
    """Lees de groep-naam veilig — kan dict, str of None zijn afhankelijk van depth."""
    grp = at.get("analysis_type_group")
    if isinstance(grp, dict):
        return str(grp.get("name", "Overig"))
    if isinstance(grp, str):
        return grp
    return "Overig"


# Vaste leesvolgorde voor groepen in het menu — komt overeen met de tabbladen
# in Streamlit. Onbekende groepen vallen onder "Overig".
_GROUP_ORDER: tuple[str, ...] = (
    "BaseAnalysis",
    "DeepeningAnalysis",
    "PerspectiveAnalysis",
    "PrayerAnalysis",
    "SermonOutlineAnalysis",  # bevat de niet-preek subset (illustraties, focus_en_functie, ...)
)

# Vriendelijke namen per groep voor het tabblad-label boven elke prompt.
# Onbekende groepen vallen terug op de DRF-naam.
_GROUP_DISPLAY_NAMES: dict[str, str] = {
    "BaseAnalysis": "Basis",
    "DeepeningAnalysis": "Verdieping",
    "PerspectiveAnalysis": "Perspectieven",
    "PrayerAnalysis": "Gebeden",
    "SermonOutlineAnalysis": "Preekschets-onderdelen",
}


def _group_items_in_display_order(
    selectable: list[dict[str, Any]],
) -> list[tuple[str, list[dict[str, Any]]]]:
    """Groepeer en sorteer voor het tabblad-overzicht; lege groepen vervallen.

    Terug-tuple is (DRF-groepnaam, gesorteerde items). De aanroeper kan met
    `_GROUP_DISPLAY_NAMES.get(name, name)` een vriendelijk label tonen.
    """
    by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for at in selectable:
        by_group[_group_label(at)].append(at)
    for grp in by_group.values():
        grp.sort(key=lambda a: (a.get("order", 0), a["name"]))

    geordend = [g for g in _GROUP_ORDER if g in by_group]
    overig = sorted(g for g in by_group if g not in _GROUP_ORDER)
    return [(g, by_group[g]) for g in (geordend + overig) if by_group[g]]


def _choices_for_items(
    items: list[dict[str, Any]],
    completed_ids: set[int],
    initially_checked_ids: set[int] | None = None,
) -> list[questionary.Choice]:
    """Bouw questionary.Choice-objecten voor één tabblad (groep).

    Bij `initially_checked_ids=None` (eerste bezoek) gebruiken we
    `_DEFAULT_CHECKED_NAMES` als initiële vinkjes. Bij een terugkeer naar
    een tabblad geeft de aanroeper de eerder gemaakte selectie mee zodat
    de toggles van de gebruiker bewaard blijven.
    """
    out: list[questionary.Choice] = []
    for at in items:
        label: str = at.get("front_end_name") or at["name"]
        is_done: bool = int(at["id"]) in completed_ids
        # Lijst van (style, text)-tuples i.p.v. HTML(), omdat questionary
        # 2.1.1 een HTML-object via str() rendert (waardoor de gebruiker
        # de Python-repr ziet i.p.v. opgemaakte tekst). Tuples worden door
        # prompt_toolkit direct als FormattedText opgepikt.
        if is_done:
            title: Any = [
                ("", f"{label} "),
                ("ansibrightgreen bold", "✓"),
                ("", " "),
                ("ansibrightblack italic", "al gedaan, wordt geskipt"),
            ]
        else:
            title = label
        if initially_checked_ids is not None:
            checked: bool = int(at["id"]) in initially_checked_ids
        else:
            # Default-aanvinken voor de core productie-set, maar nooit voor
            # reeds voltooide analyses (zou alleen visueel verwarren — ze
            # worden in de runner-loop toch geskipt).
            checked = at["name"] in _DEFAULT_CHECKED_NAMES and not is_done
        out.append(
            questionary.Choice(title=title, value=int(at["id"]), checked=checked)
        )
    return out


def _print_run_plan(
    order: list[int],
    by_id: dict[int, dict[str, Any]],
    completed_ids: set[int],
) -> None:
    """Print het uitgewerkte runplan voordat we (eventueel) gaan draaien."""
    print("\nRun-plan in topologische volgorde:")
    for idx, tid in enumerate(order, start=1):
        at = by_id[tid]
        marker = "→ skip" if tid in completed_ids else "▸ run "
        print(f"  {idx:2d}. {marker}  {at['name']}  (id={tid})")
    print()


def _run_one(
    agent_url: str,
    api_url: str,
    jwt: JwtHandler,
    sermon_id: int,
    at: dict[str, Any],
    pre_existing_error: bool,
) -> str:
    """Start één analyse, wacht tot resultaat of fout, retourneer status-string.

    Geeft 'completed', 'failed', of 'timeout' terug. `pre_existing_error`
    geeft aan dat SermonAnalysis.status al 'error' was bij start van het
    script — dan wordt de status-flip naar error niet gezien als een nieuwe
    failure (we vertrouwen alleen op result-existence + timeout).
    """
    type_id = int(at["id"])
    name: str = at["name"]

    # 1. Slot-acquire via POST /single_analysis/. Bij 409 is het slot al bezet
    #    door bv. een eerdere klik in Streamlit; korte retry-loop voordat we
    #    opgeven. Andere niet-200-statussen zijn fataal.
    payload = {"sermon_analysis_id": sermon_id, "analysis_type_id": type_id}
    started = False
    for poging in range(_SLOT_RETRY_MAX):
        resp = _post(f"{agent_url}{_SINGLE_ANALYSIS_PATH}", jwt, payload)
        if resp.status_code == 200:
            started = True
            break
        if resp.status_code == 409:
            print(
                f"   slot bezet voor '{name}', wacht {_SLOT_RETRY_DELAY_SECONDS}s "
                f"({poging + 1}/{_SLOT_RETRY_MAX})..."
            )
            sleep(_SLOT_RETRY_DELAY_SECONDS)
            continue
        # Andere status — print body en abort deze analyse.
        print(f"   POST /single_analysis/ gaf {resp.status_code}: {resp.text[:300]}")
        return "failed"
    if not started:
        print(f"   slot bleef bezet voor '{name}' na {_SLOT_RETRY_MAX} pogingen.")
        return "failed"

    # 2. Polling-loop. Resultaat-rij = klaar; status-flip naar error = mislukt.
    deadline = time() + _POLL_TIMEOUT_SECONDS
    while time() < deadline:
        sleep(_POLL_INTERVAL_SECONDS)
        if _result_exists(api_url, jwt, sermon_id, type_id):
            return "completed"
        if not pre_existing_error:
            current = _fetch_sermon_status(api_url, jwt, sermon_id)
            if current == "error":
                return "failed"
    return "timeout"


def _confirm_proceed(prompt: str) -> bool:
    """Y/N-prompt; default N zodat een lege enter veilig afbreekt."""
    antwoord = input(f"{prompt} [y/N]: ").strip().lower()
    return antwoord in {"y", "yes", "j", "ja"}


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch-runner voor analyses op één SermonAnalysis."
    )
    parser.add_argument(
        "--sermon-id",
        type=int,
        required=True,
        help="Id van de SermonAnalysis waarvoor analyses gedraaid moeten worden.",
    )
    parser.add_argument(
        "--username",
        default=None,
        help=(
            "Username voor login. Default: $HOMILETIEK_USERNAME, "
            "$API_USERNAME (.env) of prompt."
        ),
    )
    parser.add_argument(
        "--api-url",
        default=None,
        help="Base-URL van de Django-backend (default uit secrets/env/.env).",
    )
    parser.add_argument(
        "--agent-url",
        default=None,
        help="Base-URL van homiletiek_agent (default uit secrets/env/.env).",
    )
    parser.add_argument(
        "--prod",
        action="store_true",
        help=(
            "Praat met de Heroku-backends i.p.v. lokaal. Leest "
            "HEROKU_API_BASE_URL en HEROKU_API_AGENT_URL uit .env "
            "(of shell-env)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Toon alleen het run-plan; geen POSTs naar de agent.",
    )
    return parser.parse_args(argv)


class _LoginFailed(Exception):
    """Marker-exception voor login-mislukkingen met een eindgebruiker-melding."""


def _login(api_url: str, username: str | None) -> JwtHandler:
    """Vraag credentials zo nodig en log in tegen de Django-backend.

    Bij verkeerde credentials of een onjuiste backend-URL gooien we een
    `_LoginFailed` met een korte, nette melding — zonder de volledige
    requests-stacktrace die voor de gebruiker geen extra info bevat.
    """
    user: str = (
        username
        or os.environ.get("HOMILETIEK_USERNAME")
        # API_USERNAME / API_PASSWORD zijn de project-conventies in .env;
        # door ze hier ook te lezen kan het script zonder credential-prompt
        # draaien als de gebruiker ze al voor agent/Streamlit heeft gezet.
        or os.environ.get("API_USERNAME")
        or input("Username: ").strip()
    )
    wachtwoord: str = (
        os.environ.get("HOMILETIEK_PASSWORD")
        or os.environ.get("API_PASSWORD")
        or getpass.getpass("Password: ")
    )
    # JwtHandler.__init__ doet zelf de POST naar /api/token/, dus de 401-
    # HTTPError ontsnapt tijdens de constructor — niet pas bij `handler.token`.
    # Daarom wrappen we de constructie + token-fetch beide binnen dezelfde
    # try/except.
    try:
        handler = JwtHandler(
            username=user,
            password=wachtwoord,
            base_url=api_url,
            access_endpoint=_JWT_ACCESS_PATH,
            refresh_endpoint=_JWT_REFRESH_PATH,
        )
        # Trigger token-property zodat een eventuele lazy refresh hier ook valt.
        _ = handler.token
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        if status == 401:
            raise _LoginFailed(
                "Login mislukt (HTTP 401): gebruikersnaam of wachtwoord onjuist.\n"
                f"  Backend: {api_url}\n"
                "  Controleer of je tegen de juiste backend praat (lokaal vs Heroku) "
                "via --api-url, API_BASE_URL of HEROKU_API_BASE_URL met --prod."
            ) from exc
        raise _LoginFailed(
            f"Login mislukt (HTTP {status}) tegen {api_url}: {exc}"
        ) from exc
    except requests.RequestException as exc:
        raise _LoginFailed(
            f"Login mislukt — kon backend niet bereiken op {api_url}: {exc}"
        ) from exc
    return handler


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    api_url, agent_url = _resolve_urls(args)

    print(f"Django-backend: {api_url}")
    print(f"Agent-runtime : {agent_url}")
    print(f"SermonAnalysis: {args.sermon_id}")

    try:
        jwt = _login(api_url, args.username)
    except _LoginFailed as exc:
        # Schoon afsluiten met exit-code 1 i.p.v. een rauwe stacktrace; de
        # melding van _login bevat alle relevante hints (status + backend-URL).
        print(f"\n✗ {exc}")
        return 1

    # Initiële status — als deze al 'error' is, willen we niet dat de
    # poll-logica elke nieuwe analyse direct als 'failed' rapporteert.
    # 404 hier betekent typisch: sermon-id bestaat niet of hoort bij een
    # andere gebruiker (DRF-viewset filtert per-user). 403 = geen toegang.
    try:
        initial_status = _fetch_sermon_status(api_url, jwt, args.sermon_id)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        if status == 404:
            print(
                f"\n✗ SermonAnalysis met id={args.sermon_id} niet gevonden op {api_url}.\n"
                "  Mogelijke oorzaken:\n"
                "  - Het id bestaat niet.\n"
                "  - De sermon hoort bij een andere gebruiker (de API filtert per-user).\n"
                "  - Je praat tegen de verkeerde backend (lokaal vs Heroku — check --api-url / --prod)."
            )
            return 1
        if status == 403:
            print(
                f"\n✗ Geen toegang tot SermonAnalysis id={args.sermon_id} (HTTP 403).\n"
                "  Log in als de eigenaar van deze sermon."
            )
            return 1
        print(f"\n✗ Onverwachte fout bij ophalen sermon-status (HTTP {status}): {exc}")
        return 1
    except requests.RequestException as exc:
        print(f"\n✗ Backend niet bereikbaar voor sermon-status: {exc}")
        return 1
    pre_existing_error = initial_status == "error"
    if pre_existing_error:
        print(
            "\n⚠ SermonAnalysis staat al op status='error'. Failure-detectie via "
            "status wordt overgeslagen; alleen result-existence + timeout."
        )

    print("\nAnalysetypes ophalen...")
    try:
        types = _fetch_all_analysis_types(api_url, jwt)
    except requests.RequestException as exc:
        print(f"\n✗ Kon analysetypes niet ophalen: {exc}")
        return 1
    by_id = _build_index(types)

    print(f"Reeds voltooide analyses ophalen voor sermon {args.sermon_id}...")
    try:
        completed_ids = _fetch_completed_type_ids(api_url, jwt, args.sermon_id)
    except requests.RequestException as exc:
        print(f"\n✗ Kon voltooide analyses niet ophalen: {exc}")
        return 1
    print(f"  → {len(completed_ids)} reeds voltooid.")

    selectable = _filter_selectable(types)
    if not selectable:
        print("Geen selecteerbare analysetypes gevonden.")
        return 1

    grouped = _group_items_in_display_order(selectable)

    print(
        "\nKies analyses per tabblad:\n"
        "  spatie = aan/uit  ·  enter = bevestig dit tabblad  ·  ctrl-c = afbreken\n"
        "  [X] = wordt gedraaid  ·  [ ] = wordt overgeslagen\n"
        "Na elk tabblad kun je vooruit, terug, of afsluiten.\n"
        "Dependencies worden automatisch toegevoegd."
    )
    # Custom style. Reden per klasse:
    # - question     : de vraag bovenaan ('[1/5] Basis') vet zodat het
    #                  tabblad-label duidelijk afsteekt tegen de keuzes.
    # - selected     : ●-indicator (of '[X]' na monkey-patch) van een
    #                  aangevinkte keuze in helder groen+vet.
    # - pointer      : »-cursor in helder cyaan+vet.
    # - highlighted  : de hele regel waar de cursor op staat in
    #                  bright-yellow+vet voor unmistakable contrast.
    menu_style = questionary.Style(
        [
            ("question", "bold"),
            ("selected", "fg:ansibrightgreen bold"),
            ("pointer", "fg:ansibrightcyan bold"),
            ("highlighted", "fg:ansibrightyellow bold"),
        ]
    )

    # Per tabblad een aparte checkbox-prompt; selecties hoopt zich op per
    # tab-index in `selecties_per_tab` zodat de gebruiker met '← Vorige'
    # naar een eerder tabblad kan terugkeren zonder selecties te verliezen.
    # We gebruiken een while-loop met handmatig index-management i.p.v. een
    # for-loop omdat we vooruit én achteruit moeten kunnen springen.
    selecties_per_tab: dict[int, set[int]] = {}
    totaal = len(grouped)
    i = 0
    while i < totaal:
        groep_naam, items = grouped[i]
        pretty = _GROUP_DISPLAY_NAMES.get(groep_naam, groep_naam)
        # Bij eerste bezoek: defaults uit _DEFAULT_CHECKED_NAMES; bij
        # terugkeer: de keuzes die de gebruiker eerder maakte.
        pre_checked: set[int] | None = selecties_per_tab.get(i)
        choices = _choices_for_items(
            items,
            completed_ids,
            initially_checked_ids=pre_checked,
        )
        selectie = questionary.checkbox(
            f"[{i + 1}/{totaal}] {pretty}",
            choices=choices,
            style=menu_style,
        ).ask()
        if selectie is None:
            print("Afgebroken.")
            return 0
        selecties_per_tab[i] = {int(s) for s in selectie}

        # Eén tabblad → geen navigatie nodig.
        if totaal == 1:
            break

        # Nav-prompt met alleen relevante opties. 'Volgende' staat eerst
        # zodat een Enter-zonder-actie het meest voor de hand liggende
        # gedrag (forward) oplevert.
        totaal_aangevinkt = sum(len(v) for v in selecties_per_tab.values())
        nav_choices: list[questionary.Choice] = []
        if i < totaal - 1:
            nav_choices.append(
                questionary.Choice(title="→ Volgende tabblad", value="next")
            )
        if i > 0:
            nav_choices.append(
                questionary.Choice(title="← Vorige tabblad", value="prev")
            )
        nav_choices.append(
            questionary.Choice(
                title=f"✓ Klaar — gebruik huidige selecties ({totaal_aangevinkt} aangevinkt)",
                value="done",
            )
        )
        nav = questionary.select(
            f"Tabblad {i + 1}/{totaal} ({pretty}) — wat nu?",
            choices=nav_choices,
            style=menu_style,
        ).ask()
        if nav is None:
            print("Afgebroken.")
            return 0
        if nav == "next":
            i += 1
        elif nav == "prev":
            i -= 1
        else:  # "done"
            break

    selected_ids: set[int] = set()
    for ids in selecties_per_tab.values():
        selected_ids.update(ids)
    if not selected_ids:
        print("Geen selectie over alle tabbladen. Afgebroken.")
        return 0
    expanded = _expand_with_deps(selected_ids, by_id)

    # Interne auxiliary types kunnen via een dep-keten in `expanded` zitten —
    # niet zelf draaien, maar verifiëren dat ze er al zijn, anders abort.
    auxiliary_id_to_name: dict[int, str] = {
        int(at["id"]): at["name"]
        for at in types
        if at["name"] in _INTERNAL_AUXILIARY_NAMES
    }
    ontbrekend_aux: list[str] = []
    for aux_id, aux_name in auxiliary_id_to_name.items():
        if aux_id not in expanded:
            continue
        if aux_id in completed_ids:
            # Aanwezig — uit de te-draaien set halen; topologische sort
            # behandelt 'm dan als al-voltooid voorganger.
            expanded.discard(aux_id)
        else:
            ontbrekend_aux.append(aux_name)
    if ontbrekend_aux:
        print(
            f"\n✗ Interne dependencies ontbreken: {', '.join(sorted(ontbrekend_aux))}\n"
            "  Maak de SermonAnalysis opnieuw aan via Streamlit zodat "
            "deze automatisch worden gevuld (bijbelteksten en base-analyses)."
        )
        return 2

    extra: set[int] = expanded - selected_ids
    if extra:
        namen = ", ".join(sorted(by_id[t]["name"] for t in extra))
        print(f"\nDependencies toegevoegd: {namen}")

    order = _topological_order(expanded, by_id)
    _print_run_plan(order, by_id, completed_ids)

    if args.dry_run:
        print("--dry-run actief: geen POSTs uitgevoerd.")
        return 0

    if not _confirm_proceed("Doorgaan met draaien?"):
        print("Afgebroken.")
        return 0

    rapport: list[tuple[str, str]] = []
    for tid in order:
        at = by_id[tid]
        name = at["name"]
        if tid in completed_ids:
            print(f"→ skip   {name}  (al gedaan)")
            rapport.append((name, "skip"))
            continue
        print(f"▸ start  {name}  (id={tid})")
        status = _run_one(
            agent_url=agent_url,
            api_url=api_url,
            jwt=jwt,
            sermon_id=args.sermon_id,
            at=at,
            pre_existing_error=pre_existing_error,
        )
        rapport.append((name, status))
        if status == "completed":
            print(f"  ✓ klaar  {name}")
            completed_ids.add(tid)
        elif status == "failed":
            # Vervolg-analyses die op deze als dep leunen, kunnen niet
            # zinvol verder; aborteer de hele run en rapporteer.
            print(f"  ✗ failed {name}  — verdere analyses worden overgeslagen.")
            break
        else:  # timeout
            print(f"  ⏱ timeout {name}  — verdere analyses worden overgeslagen.")
            break

    print("\n=== Eindrapport ===")
    for name, status in rapport:
        symbol = {"completed": "✓", "skip": "→", "failed": "✗", "timeout": "⏱"}.get(
            status, "?"
        )
        print(f"  {symbol} {status:9s}  {name}")

    failed_or_timeout = any(s in {"failed", "timeout"} for _, s in rapport)
    return 1 if failed_or_timeout else 0


if __name__ == "__main__":
    sys.exit(main())
