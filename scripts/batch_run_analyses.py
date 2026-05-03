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
import requests

# Maak imports vanuit de streamlit_homiletiek-repo werkend wanneer dit script
# wordt gedraaid als `python -m scripts.batch_run_analyses` (dan zit de repo
# al in sys.path) maar ook als `python scripts/batch_run_analyses.py`.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.api.jwthandler import JwtHandler  # noqa: E402

# Endpoints op de Django-backend voor het ophalen van analysetypes,
# bestaande resultaten en de status van de sermon zelf.
_ANALYSIS_TYPES_PATH: str = "/api/analysis-types/"
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

# 'bijbelteksten' wordt door /original_scriptures/ gevuld, niet door
# /single_analysis/. Voor een verse SermonAnalysis is dit altijd al
# gedaan — in deze CLI dus nooit zelf triggeren.
_BIJBELTEKSTEN_NAAM: str = "bijbelteksten"

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
        "base_analysis_creatief",
        "base_analysis_perspectief_creatief",
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
    """Resolveer de Django- en agent-URL met voorrang CLI > env > secrets > default."""
    secrets = _load_secrets_toml(_REPO_ROOT / ".streamlit" / "secrets.toml")

    api_url: str = (
        args.api_url
        or os.environ.get("API_BASE_URL")
        or secrets.get("API_BASE_URL")
        or _DEFAULT_API_BASE_URL
    )
    agent_url: str = (
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

    De viewset gebruikt geen pagination (geen DEFAULT_PAGINATION_CLASS), dus
    één call levert de volledige lijst.
    """
    return _get(f"{api_url}{_ANALYSIS_TYPES_PATH}", jwt)


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
        if at["name"] == _BIJBELTEKSTEN_NAAM:
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


def _build_menu_choices(
    selectable: list[dict[str, Any]],
    completed_ids: set[int],
) -> list[Any]:
    """Bouw de questionary.Choice-lijst gegroepeerd per AnalysisTypeGroup."""
    by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for at in selectable:
        by_group[_group_label(at)].append(at)

    # Sortering binnen een groep op `order`-veld zodat het menu dezelfde
    # volgorde gebruikt als Streamlit's tabbladen.
    for grp in by_group.values():
        grp.sort(key=lambda a: (a.get("order", 0), a["name"]))

    geordende_groepen: list[str] = [g for g in _GROUP_ORDER if g in by_group]
    voor_overige: list[str] = sorted(g for g in by_group if g not in _GROUP_ORDER)

    choices: list[Any] = []
    for grp_name in geordende_groepen + voor_overige:
        # Disabled separator-regel als visuele groephoofd; questionary slaat
        # die over bij selectie. Het bullet-teken zorgt dat de regel duidelijk
        # van een echte keuze afwijkt.
        choices.append(
            questionary.Separator(f"── {grp_name} ──")
        )
        for at in by_group[grp_name]:
            label = at.get("front_end_name") or at["name"]
            suffix = "  (✓ al gedaan, wordt geskipt)" if int(at["id"]) in completed_ids else ""
            # Default-aanvinken voor de core productie-set, maar nooit voor
            # analyses die al voltooid zijn (zou alleen visueel verwarren —
            # ze worden in de runner-loop toch geskipt).
            checked: bool = (
                at["name"] in _DEFAULT_CHECKED_NAMES
                and int(at["id"]) not in completed_ids
            )
            choices.append(
                questionary.Choice(
                    title=f"{label}  ·  {at['name']}{suffix}",
                    value=int(at["id"]),
                    checked=checked,
                )
            )
    return choices


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
        help="Username voor login. Default: $HOMILETIEK_USERNAME of prompt.",
    )
    parser.add_argument(
        "--api-url",
        default=None,
        help="Base-URL van de Django-backend (default uit secrets/env).",
    )
    parser.add_argument(
        "--agent-url",
        default=None,
        help="Base-URL van homiletiek_agent (default uit secrets/env).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Toon alleen het run-plan; geen POSTs naar de agent.",
    )
    return parser.parse_args(argv)


def _login(api_url: str, username: str | None) -> JwtHandler:
    """Vraag credentials zo nodig en log in tegen de Django-backend."""
    user: str = (
        username
        or os.environ.get("HOMILETIEK_USERNAME")
        or input("Username: ").strip()
    )
    wachtwoord: str = (
        os.environ.get("HOMILETIEK_PASSWORD") or getpass.getpass("Password: ")
    )
    handler = JwtHandler(
        username=user,
        password=wachtwoord,
        base_url=api_url,
        access_endpoint=_JWT_ACCESS_PATH,
        refresh_endpoint=_JWT_REFRESH_PATH,
    )
    # Trigger token-fetch direct zodat fout-credentials meteen falen i.p.v. pas
    # bij de eerste echte request.
    _ = handler.token
    return handler


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    api_url, agent_url = _resolve_urls(args)

    print(f"Django-backend: {api_url}")
    print(f"Agent-runtime : {agent_url}")
    print(f"SermonAnalysis: {args.sermon_id}")

    jwt = _login(api_url, args.username)

    # Initiële status — als deze al 'error' is, willen we niet dat de
    # poll-logica elke nieuwe analyse direct als 'failed' rapporteert.
    initial_status = _fetch_sermon_status(api_url, jwt, args.sermon_id)
    pre_existing_error = initial_status == "error"
    if pre_existing_error:
        print(
            "\n⚠ SermonAnalysis staat al op status='error'. Failure-detectie via "
            "status wordt overgeslagen; alleen result-existence + timeout."
        )

    print("\nAnalysetypes ophalen...")
    types = _fetch_all_analysis_types(api_url, jwt)
    by_id = _build_index(types)

    print(f"Reeds voltooide analyses ophalen voor sermon {args.sermon_id}...")
    completed_ids = _fetch_completed_type_ids(api_url, jwt, args.sermon_id)
    print(f"  → {len(completed_ids)} reeds voltooid.")

    selectable = _filter_selectable(types)
    if not selectable:
        print("Geen selecteerbare analysetypes gevonden.")
        return 1

    choices = _build_menu_choices(selectable, completed_ids)

    print(
        "\nKies analyses om te draaien (spatie = aan/uit, enter = bevestig, "
        "ctrl-c = afbreken).\nDependencies worden automatisch toegevoegd."
    )
    selectie = questionary.checkbox(
        "Welke analyses?",
        choices=choices,
    ).ask()
    if not selectie:
        print("Geen selectie. Afgebroken.")
        return 0

    selected_ids: set[int] = {int(s) for s in selectie}
    expanded = _expand_with_deps(selected_ids, by_id)

    # 'bijbelteksten' kan via een dep-keten in `expanded` zitten — niet zelf
    # draaien, maar verifiëren dat het er al is, anders abort.
    bijbelteksten_id: int | None = next(
        (int(at["id"]) for at in types if at["name"] == _BIJBELTEKSTEN_NAAM),
        None,
    )
    if bijbelteksten_id is not None and bijbelteksten_id in expanded:
        if bijbelteksten_id not in completed_ids:
            print(
                "\n✗ Dependency 'bijbelteksten' ontbreekt voor deze sermon. "
                "Draai eerst /original_scriptures/ via de Streamlit-UI."
            )
            return 2
        # Niet zelf opnieuw draaien — uit de te-draaien set halen, maar
        # wel als 'voltooid' markeren voor topologische sortering.
        expanded.discard(bijbelteksten_id)

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
