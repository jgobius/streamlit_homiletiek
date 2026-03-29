#!/usr/bin/env python3
"""
Validatiescript voor gemeente- en dienstoperaties via de API.

Gebruik:
    python validate.py --username wmotte@gmail.com --password Wachtwoord1
    python validate.py --username wmotte@gmail.com --password Wachtwoord1 --keep
    python validate.py --username wmotte@gmail.com --password Wachtwoord1 --base-url http://localhost:8000
"""

import argparse
import sys
import tomllib
from pathlib import Path

import requests

from src.api.handler import APIHandler
from src.api.jwthandler import JwtHandler


# ── Helpers ───────────────────────────────────────────────────────────────────

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
SKIP = "\033[33mSKIP\033[0m"

results: list[tuple[str, bool]] = []


def check(label: str, condition: bool, detail: str = "") -> bool:
    tag = PASS if condition else FAIL
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{tag}] {label}{suffix}")
    results.append((label, condition))
    return condition


def expect_error(label: str, fn, expected_status: int) -> bool:
    try:
        fn()
        check(label, False, f"verwachtte HTTP {expected_status}, maar kreeg 2xx")
        return False
    except requests.exceptions.HTTPError as e:
        got = e.response.status_code
        ok = got == expected_status
        check(label, ok, f"HTTP {got}" if not ok else f"HTTP {got} zoals verwacht")
        return ok
    except Exception as e:
        check(label, False, str(e))
        return False


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


# ── Gemeente-tests ─────────────────────────────────────────────────────────────

def test_gemeenten(api: APIHandler, keep: bool) -> int | None:
    """Geeft het ID terug van de aangemaakte testgemeente (of None bij mislukking)."""

    print("\n── Gemeenten ────────────────────────────────────────────────────────")

    # 1. Lijst ophalen
    try:
        gemeenten = api.get("api/churches/")
        check("GET /api/churches/ geeft een lijst terug", isinstance(gemeenten, list))
    except Exception as e:
        check("GET /api/churches/ geeft een lijst terug", False, str(e))
        return None

    # 2. Geldige gemeente aanmaken
    church_id: int | None = None
    valid_payload = {
        "name": "__test_gemeente__",
        "place": "Testplaats",
        "website": "https://example.com",
        "denomination": "PKN",
        "modality": "confessioneel",
        "address": "Teststraat 1, 1234 AB Testplaats",
        "context": "Testgemeente aangemaakt door validate.py",
    }
    try:
        created = api.post("api/churches/", valid_payload)
        church_id = created.get("id")
        ok = church_id is not None
        check("POST geldige gemeente → aangemaakt", ok, f"id={church_id}")
    except Exception as e:
        check("POST geldige gemeente → aangemaakt", False, str(e))

    # 3. Gemeente terugvinden in lijst
    if church_id is not None:
        try:
            gemeenten2 = api.get("api/churches/")
            ids = [c["id"] for c in gemeenten2]
            check("Nieuwe gemeente zichtbaar in GET /api/churches/", church_id in ids)
        except Exception as e:
            check("Nieuwe gemeente zichtbaar in GET /api/churches/", False, str(e))

        # 4. Gemeente ophalen via detail-endpoint
        try:
            detail = api.get(f"api/churches/{church_id}/")
            check(
                "GET /api/churches/{id}/ geeft correcte naam terug",
                detail.get("name") == "__test_gemeente__",
            )
        except Exception as e:
            check("GET /api/churches/{id}/ geeft correcte naam terug", False, str(e))

    # 5. Aanmaken zonder 'name' → 400
    payload_no_name = {"place": "Testplaats", "website": "https://example.com"}
    expect_error(
        "POST gemeente zonder naam → HTTP 400",
        lambda: api.post("api/churches/", payload_no_name),
        expected_status=400,
    )

    # 6. Aanmaken zonder 'place' → 400
    payload_no_place = {"name": "__test__", "website": "https://example.com"}
    expect_error(
        "POST gemeente zonder plaats → HTTP 400",
        lambda: api.post("api/churches/", payload_no_place),
        expected_status=400,
    )

    # 7. Ongeldig denomination-code → 400
    payload_bad_denom = {
        "name": "__test__",
        "place": "Testplaats",
        "website": "https://example.com",
        "denomination": "ONBEKEND",
    }
    expect_error(
        "POST gemeente met ongeldige denominatie → HTTP 400",
        lambda: api.post("api/churches/", payload_bad_denom),
        expected_status=400,
    )

    # 8. Ongeldig modality-code → 400
    payload_bad_modality = {
        "name": "__test__",
        "place": "Testplaats",
        "website": "https://example.com",
        "modality": "ONBEKEND",
    }
    expect_error(
        "POST gemeente met ongeldige modaliteit → HTTP 400",
        lambda: api.post("api/churches/", payload_bad_modality),
        expected_status=400,
    )

    # 9. Opruimen
    if church_id is not None and not keep:
        try:
            api.delete(f"api/churches/{church_id}/")
            check(f"DELETE testgemeente id={church_id}", True)
        except Exception as e:
            check(f"DELETE testgemeente id={church_id}", False, str(e))
    elif church_id is not None:
        print(f"  [{SKIP}] DELETE testgemeente (--keep actief, id={church_id})")

    return church_id if keep else None


