"""Export van één kerkdienstanalyse naar een Word-document.

Pure module zonder Streamlit-afhankelijkheden: alle UI-feedback (progressbar
e.d.) loopt via een optionele callback die de aanroeper meegeeft. Zo blijft
de documentgeneratie los te testen en te hergebruiken buiten een Streamlit-
context.

Gebruik:

    from src.utils.word_export import bouw_kerkdienstanalyse_docx
    bytes_out, bestandsnaam = bouw_kerkdienstanalyse_docx(
        analysis_id, api_handler,
        voortgang_callback=lambda f, t: print(f"{f:.0%} {t}"),
    )
"""
import io
import re
from datetime import datetime
from typing import Any, Callable
from zoneinfo import ZoneInfo

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt

from src.api.handler import APIHandler
from src.utils.analyse_tabs import TAB_NAAR_ANALYSES, TAB_VOLGORDE

# Signature voor de optionele voortgangs-callback. De aanroeper ontvangt een
# fractie (0.0 - 1.0) en een korte Nederlandse statusregel.
VoortgangCallback = Callable[[float, str], None]

# Backend-timestamps komen in UTC binnen; we tonen ze in Nederlandse tijd
# (DST-aware via zoneinfo), identiek aan dashboard.py.
_DISPLAY_TZ = ZoneInfo("Europe/Amsterdam")

# Sleutels die we bij een list-of-dicts gebruiken als subheading. Volgorde =
# prioriteit; de eerst-gematchte aanwezige sleutel wint.
_SUBHEADING_KEYS: tuple[str, ...] = (
    "titel",
    "title",
    "naam",
    "name",
    "reference",
    "heading",
    "label",
)

# Maximaal toegestaan heading-niveau in python-docx is theoretisch 9, maar
# alles boven 5 oogt scheef in Word; we cappen daarom op 5.
_MAX_HEADING_LEVEL = 5

# Drempel voor inline-vs-block rendering van string-waarden in een dict. Onder
# deze lengte (en zonder newlines) tonen we 'Sleutel: korte waarde' inline;
# daarboven krijgt de sleutel een subheading en wordt de tekst als losse
# paragraphs gerenderd (zodat meerregelige analyse-output leesbaar blijft).
_INLINE_STRING_MAX = 120

# Scheidingsteken voor paragraph-splitting binnen één string-waarde: elke
# reeks van ≥ 1 blank line telt als nieuwe alinea.
_BLANK_LINE_RE = re.compile(r"\n\s*\n")

# Regex voor _humanize_key: vervangt snake_case-underscores en niet-
# woordkarakters door een enkele spatie.
_WORD_SEP_RE = re.compile(r"[_\W]+")


