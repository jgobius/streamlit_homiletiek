#!/usr/bin/env python3

"""
CLI-script om nieuwe preekanalyses toe te voegen via de API.

Gebruik:
    # Toon beschikbare gemeentes, bijbelvertalingen en liedboeken:
    python add_analysis.py --username jan --password geheim list-options

    # Maak een nieuwe analyse (eigen lezingen):
    python add_analysis.py --username jan --password geheim create \
        --church-id 1 \
        --date 2026-04-05 \
        --scripture "Johannes 3:16-21" \
        --scripture "Psalm 23" \
        --bible-version-id 2 \
        --title "Paaspreek"

    # Met kerkelijk rooster:
    python add_analysis.py --username jan --password geheim create \
        --church-id 1 \
        --date 2026-04-05 \
        --use-calendar
"""

import argparse
import json
import sys
import tomllib
from datetime import date
from pathlib import Path

import requests

from src.api.handler import APIHandler
from src.api.jwthandler import JwtHandler


# ── Config ────────────────────────────────────────────────────────────────────

def load_base_url() -> str:
    secrets_path = Path(__file__).parent / ".streamlit" / "secrets.toml"
    with open(secrets_path, "rb") as f:
        secrets = tomllib.load(f)
    return secrets["API_BASE_URL"]


def login(username: str, password: str, base_url: str) -> APIHandler:
    jwt_handler = JwtHandler(
        username=username,
        password=password,
        base_url=base_url,
        access_endpoint="/api/token/",
        refresh_endpoint="/api/token/refresh/",
    )
    return APIHandler(base_url=base_url, jwt_handler=jwt_handler)


# ── Subcommands ────────────────────────────────────────────────────────────────

def cmd_list_options(api: APIHandler) -> None:
    churches = api.get("api/churches/")
    bible_versions = api.get("api/bible-versions/")
    song_books = api.get("api/song-books/")

    print("\n=== Kerkelijke gemeenten ===")
    for c in churches:
        print(f"  id={c['id']:>3}  {c['name']}")

    print("\n=== Bijbelvertalingen ===")
    for b in bible_versions:
        print(f"  id={b['id']:>3}  {b['version']}")

    print("\n=== Liedboeken ===")
    for s in song_books:
        print(f"  id={s['id']:>3}  {s['name']}")

    print()


def get_structured_scriptures(
    scriptures: list[str],
    bible_version: str | None,
    agent_url: str,
) -> list[dict]:
    results = []
    for scripture in scriptures:
        data = {
            "scripture_data": scripture,
            "bible_version": bible_version or "",
            "language": "nl",
        }
        response = requests.post(f"{agent_url}/structured_scripture/", json=data)
        if response.status_code == 200:
            results.append(response.json())
        else:
            print(f"  [!] Kon lezing '{scripture}' niet ophalen: {response.text}", file=sys.stderr)
    return results


def cmd_delete_results(api: APIHandler, args: argparse.Namespace) -> None:
    results = api.get("api/analysis-results/", params={"sermon_analysis_id": args.analysis_id})
    if not results:
        print(f"Geen analyseresultaten gevonden voor analyse id={args.analysis_id}.")
        return
    for r in results:
        api.delete(f"api/analysis-results/{r['id']}/")
        print(f"  Verwijderd: id={r['id']}  type={r['analysis_type']['name']}")
    print(f"\n{len(results)} resultaten verwijderd.")


