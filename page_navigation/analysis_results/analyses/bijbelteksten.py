from typing import Any

import streamlit as st

from src.utils.utils import (
    format_verse_range,
    groepeer_samengevoegde_verzen,
    render_verse_layout,
)


def _is_hebrew(text: str) -> bool:
    return any("֐" <= ch <= "׿" for ch in text)


def _verzamel_bron_paren(
    nummers: list[Any], verses: list[dict[str, Any]]
) -> list[tuple[str, Any]]:
    """Verzamel unieke (source_text, source_ref_id)-paren voor de gegeven
    Dutch-versnummers, in voorkomvolgorde.

    Wanneer meerdere Dutch-verzen samen in één groep zitten (bv. BGT v13-14
    met identieke modern_text maar verschillende Hebreeuws — MT v13 +
    MT v14 — sinds we via `modern_verse_reference` correct mappen),
    levert dit alle bronregels die onder de gedeelde Dutch-tekst horen.
    Lege source_texts worden gefilterd. Dedup vindt plaats op de
    combinatie (text, ref_id) zodat een gedeelde BHS-rij die in
    opeenvolgende verzen voorkomt slechts één keer wordt teruggegeven.
    """
    paren: list[tuple[str, Any]] = []
    gezien: set[tuple[str, Any]] = set()
    for n in nummers:
        v = next(
            (v for v in verses if isinstance(v, dict) and v.get("number") == n),
            None,
        )
        if v is None:
            continue
        src = (v.get("source_text") or "").strip()
        if not src:
            continue
        sleutel = (src, v.get("source_ref_id"))
        if sleutel in gezien:
            continue
        gezien.add(sleutel)
        paren.append(sleutel)
    return paren