def bouw_kerkdienstanalyse_docx(
    analysis_id: int,
    api_handler: APIHandler,
    voortgang_callback: VoortgangCallback | None = None,
) -> tuple[bytes, str]:
    """Bouwt een .docx met alle voltooide sub-analyses van één kerkdienstanalyse.

    Args:
        analysis_id: ID van de kerkdienstanalyse (SermonAnalysis in de backend).
        api_handler: Centrale APIHandler-instantie uit session_state.
        voortgang_callback: Optionele callback die bij elke stap wordt
            aangeroepen met (fractie 0.0-1.0, status-tekst in NL). Zo kan de
            UI een progressbar laten meelopen zonder dat deze module
            Streamlit hoeft te importeren.

    Returns:
        (bytes, bestandsnaam) — de ruwe .docx-bytes en een voorgestelde
        bestandsnaam gebaseerd op gemeente en zondagdatum.
    """
    # No-op callback zodat we verderop niet steeds op None hoeven te checken.
    cb: VoortgangCallback = voortgang_callback or (lambda f, t: None)

    cb(0.00, "Metadata ophalen...")
    sermon = api_handler.get(f"api/sermon-analyses/{analysis_id}/")

    cb(0.05, "Sub-analyses ophalen...")
    sub_raw = api_handler.get(
        "api/analysis-results",
        params={"sermon_analysis_id": analysis_id},
    )
    sub_analyses = _lijst_normaliseren(sub_raw)

    cb(0.15, "Document opbouwen — kop...")
    doc = Document()
    # Forceer Word om velden (TOC, paginanummers) bij openen automatisch
    # bij te werken; anders moet de lezer handmatig F9 drukken.
    _enable_auto_update_fields(doc)
    # Footer met "Pagina X van Y", gecentreerd. Moet vóór de content, want
    # de footer geldt voor alle pagina's van de huidige sectie.
    _voeg_paginanummers_toe(doc)
    _render_kop(doc, sermon)
    # Klikbare inhoudsopgave (tab-koppen + analyse-namen = niveau 1-2).
    # Komt direct onder de kop zodat de lezer meteen kan navigeren; daarna
    # een page break zodat de eerste inhoudelijke tab op een nieuwe pagina
    # begint.
    _render_inhoudsopgave(doc)
    doc.add_page_break()

    gegroepeerd = _groepeer_per_tab(sub_analyses)

    # Voortgang tijdens de per-analyse loop: lineair verdeeld over het
    # interval [0.20, 0.95]. Bij 0 analyses slaan we het interval simpelweg
    # over (max(...,1) voorkomt deling door 0).
    n_totaal = sum(len(lijst) for lijst in gegroepeerd.values())
    fractie_base = 0.20
    fractie_stap = (0.95 - fractie_base) / max(n_totaal, 1)

    # Volgorde: eerst de bekende tabs (TAB_VOLGORDE), daarna 'Overig' voor
    # analyse-types die nog niet in de mapping staan (toekomstbestendig).
    tabs_in_volgorde: list[str] = list(TAB_VOLGORDE) + ["Overig"]
    i_globaal = 0
    for tab in tabs_in_volgorde:
        lijst = gegroepeerd.get(tab, [])
        if not lijst:
            continue
        doc.add_heading(tab, level=1)
        for sub in lijst:
            front_name = _front_end_name(sub)
            cb(
                fractie_base + i_globaal * fractie_stap,
                f"Bezig met {front_name} ({i_globaal + 1}/{n_totaal})...",
            )
            _render_analyse(doc, sub)
            i_globaal += 1

    if n_totaal == 0:
        # Edge case: kerkdienstanalyse zonder enige sub-analyse. We leveren
        # nog steeds een document met de kop + expliciete melding, zodat de
        # gebruiker niet voor een onverklaarbaar lege file staat.
        doc.add_paragraph(
            "Er zijn nog geen sub-analyses om te exporteren voor deze "
            "kerkdienstanalyse."
        )

    cb(0.98, "Document opslaan...")
    buffer = io.BytesIO()
    doc.save(buffer)
    bytes_out = buffer.getvalue()

    cb(1.00, "Klaar!")
    return bytes_out, _bestandsnaam(sermon)


# ---------------------------------------------------------------------------
# Datafetch-helpers
# ---------------------------------------------------------------------------


def _lijst_normaliseren(respons: Any) -> list[dict]:
    """Normaliseert de API-respons naar een gewone list[dict].

    Django REST Framework kan bij paginatie een wrapper-dict leveren met
    sleutel 'results'; in andere gevallen komt er direct een list terug.
    Deze helper maakt er altijd een list van zodat de rest van de module
    uniform kan werken.
    """
    if isinstance(respons, list):
        return respons
    if isinstance(respons, dict) and isinstance(respons.get("results"), list):
        return respons["results"]
    return []


def _groepeer_per_tab(sub_analyses: list[dict]) -> dict[str, list[dict]]:
    """Verdeelt sub-analyses over de zes tabs + een 'Overig'-bak.

    Onbekende analyse-namen belanden in 'Overig' zodat we geen data
    verliezen wanneer er later in de backend een type bijkomt dat hier nog
    niet in de mapping zit. Binnen elke tab sorteren we op het `order`-veld
    van het analyse-type; bij afwezigheid vallen we terug op 99 zodat de
    onbekende types achteraan in de tab komen.
    """
    result: dict[str, list[dict]] = {tab: [] for tab in TAB_VOLGORDE}
    result["Overig"] = []

    for sub in sub_analyses:
        name = sub.get("analysis_type", {}).get("name", "")
        gevonden = False
        for tab in TAB_VOLGORDE:
            if name in TAB_NAAR_ANALYSES[tab]:
                result[tab].append(sub)
                gevonden = True
                break
        if not gevonden:
            result["Overig"].append(sub)

    for lijst in result.values():
        lijst.sort(key=lambda s: s.get("analysis_type", {}).get("order", 99))

    return result


def _front_end_name(sub: dict) -> str:
    at = sub.get("analysis_type") or {}
    return (
        at.get("front_end_name")
        or _humanize_key(at.get("name", ""))
        or "Onbekende analyse"
    )


# ---------------------------------------------------------------------------
# Rendering: kop + per analyse
# ---------------------------------------------------------------------------