def cmd_create(api: APIHandler, agent_url: str, args: argparse.Namespace) -> None:
    sermon_date = date.fromisoformat(args.date)

    structured_scriptures: list[dict] = []
    liturgy_id: int | None = None

    if args.use_calendar:
        liturgy = api.get("api/liturgy/")
        matches = [l for l in liturgy if l.get("date") == sermon_date.isoformat()]
        if not matches:
            print(f"[!] Geen roosterlezingen gevonden voor {args.date}.", file=sys.stderr)
            sys.exit(1)
        liturgy_id = matches[0]["id"]
        print(f"Roosterlezing gevonden: id={liturgy_id}")
    else:
        if not args.scripture:
            print("[!] Geef minimaal één --scripture op, of gebruik --use-calendar.", file=sys.stderr)
            sys.exit(1)

        bible_version_name: str | None = None
        if args.bible_version_id:
            bible_versions = api.get("api/bible-versions/")
            match = next((b for b in bible_versions if b["id"] == args.bible_version_id), None)
            if match:
                bible_version_name = match["version"]
            else:
                print(f"[!] Bijbelvertaling id={args.bible_version_id} niet gevonden.", file=sys.stderr)
                sys.exit(1)

        print(f"Lezingen ophalen voor: {args.scripture} ...")
        structured_scriptures = get_structured_scriptures(
            scriptures=args.scripture,
            bible_version=bible_version_name,
            agent_url=agent_url,
        )
        if not structured_scriptures:
            print("[!] Geen lezingen opgehaald. Controleer de lezingen en de agent-URL.", file=sys.stderr)
            sys.exit(1)

    data = {
        "church": args.church_id,
        "title": args.title or None,
        "sermon_date": sermon_date.isoformat(),
        "liturgy": liturgy_id,
        "core_scriptures": args.core_scripture or None,
        "scripture_json": structured_scriptures,
        "use_calendar": args.use_calendar,
        "song_books": args.song_book_ids or [],
        "bible_version": args.bible_version_id or None,
        "extra_context": args.extra_context or None,
    }

    print("\nVersturen naar API...")
    result = api.post(endpoint="api/sermon-analyses/", data=data)
    print(f"\nAnalyse aangemaakt:")
    print(f"  id     : {result.get('id')}")
    print(f"  status : {result.get('status')}")
    print(f"  datum  : {result.get('sermon_date')}")
    print(f"  titel  : {result.get('title') or '(geen)'}")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="CLI voor het aanmaken van preekanalyses",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--username", required=True, help="API gebruikersnaam")
    parser.add_argument("--password", required=True, help="API wachtwoord")
    parser.add_argument("--base-url", default=None, help="API base URL (default: uit secrets.toml)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # list-options
    subparsers.add_parser("list-options", help="Toon beschikbare gemeentes, bijbelvertalingen en liedboeken")

    # delete-results
    del_r = subparsers.add_parser("delete-results", help="Verwijder alle analyseresultaten voor een analyse")
    del_r.add_argument("--analysis-id", type=int, required=True, help="ID van de preekanalyse")

    # create
    create = subparsers.add_parser("create", help="Maak een nieuwe preekanalyse")
    create.add_argument("--church-id", type=int, required=True, help="ID van de gemeente")
    create.add_argument("--date", required=True, help="Preekdatum (YYYY-MM-DD)")
    create.add_argument("--scripture", action="append", metavar="LEZING",
                        help="Schriftlezing, bijv. 'Johannes 3:16'. Herhaal voor meerdere lezingen.")
    create.add_argument("--use-calendar", action="store_true",
                        help="Gebruik kerkelijk rooster in plaats van eigen lezingen")
    create.add_argument("--title", default=None, help="Thema/titel (optioneel)")
    create.add_argument("--core-scripture", default=None, help="Kernlezing (optioneel)")
    create.add_argument("--bible-version-id", type=int, default=None, help="ID van de bijbelvertaling (optioneel)")
    create.add_argument("--song-book-ids", type=int, nargs="+", metavar="ID",
                        help="IDs van liedboeken, bijv. --song-book-ids 1 3 (optioneel)")
    create.add_argument("--extra-context", default=None, help="Extra context (optioneel)")

    args = parser.parse_args()

    base_url = args.base_url or load_base_url()

    # Lees agent URL uit secrets voor structured scripture
    secrets_path = Path(__file__).parent / ".streamlit" / "secrets.toml"
    with open(secrets_path, "rb") as f:
        secrets = tomllib.load(f)
    agent_url = secrets.get("API_AGENT_URL", base_url).rstrip("/")

    try:
        print(f"Inloggen op {base_url} ...")
        api = login(args.username, args.password, base_url)
        print("Ingelogd.\n")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("[!] Ongeldige gebruikersnaam of wachtwoord.", file=sys.stderr)
        else:
            print(f"[!] Inloggen mislukt: {e}", file=sys.stderr)
        sys.exit(1)

    if args.command == "list-options":
        cmd_list_options(api)
    elif args.command == "delete-results":
        cmd_delete_results(api, args)
    elif args.command == "create":
        cmd_create(api, agent_url, args)


if __name__ == "__main__":
    main()