def _cluster_op_source_ref(
    groepen: list[dict[str, Any]],
    verses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Voeg opeenvolgende groepen met dezelfde BHS-`source_ref_id` samen tot
    één super-cluster.

    Achtergrond: voor psalmen met opschrift kan een mapping in
    `modern_verse_reference` meerdere Dutch-verzen aan dezelfde BHS-rij
    koppelen (bv. BGT v1 = "opschrift" + BGT v2 = eerste content-regel,
    beide naar BHS v1 dat opschrift+v2 fuseert). De agent levert dan voor
    élk Dutch-vers dezelfde `source_text` aan, maar verschillende
    `modern_text`.

    Hier doen we de tweede pas: bij gelijke `source_ref_id` plaatsen we
    de Dutch-fragmenten als sub-groep onder één Hebreeuws blok.
    Defensief: clustering gebeurt alleen wanneer alle betrokken Dutch-
    verzen dezelfde niet-lege `source_ref_id` hebben — anders blijft
    elke groep een eigen super-cluster (oude weergave).

    Output-shape per super-cluster:
        {
            "sub_groepen": [groep, ...],
            "bron_paren": [(source_text, source_ref_id), ...],
        }

    `bron_paren` kan meer dan één item bevatten wanneer een groep zelf
    meerdere versnummers met *verschillende* bron-rijen omvat (BGT v13-14
    in Ps 65: identieke Dutch-tekst, twee aparte BHS-rijen voor MT v13
    en MT v14). De renderer toont die regels onder elkaar onder de
    gedeelde Dutch-tekst.
    """
    ref_per_nummer: dict[Any, Any] = {}
    for v in verses:
        if not isinstance(v, dict):
            continue
        ref_per_nummer[v.get("number")] = v.get("source_ref_id")

    super_clusters: list[dict[str, Any]] = []
    for groep in groepen:
        nummers = groep.get("numbers") or []
        ref_ids = {ref_per_nummer.get(n) for n in nummers}
        # Een groep met identieke modern_text kan ofwel één gedeelde
        # bron-rij hebben (Case A: opschrift+content fusie) of meerdere
        # (Case B: BGT v13-14 met verschillende MT-bronrijen). Alleen
        # Case A komt in aanmerking voor super-cluster-merging met de
        # voorgaande groep.
        gedeelde_ref = ref_ids.pop() if len(ref_ids) == 1 else None
        bron_paren = _verzamel_bron_paren(nummers, verses)

        if (
            super_clusters
            and gedeelde_ref is not None
            and len(super_clusters[-1]["bron_paren"]) == 1
            and super_clusters[-1]["bron_paren"][0][1] == gedeelde_ref
            and super_clusters[-1]["bron_paren"][0][1] is not None
        ):
            super_clusters[-1]["sub_groepen"].append(groep)
            continue

        super_clusters.append(
            {
                "sub_groepen": [groep],
                "bron_paren": bron_paren,
            }
        )
    return super_clusters


def _spreid_source_text(verses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Geef lege source_text-verzen de brontekst van een buur met identieke
    modern_text. Bedoeld als UI-vangnet voor samengevoegde verzen.

    De agent doet deze spreid al in `_match_verses` (homiletiek_agent), maar
    bestaande `scripture_json`-records die vóór die fix zijn opgeslagen
    hebben de oude shape (één van de twee samengevoegde verzen heeft een
    lege source_text). Zonder deze stap zou `groepeer_samengevoegde_verzen`
    v13 (gevuld) en v14 (leeg) als 'verschillend' beschouwen en niet
    samenvouwen, en zou de prediker dezelfde modern_text twee keer onder
    elkaar zien.

    Spreid alleen wanneer:
    - opeenvolgende verzen identieke modern_text hebben, én
    - één van de bronteksten leeg is en de andere gevuld.

    De spread loopt zowel voor- als achterwaarts zodat het niet uitmaakt
    of het gevulde vers links of rechts van het lege staat. We muteren
    een kopie van de input zodat downstream-data niet wijzigt.
    """
    schoon = [dict(v) if isinstance(v, dict) else v for v in verses]

    def _bron(v: dict[str, Any]) -> str:
        return (v.get("source_text") or "").strip()

    def _modern(v: dict[str, Any]) -> str:
        return (v.get("modern_text") or "").rstrip()

    # Forward: vul een leeg vers met de brontekst van de vorige.
    for i in range(1, len(schoon)):
        cur, prev = schoon[i], schoon[i - 1]
        if (
            isinstance(cur, dict) and isinstance(prev, dict)
            and _modern(cur) and _modern(cur) == _modern(prev)
            and not _bron(cur) and _bron(prev)
        ):
            cur["source_text"] = prev["source_text"]
    # Backward: vul een leeg vers met de brontekst van de volgende.
    for i in range(len(schoon) - 2, -1, -1):
        cur, nxt = schoon[i], schoon[i + 1]
        if (
            isinstance(cur, dict) and isinstance(nxt, dict)
            and _modern(cur) and _modern(cur) == _modern(nxt)
            and not _bron(cur) and _bron(nxt)
        ):
            cur["source_text"] = nxt["source_text"]
    return schoon


def bijbelteksten(analysis: dict[str, Any]) -> None:
    """Render bijbelteksten analysis result."""
    result: Any = analysis.get("result")

    # Titel, actieknoppen én de afsluitende scheidingslijn worden centraal in
    # overview.py getoond, zodat alle tabs dezelfde kop hebben
    # (titel → actieknoppen → lijn → inhoud). Deze renderer begint daarom
    # direct met de eigen inhoud.

    # `result` is een lijst van lezing-entries in liturgische leesvolgorde
    # (eerste lezing → psalm → tweede lezing → evangelie). Elke entry heeft
    # een 'reference'-veld met de originele referentie. We gebruiken een
    # lijst in plaats van een dict-op-referentie omdat Postgres jsonb
    # object-key-volgorde niet bewaart, maar list-volgorde wél.
    if not isinstance(result, list):
        st.info("Nog geen bijbeltekst beschikbaar.")
        return

    for scripture in result:
        if not isinstance(scripture, dict):
            continue
        scripture_ref = (scripture.get("reference") or "").rstrip(".").strip()
        st.subheader(scripture_ref)
        verses: list[dict] = scripture.get("verses", [])

        # Eerst lege bronteksten over consecutieve identieke modern_text-
        # verzen heen aanvullen (UI-vangnet voor scripture_json-records
        # die vóór de agent-spread-fix zijn opgeslagen). Daarna pas
        # samenvouwen — anders zou de groepering nog steeds een lege
        # vs. gevulde source_text als 'verschillend' zien.
        verses = _spreid_source_text(verses)

        # Groepeer alleen op modern_text. Verzen met identieke Dutch-tekst
        # maar verschillende brontekst (BGT v13-14 in Ps 65: één Dutch-
        # blok, maar MT v13 én MT v14 als aparte Hebreeuwse regels via
        # de modern_verse_reference-mapping) horen visueel onder één
        # Dutch-regel met de twee bronregels onder elkaar — niet als
        # twee aparte blokken met dezelfde Dutch eronder. De voorganger
        # van deze code gebruikte text_fields=("modern_text", "source_text")
        # waardoor zo'n geval splitste; nu loopt het via
        # `_cluster_op_source_ref` + `bron_paren`.
        groepen = groepeer_samengevoegde_verzen(
            verses, text_fields=("modern_text",)
        )
        # Tweede pas: cluster opeenvolgende groepen die naar dezelfde
        # BHS-`verse_reference` wijzen (zelfde `source_ref_id`). Dit
        # voorkomt dat — wanneer Dutch-versie (BGT/HSV) een opschrift-
        # vers en een content-vers naar dezelfde BHS-rij mapt — de
        # prediker dezelfde lange Hebreeuwse regel twee keer achter
        # elkaar ziet. Voor NBV21 (waar het opschrift al is weggelaten)
        # is dit een no-op; voor oude `scripture_json`-records zonder
        # `source_ref_id` ook.
        super_clusters = _cluster_op_source_ref(groepen, verses)

        for cluster in super_clusters:
            sub_groepen = cluster["sub_groepen"]
            for groep in sub_groepen:
                label = format_verse_range(groep["numbers"])
                # `modern_text` voor weergave: rstrip houdt leading whitespace
                # intact — de Naardense Bijbel gebruikt dat als poëtische
                # inspringing. De helper deed hierboven `.strip()` alleen voor
                # de identiteits-vergelijking, niet voor de waarde zelf.
                modern_text = (groep["modern_text"] or "").rstrip()

                st.markdown(
                    f"<span style='color:grey;font-size:0.85em;font-weight:bold;'>{label}</span>"
                    f"&nbsp;&nbsp;{render_verse_layout(modern_text)}",
                    unsafe_allow_html=True,
                )

            # Eén Hebreeuws/bron-blok per unieke bron-regel in het
            # cluster. Bij Case A (opschrift+content delen één BHS-rij)
            # is dat één regel; bij Case B (BGT v13-14 met aparte
            # MT v13 + MT v14 mappings) zijn het er twee onder elkaar.
            for source_text, _ in cluster["bron_paren"]:
                is_heb = _is_hebrew(source_text)
                direction = "rtl" if is_heb else "ltr"
                align = "right" if is_heb else "left"
                st.markdown(
                    f"<p style='color:#888;font-size:0.8em;font-style:italic;"
                    f"direction:{direction};text-align:{align};margin-top:2px;'>"
                    f"{source_text}</p>",
                    unsafe_allow_html=True,
                )

        st.write("")