def _render_kop(doc, sermon: dict) -> None:
    """Rendert titel + metadata bovenaan het document."""
    doc.add_heading(_kop_titel(sermon), level=0)

    gemeente = (sermon.get("church") or {}).get("name", "")
    sermon_date_iso = sermon.get("sermon_date", "")
    aanmaak = _format_aanmaak_label(sermon.get("created_at"))

    if gemeente:
        _metadata_regel(doc, "Gemeente", gemeente)
    if sermon_date_iso:
        _metadata_regel(doc, "Zondagdatum", _format_sermon_date(sermon_date_iso))
    if aanmaak:
        _metadata_regel(doc, "Aangemaakt", aanmaak)

    # Witregel tussen kop en eerste tabblad.
    doc.add_paragraph()


def _metadata_regel(doc, label: str, waarde: str) -> None:
    p = doc.add_paragraph()
    p.add_run(f"{label}: ").bold = True
    p.add_run(waarde)


def _kop_titel(sermon: dict) -> str:
    """Kopt op basis van de title van de analyse; valt terug op gemeente+datum."""
    titel = (sermon.get("title") or "").strip()
    if titel:
        return titel
    gemeente = (sermon.get("church") or {}).get("name", "")
    sermon_date = _format_sermon_date(sermon.get("sermon_date", ""))
    return f"{gemeente} — {sermon_date}".strip(" —")


def _format_sermon_date(iso_datum: str) -> str:
    # Zondagdatum komt in 'YYYY-MM-DD'-formaat van de API.
    try:
        return datetime.strptime(iso_datum, "%Y-%m-%d").strftime("%d-%m-%Y")
    except ValueError:
        return iso_datum


def _format_aanmaak_label(created_at: str | None) -> str | None:
    """Converteert ISO-8601 UTC-timestamp naar 'dd-mm-yyyy HH:MM' in NL-tijd.

    Retourneert None wanneer het veld ontbreekt of niet geparsed kan worden;
    de aanroeper laat de regel in dat geval weg.
    """
    if not created_at:
        return None
    try:
        dt_utc = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return dt_utc.astimezone(_DISPLAY_TZ).strftime("%d-%m-%Y %H:%M")
    except ValueError:
        return None


def _render_analyse(doc, sub: dict) -> None:
    """Rendert één sub-analyse: heading + body (walk) of een lege-melding.

    We filteren niet op een `status`-veld: de bestaande renderers in
    page_navigation/analysis_results/analyses/ doen dat ook niet, en in de
    praktijk blijkt het statusveld vaak niet op de verwachte sentinel-
    waarde ('completed') te staan terwijl `result` wél bruikbare data
    bevat. Presence van `result` is de enige betrouwbare indicator.
    """
    doc.add_heading(_front_end_name(sub), level=2)

    result = sub.get("result")
    if _is_leeg_resultaat(result):
        p = doc.add_paragraph()
        p.add_run("— nog geen resultaat beschikbaar.").italic = True
        return

    _walk(result, doc, heading_level=3)


def _is_leeg_resultaat(result: Any) -> bool:
    """True wanneer er niks zinnigs in `result` staat om te renderen."""
    if result is None:
        return True
    if isinstance(result, (str, list, dict)) and len(result) == 0:
        return True
    return False


# ---------------------------------------------------------------------------
# Generieke JSON → docx walker
# ---------------------------------------------------------------------------


def _walk(
    value: Any,
    doc,
    heading_level: int = 3,
    skip_keys: set[str] | None = None,
) -> None:
    """Recursieve JSON-walker.

    - dict  → sleutels als "Key: value"-paragraph of als subheading+recursie.
    - list  → list-of-dict → secties, list-of-primitives → bullets.
    - str   → paragraph (met dubbele-newline-splitting voor lange teksten).
    - bool  → "Ja"/"Nee" paragraph.
    - None of ""  → overgeslagen.
    - overig (getal) → str(x) paragraph.
    """
    if value is None or value == "":
        return
    if isinstance(value, dict):
        _walk_dict(value, doc, heading_level, skip_keys or set())
    elif isinstance(value, list):
        _walk_list(value, doc, heading_level)
    elif isinstance(value, bool):
        doc.add_paragraph("Ja" if value else "Nee")
    elif isinstance(value, str):
        _add_paragraph_multiline(doc, value)
    else:
        doc.add_paragraph(str(value))