# ── Dienst-tests ──────────────────────────────────────────────────────────────

def test_diensten(api: APIHandler, church_id: int, keep: bool) -> None:

    print("\n── Diensten (preekanalyses) ──────────────────────────────────────────")

    # 1. Lijst ophalen
    try:
        analyses = api.get("api/sermon-analyses/")
        check("GET /api/sermon-analyses/ geeft een lijst terug", isinstance(analyses, list))
    except Exception as e:
        check("GET /api/sermon-analyses/ geeft een lijst terug", False, str(e))
        return

    # 2. Geldige analyse aanmaken (minimaal)
    analysis_id: int | None = None
    valid_payload = {
        "church": church_id,
        "sermon_date": "2099-01-01",
        "use_calendar": False,
        "scripture_json": [],
        "title": "__test_dienst__",
    }
    try:
        created = api.post("api/sermon-analyses/", valid_payload)
        analysis_id = created.get("id")
        ok = analysis_id is not None
        check("POST geldige dienst → aangemaakt", ok, f"id={analysis_id}")
    except Exception as e:
        check("POST geldige dienst → aangemaakt", False, str(e))

    # 3. Dienst terugvinden in lijst
    if analysis_id is not None:
        try:
            analyses2 = api.get("api/sermon-analyses/")
            ids = [a["id"] for a in analyses2]
            check("Nieuwe dienst zichtbaar in GET /api/sermon-analyses/", analysis_id in ids)
        except Exception as e:
            check("Nieuwe dienst zichtbaar in GET /api/sermon-analyses/", False, str(e))

        # 4. Detail ophalen
        try:
            detail = api.get(f"api/sermon-analyses/{analysis_id}/")
            check(
                "GET /api/sermon-analyses/{id}/ geeft correcte datum terug",
                detail.get("sermon_date") == "2099-01-01",
            )
            check(
                "Kerkgegevens zijn uitgebreid teruggegeven (denomination)",
                "denomination" in detail.get("church", {}),
            )
        except Exception as e:
            check("GET /api/sermon-analyses/{id}/ geeft correcte datum terug", False, str(e))

    # 5. Aanmaken zonder 'church' → 400
    payload_no_church = {"sermon_date": "2099-01-01", "use_calendar": False, "scripture_json": []}
    expect_error(
        "POST dienst zonder gemeente → HTTP 400",
        lambda: api.post("api/sermon-analyses/", payload_no_church),
        expected_status=400,
    )

    # 6. Aanmaken zonder 'sermon_date' → 400
    payload_no_date = {"church": church_id, "use_calendar": False, "scripture_json": []}
    expect_error(
        "POST dienst zonder datum → HTTP 400",
        lambda: api.post("api/sermon-analyses/", payload_no_date),
        expected_status=400,
    )

    # 7. Aanmaken met niet-bestaande church_id → 400
    expect_error(
        "POST dienst met niet-bestaande kerk-ID → HTTP 400",
        lambda: api.post("api/sermon-analyses/", {
            "church": 999999,
            "sermon_date": "2099-01-01",
            "use_calendar": False,
            "scripture_json": [],
        }),
        expected_status=400,
    )

    # 8. Aanmaken met ongeldige datumnotatie → 400
    expect_error(
        "POST dienst met ongeldige datum → HTTP 400",
        lambda: api.post("api/sermon-analyses/", {
            "church": church_id,
            "sermon_date": "niet-een-datum",
            "use_calendar": False,
            "scripture_json": [],
        }),
        expected_status=400,
    )

    # 9. Opruimen
    if analysis_id is not None and not keep:
        try:
            api.delete(f"api/sermon-analyses/{analysis_id}/")
            check(f"DELETE testdienst id={analysis_id}", True)
        except Exception as e:
            check(f"DELETE testdienst id={analysis_id}", False, str(e))
    elif analysis_id is not None:
        print(f"  [{SKIP}] DELETE testdienst (--keep actief, id={analysis_id})")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validatiescript voor gemeente- en dienstoperaties",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--username", required=True, help="API gebruikersnaam")
    parser.add_argument("--password", required=True, help="API wachtwoord")
    parser.add_argument("--base-url", default=None, help="API base URL (default: uit secrets.toml)")
    parser.add_argument("--church-id", type=int, default=None,
                        help="Gebruik een bestaande gemeente-ID voor diensttests (slaat gemeente-aanmaken over)")
    parser.add_argument("--keep", action="store_true",
                        help="Verwijder de aangemaakte testdata niet na afloop")
    args = parser.parse_args()

    base_url = args.base_url or load_base_url()

    # Login
    print(f"Inloggen op {base_url} ...")
    try:
        api = login(args.username, args.password, base_url)
        check("Login geslaagd", True)
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        check("Login geslaagd", False, f"HTTP {status}")
        sys.exit(1)
    except Exception as e:
        check("Login geslaagd", False, str(e))
        sys.exit(1)

    # Gemeente-tests
    if args.church_id:
        print(f"\n── Gemeenten ────────────────────────────────────────────────────────")
        print(f"  [{SKIP}] Gemeentetests overgeslagen (--church-id {args.church_id} opgegeven)")
        church_id_for_diensten = args.church_id
    else:
        created_church_id = test_gemeenten(api, keep=args.keep)
        # Voor dienst-tests hebben we altijd een gemeente nodig — haal eerste beschikbare op als --keep uitstaat
        if created_church_id is None:
            try:
                gemeenten = api.get("api/churches/")
                if gemeenten:
                    church_id_for_diensten = gemeenten[0]["id"]
                    print(f"\n  (Gebruik bestaande gemeente id={church_id_for_diensten} voor diensttests)")
                else:
                    print("\n  [!] Geen gemeente beschikbaar voor diensttests. Maak eerst een gemeente aan.")
                    church_id_for_diensten = None
            except Exception:
                church_id_for_diensten = None
        else:
            church_id_for_diensten = created_church_id

    # Dienst-tests
    if church_id_for_diensten is not None:
        test_diensten(api, church_id=church_id_for_diensten, keep=args.keep)
    else:
        print(f"\n── Diensten (preekanalyses) ──────────────────────────────────────────")
        print(f"  [{SKIP}] Diensttests overgeslagen (geen gemeente beschikbaar)")
        results.append(("Diensttests", False))

    # Samenvatting
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    failed = total - passed
    print(f"\n{'─' * 60}")
    print(f"Resultaat: {passed}/{total} geslaagd", end="")
    if failed:
        print(f"  (\033[31m{failed} mislukt\033[0m)")
    else:
        print(f"  (\033[32mall geslaagd\033[0m)")
    print()

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