def _walk_dict(
    value: dict,
    doc,
    heading_level: int,
    skip_keys: set[str],
) -> None:
    """Doorloopt een dict in insertion-order.

    Primitieve waarden (str/number/bool) worden als "Key: value"-paragraph
    gerenderd; nested dicts/lists krijgen een subheading en recursieve
    verwerking. Sleutels in `skip_keys` worden overgeslagen — handig wanneer
    de aanroepende _walk_list de titel al als heading heeft gerenderd.
    """
    for key, val in value.items():
        if key in skip_keys:
            continue
        label = _humanize_key(key)
        if isinstance(val, (dict, list)):
            niveau = min(heading_level, _MAX_HEADING_LEVEL)
            doc.add_heading(label, level=niveau)
            _walk(val, doc, heading_level + 1)
        elif val is None or val == "":
            # Lege velden overslaan voorkomt eindeloze "Key: "-regels zonder
            # inhoud in documenten waar veel optionele velden leegblijven.
            continue
        elif isinstance(val, str) and _is_block_tekst(val):
            # Lange of meerregelige strings krijgen een eigen subheading +
            # losse paragraphs, anders verdwijnen de alinea-grenzen uit de
            # model-output in één lange inline-regel.
            niveau = min(heading_level, _MAX_HEADING_LEVEL)
            doc.add_heading(label, level=niveau)
            _add_paragraph_multiline(doc, val)
        else:
            p = doc.add_paragraph()
            p.add_run(f"{label}: ").bold = True
            _append_value_run(p, val)


def _walk_list(value: list, doc, heading_level: int) -> None:
    if not value:
        return

    # Drie gevallen:
    # 1) alle items zijn dicts            → elk item als sectie met subheading
    # 2) alle items zijn primitieven      → bullet-list
    # 3) gemengd (zeldzaam in onze data)  → per-item recursieve fallback
    if all(isinstance(item, dict) for item in value):
        for i, item in enumerate(value, start=1):
            subkey, subwaarde = _subheading_van_dict(item)
            niveau = min(heading_level, _MAX_HEADING_LEVEL)
            if subwaarde:
                doc.add_heading(subwaarde, level=niveau)
                # De gebruikte sleutel overslaan, anders wordt hij hieronder
                # nóg een keer als "Titel: ..."-paragraph gerenderd.
                _walk(item, doc, heading_level + 1, skip_keys={subkey})
            else:
                doc.add_heading(f"{i}.", level=niveau)
                _walk(item, doc, heading_level + 1)
        return

    if all(not isinstance(item, (dict, list)) for item in value):
        for item in value:
            if item is None or item == "":
                continue
            tekst = ("Ja" if item else "Nee") if isinstance(item, bool) else str(item)
            doc.add_paragraph(tekst, style="List Bullet")
        return

    # Gemengde lijst: per item recursief verwerken zonder lijstopmaak.
    for item in value:
        _walk(item, doc, heading_level)


def _subheading_van_dict(item: dict) -> tuple[str | None, str | None]:
    """Zoekt de eerste bruikbare titel-achtige sleutel in een dict.

    Retourneert (sleutel, waarde) zodat de caller de sleutel aan
    `skip_keys` kan toevoegen. Beide None als er geen geschikte sleutel is.
    """
    for key in _SUBHEADING_KEYS:
        val = item.get(key)
        if isinstance(val, str) and val.strip():
            return key, val.strip()
    return None, None


def _append_value_run(p, value: Any) -> None:
    if isinstance(value, bool):
        p.add_run("Ja" if value else "Nee")
    else:
        p.add_run(str(value))


def _add_paragraph_multiline(doc, text: str) -> None:
    """Splitst een string op blank lines en maakt er aparte paragraphs van.

    Zo blijven gestructureerde analyse-resultaten met meerdere alinea's ook
    in Word leesbaar: de model-output gebruikt vaak '\\n\\n' als alinea-
    scheider, wat python-docx anders als één grote paragraph zou behandelen.
    """
    text = text.strip()
    if not text:
        return
    stukken = _BLANK_LINE_RE.split(text)
    for stuk in stukken:
        gestript = stuk.strip()
        if not gestript:
            continue
        doc.add_paragraph(gestript)


def _is_block_tekst(tekst: str) -> bool:
    """True als een string beter als block-paragraph gerenderd kan worden.

    Criterium: bevat een newline (dus meerdere regels) óf is langer dan
    _INLINE_STRING_MAX tekens (zonder newlines). Kort+eenregelig blijft
    inline in 'Sleutel: waarde'-vorm.
    """
    if "\n" in tekst:
        return True
    return len(tekst) > _INLINE_STRING_MAX


def _humanize_key(key: str) -> str:
    """Maakt 'structuralistische_exegese' → 'Structuralistische exegese'."""
    woorden = _WORD_SEP_RE.sub(" ", key).strip()
    if not woorden:
        return key
    return woorden[0].upper() + woorden[1:]


# ---------------------------------------------------------------------------
# Inhoudsopgave, paginanummers en auto-update-fields (raw OOXML)
# ---------------------------------------------------------------------------
#
# python-docx heeft geen high-level API voor TOC-velden of paginanummers,
# dus we injecteren de benodigde OOXML-elementen rechtstreeks. Het "w:fldChar
# begin / instrText / separate / end"-patroon is de standaard-constructie die
# Word gebruikt voor alle veldcodes (TOC, PAGE, NUMPAGES, etc.).


def _veld_invoegen(run, instructie: str, placeholder: str = "") -> None:
    """Injecteert een Word-veldcode in een run.

    Word berekent de zichtbare tekst op basis van `instructie` (bv. 'PAGE'
    of 'TOC \\o "1-2" \\h \\z \\u'). Totdat het veld voor het eerst wordt
    bijgewerkt, toont Word `placeholder` — handig voor de TOC die pas na
    update gevuld wordt.
    """
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")

    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instructie

    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")

    placeholder_t = OxmlElement("w:t")
    placeholder_t.text = placeholder

    eind = OxmlElement("w:fldChar")
    eind.set(qn("w:fldCharType"), "end")

    r_elem = run._element
    r_elem.append(begin)
    r_elem.append(instr)
    r_elem.append(separate)
    r_elem.append(placeholder_t)
    r_elem.append(eind)


def _enable_auto_update_fields(doc) -> None:
    """Laat Word alle velden bij openen automatisch bijwerken.

    Zet `<w:updateFields w:val="true"/>` in settings.xml. Zonder dit moet
    de lezer handmatig F9 indrukken om de TOC en paginanummer-totalen te
    berekenen; met deze setting verschijnt bij openen een prompt "Dit
    document bevat velden die verwijzen naar andere bestanden. Wilt u ze
    bijwerken?" waarop 'Ja' de TOC vult.
    """
    settings = doc.settings.element
    element = OxmlElement("w:updateFields")
    element.set(qn("w:val"), "true")
    settings.append(element)


def _voeg_paginanummers_toe(doc) -> None:
    """Zet 'Pagina X van Y' gecentreerd in de footer van de eerste sectie."""
    footer = doc.sections[0].footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p.add_run("Pagina ")
    run_page = p.add_run()
    _veld_invoegen(run_page, "PAGE")
    p.add_run(" van ")
    run_total = p.add_run()
    _veld_invoegen(run_total, "NUMPAGES")


def _render_inhoudsopgave(doc) -> None:
    """Voegt een klikbare inhoudsopgave in op niveau 1-2 (tabs + analyses).

    Het label 'Inhoudsopgave' is bewust géén Heading 1/2 — anders zou de
    TOC zichzelf als eerste item bevatten. We gebruiken een gewone
    paragraph met bold + vergrote font.
    """
    label = doc.add_paragraph()
    run = label.add_run("Inhoudsopgave")
    run.bold = True
    run.font.size = Pt(18)

    # Lege regel tussen label en de feitelijke TOC-inhoud.
    doc.add_paragraph()

    p_toc = doc.add_paragraph()
    run_toc = p_toc.add_run()
    # \o "1-2"  → outline-levels 1 en 2 (onze Tab-headings en analyse-kops)
    # \h        → items renderen als hyperlinks (klikbaar in Word)
    # \z        → verberg tab-leaders/page-nummers in Web-layout
    # \u        → gebruik outline-paragraphs als basis
    _veld_invoegen(
        run_toc,
        'TOC \\o "1-2" \\h \\z \\u',
        placeholder=(
            "De inhoudsopgave wordt door Word automatisch gevuld bij het "
            "openen van dit document. Gebeurt dat niet? Klik met de "
            "rechtermuisknop op deze tekst en kies 'Veld bijwerken' (F9)."
        ),
    )


# ---------------------------------------------------------------------------
# Bestandsnaam
# ---------------------------------------------------------------------------


def _bestandsnaam(sermon: dict) -> str:
    """Levert een bestandsveilige naam o.b.v. gemeente + zondagdatum."""
    gemeente_raw = (sermon.get("church") or {}).get("name", "kerkdienst")
    sermon_date = sermon.get("sermon_date", "")
    # Vervang alles behalve letters/cijfers/underscore/koppelteken door '_',
    # lowercase, en trim trailing underscores — voorkomt problemen op
    # Windows-filesystems en ziet er netjes uit.
    veilig = re.sub(r"[^\w\-]+", "_", gemeente_raw.lower()).strip("_")
    if not veilig:
        veilig = "kerkdienst"
    if sermon_date:
        return f"kerkdienstanalyse_{veilig}_{sermon_date}.docx"
    return f"kerkdienstanalyse_{veilig}.docx"
