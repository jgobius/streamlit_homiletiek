"""Renderers voor Preekschetsen: generiek (preek_onderdelen) + specifieke
structuur-preekschetsen zoals Lowry (Homiletical Plot) en Buttrick (Moves
and Structures). Dispatch per analyse-naam."""

import json
from typing import Any

import streamlit as st

from src.utils.utils import clean_md, humanize_key


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _result(analysis: dict) -> dict:
    # Het result-veld kan zowel dict als JSON-string zijn; normaliseer
    # naar dict zodat de render-functies simpel kunnen itereren.
    result = analysis.get("result", {})
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except (json.JSONDecodeError, ValueError):
            return {}
    return result or {}


def _md(text: Any) -> str:
    if not text:
        return ""
    return clean_md(str(text))


def _section(label: str, text: Any, *, callout: bool = False) -> None:
    if not text:
        return
    st.markdown(f"**{label}**")
    if callout:
        st.info(_md(text))
    elif isinstance(text, list):
        # Lijstvelden (bv. 'verzamelde_beelden') als nette bullet list,
        # niet als ruwe Python-repr — anders zou de gebruiker letterlijk
        # ['item', 'item'] in de UI zien.
        for item in text:
            if item:
                st.markdown(f"- {_md(item)}")
    else:
        st.markdown(_md(text))


def _meta_label(label: str, value: Any) -> None:
    """Render een secundair veld als compact museum-bijschrift: kleinkapitaal
    label in dempte grijstint boven de waarde. Bedoeld voor de zijkolom van
    een plot-stadium of move, zodat de hoofdtekst (inhoud / uitgeschreven
    tekst) visueel domineert en korte meta-info (Doel, Perspectief, Type
    omkering) niet meer onder de hoofdtekst gestapeld staat."""
    if not value:
        return
    # Inline HTML omdat Streamlit geen native 'kleinkapitaal'-component heeft.
    # Geen hardcoded tekstkleur op de waarde: die erft de themakleur en blijft
    # daardoor in zowel light als dark mode goed leesbaar. Het label gebruikt
    # opacity i.p.v. een vaste grijstint, zodat het ook ten opzichte van de
    # dark-mode tekstkleur gedempt blijft (een vaste #8a8a8a was in dark mode
    # nauwelijks te onderscheiden van de achtergrond).
    # Lijstvelden (bv. 'verzamelde_beelden') krijgen een echte <ul>; anders
    # zou _md(value) een ruwe Python-repr zoals ['…', '…'] in de UI zetten.
    if isinstance(value, list):
        items = [item for item in value if item]
        if not items:
            return
        body_html = (
            "<ul style='margin:0.1rem 0 0; padding-left:1.1rem;'>"
            + "".join(f"<li>{_md(item)}</li>" for item in items)
            + "</ul>"
        )
    else:
        body_html = _md(value)
    st.markdown(
        f"<div style='margin-bottom:0.75rem;'>"
        f"<div style='font-size:0.72rem; letter-spacing:0.08em; "
        f"text-transform:uppercase; font-weight:600; opacity:0.6; "
        f"margin-bottom:0.15rem;'>{label}</div>"
        f"<div style='font-size:0.92rem; line-height:1.45;'>"
        f"{body_html}</div></div>",
        unsafe_allow_html=True,
    )


def _hero_lezing(text: Any) -> None:
    """Render de gekozen schriftlezing als oranje accent-pil bovenaan een
    Tekstkeuze-blok. Het projectthema is oranje, dus deze pil functioneert
    als visuele anker voor de bijbeltekst zonder de rest verticaal onder
    elkaar te duwen."""
    if not text:
        return
    # Expliciete donkere tekstkleur (#1f2937) omdat de cream achtergrond
    # in dark mode anders de standaard lichte themakleur zou erven, wat
    # licht-op-licht en dus onleesbaar zou zijn.
    st.markdown(
        f"<div style='display:inline-block; padding:0.35rem 0.85rem; "
        f"margin-bottom:0.8rem; background:#fff4e6; color:#1f2937; "
        f"border-left:3px solid #f97316; border-radius:2px; "
        f"font-weight:500;'>📖 {_md(text)}</div>",
        unsafe_allow_html=True,
    )


def _is_woordtelling_key(key: str) -> bool:
    """True voor velden die het aantal woorden van een (sub)analyse tellen
    (bijv. 'woorden_telling', 'woordtelling', 'aantal_woorden'). De
    gebruiker wil zulke meta-tellers niet meer in de Buttrick-UI zien — ze
    voegen geen homiletische informatie toe en maken het blok rumoeriger."""
    k = key.lower().replace("_", "").replace("-", "")
    return "woord" in k and ("tell" in k or "aantal" in k or "count" in k)


def _render_waarom_keten(items: list[dict[str, Any]]) -> None:
    """Render een 'waarom?'-keten (lijst van {vraag, antwoord}-paren) als
    genummerde markdown, in plaats van de ruwe Python-repr van de lijst.

    Wordt gebruikt in de Lowry-verdiepingsstap; het schema staat gedefinieerd
    in configs/homiletische_lowry.json."""
    if not items:
        return
    st.markdown("**Waarom-keten**")
    for idx, paar in enumerate(items, start=1):
        if not isinstance(paar, dict):
            # Defensief: schema garandeert dict, maar val terug op string-repr
            # zodat een afwijkend item niet de hele sectie breekt.
            st.markdown(f"{idx}. {_md(paar)}")
            continue
        vraag = paar.get("vraag", "")
        antwoord = paar.get("antwoord", "")
        if vraag:
            st.markdown(f"{idx}. **{_md(vraag)}**")
        if antwoord:
            # Indent het antwoord onder de vraag; non-breaking spaces zorgen
            # dat Streamlit's markdown-renderer de inspringing bewaart.
            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ {_md(antwoord)}", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Generiek preek_onderdelen-schema (Noordmans en andere auteur-preekschetsen)
# ---------------------------------------------------------------------------

def _render_noordmans_schema(analysis: dict[str, Any]) -> None:
    """Render een preekschets met preek_onderdelen formaat."""
    result = analysis.get("result", {})

    kerntekst = result.get("kerntekst") or result.get("schriftlezing", "")
    structuur_type = result.get("structuur_type", "")

    if kerntekst:
        st.info(f"📖 {kerntekst}")
    if structuur_type:
        st.caption(f"Structuur: {structuur_type}")

    st.divider()

    for onderdeel in result.get("preek_onderdelen", []):
        titel = onderdeel.get("titel", "")
        type_label = onderdeel.get("type", "")
        volgorde = onderdeel.get("volgorde", "")
        inhoud = onderdeel.get("inhoud", "")
        toelichting = onderdeel.get("toelichting", "")

        # Het 'type'-veld komt rauw uit de DB als snake_case (bv.
        # 'subversieve_wending'). Via humanize_key wordt dat
        # 'Subversieve wending' — leesbaar in de expander-header.
        type_label_leesbaar = humanize_key(type_label) if type_label else ""
        header = f"{volgorde}. {titel} ({type_label_leesbaar})" if volgorde else f"{titel} ({type_label_leesbaar})"
        # Expanders dicht openen zodat de gebruiker zelf bepaalt wat hij uitklapt;
        # consistent met Lowry/Buttrick en met volledige_preek.py.
        with st.expander(header, expanded=False):
            st.markdown(clean_md(inhoud))
            if toelichting:
                st.caption(toelichting)

    kernwoorden = result.get("kernwoorden", [])
    if kernwoorden:
        st.caption("**Kernwoorden:** " + " · ".join(kernwoorden))

    theologische_beweging = result.get("theologische_beweging", "")
    if theologische_beweging:
        st.success(f"🔷 {theologische_beweging}")


# ---------------------------------------------------------------------------
# Homiletische Lowry — 5 narratieve stadia (Hè? / Oei… / Aha! / Ja! / Zó!)
# ---------------------------------------------------------------------------

_LOWRY_LABELS = {
    "he_kwestie_oops":         "① HÈ? (OOPS!) — De Kwestie",
    "oei_verdieping_ugh":      "② OEI… (UGH!) — De Verdieping",
    "aha_wending_aha":         "③ AHA! (AHA!) — De Wending",
    "ja_verkondiging_whee":    "④ JA! (WHEE!) — De Verkondiging",
    "zo_doorwerking_yeah":     "⑤ ZÓ! (YEAH!) — De Doorwerking",
}


def render_homiletische_lowry(analysis: dict) -> None:
    result = _result(analysis)
    if not result:
        st.info("Geen resultaat beschikbaar.")
        return

    # Tekstkeuze — gekozen lezing als oranje accent-pil, onderbouwing als
    # hoofdparagraaf, omkerings-potentie als secundair meta-bijschrift.
    # Voorheen stonden alledrie als bold-label + tekst onder elkaar; het
    # nieuwe ontwerp geeft de bijbeltekst visuele voorrang en demt de
    # toelichting tot een leesbaar maar ondergeschikt niveau.
    tk = result.get("tekstkeuze", {})
    if tk:
        with st.expander("Tekstkeuze", expanded=False):
            _hero_lezing(tk.get("gekozen_lezing"))
            onderbouwing = tk.get("onderbouwing")
            if onderbouwing:
                st.markdown(_md(onderbouwing))
            _meta_label("Omkerings-potentie", tk.get("omkerings_potentie"))

    # Homiletical Plot
    plot = result.get("homiletical_plot", {})
    if plot:
        st.subheader("Homiletical Plot")
        for key, label in _LOWRY_LABELS.items():
            stap = plot.get(key, {})
            if not stap:
                continue
            with st.expander(label, expanded=False):
                titel = stap.get("titel", "")
                if titel and titel != label:
                    st.caption(titel)
                # Twee-kolomslay-out à la kunstcatalogus: hoofdtekst (Inhoud)
                # ademt links breed, korte meta-velden (Doel, Type omkering,
                # Toelichting, Ambiguïteit) staan rechts in kleinkapitaal.
                # Voorheen stond alles onder elkaar wat de plot-stadia
                # onnodig lang en rumoerig maakte.
                col_main, col_meta = st.columns([2, 1], gap="medium")
                with col_main:
                    inhoud = stap.get("inhoud")
                    if inhoud:
                        st.markdown(_md(inhoud))
                with col_meta:
                    _meta_label("Doel", stap.get("doel"))
                    _meta_label("Type omkering", stap.get("type_omkering"))
                    _meta_label(
                        "Toelichting",
                        stap.get("toelichting_type") or stap.get("toelichting"),
                    )
                    _meta_label("Ambiguïteit", stap.get("ambiguiteit"))
                # Waarom-keten als genummerde lijst onder de kolommen
                # (volle breedte) — de keten is een gestructureerde reeks
                # vraag/antwoord-paren die zich slecht laat opvouwen in een
                # smalle meta-zijkolom.
                waarom = stap.get("waarom_keten")
                if waarom:
                    _render_waarom_keten(waarom)
                # Overige onbekende velden compact onderaan, zodat schema-
                # uitbreidingen niet stilletjes verdwijnen maar de meta-
                # zijkolom wel rustig blijft.
                skip = {"titel", "inhoud", "doel", "type_omkering",
                        "toelichting_type", "toelichting", "ambiguiteit",
                        "waarom_keten"}
                for k, v in stap.items():
                    if k not in skip and v:
                        _meta_label(k.replace("_", " ").capitalize(), v)

    # Logica check (sluitcontrole op diagnose-remedie)
    lc = result.get("logica_check", {})
    if lc:
        klopt = lc.get("diagnose_remedie_klopt")
        toelichting = lc.get("toelichting", "")
        status = "✅ Diagnose–remedie klopt" if klopt else "⚠️ Controleer diagnose–remedie"
        st.caption(f"{status} — {_md(toelichting)}")


# ---------------------------------------------------------------------------
# Homiletische Buttrick — introductie + moves + conclusie
# ---------------------------------------------------------------------------

def render_homiletische_buttrick(analysis: dict) -> None:
    result = _result(analysis)
    if not result:
        st.info("Geen resultaat beschikbaar.")
        return

    # Tekstkeuze — zelfde patroon als Lowry: bijbeltekst als oranje pil
    # bovenaan, onderbouwing als hoofdtekst, en aansluiting/alternatieven
    # als compacte meta onderaan. Houdt het blok rustig en leesbaar.
    tk = result.get("tekstkeuze", {})
    if tk:
        with st.expander("Tekstkeuze", expanded=False):
            _hero_lezing(tk.get("gekozen_lezing"))
            onderbouwing = tk.get("onderbouwing")
            if onderbouwing:
                st.markdown(_md(onderbouwing))
            _meta_label("Aansluiting context", tk.get("aansluiting_context"))
            alt = tk.get("alternatieve_lezingen", [])
            if alt:
                _meta_label("Alternatieve lezingen", ", ".join(str(a) for a in alt))

    # Introductie — de uitgeschreven tekst is de eigenlijke preekopening en
    # krijgt de hoofdkolom; focus-beeld en hermeneutische oriëntatie zijn
    # regie-aanwijzingen en horen als meta in de zijkolom.
    intro = result.get("introductie", {})
    if intro:
        with st.expander("Introductie", expanded=False):
            col_main, col_meta = st.columns([2, 1], gap="medium")
            with col_main:
                tekst = intro.get("uitgeschreven_tekst")
                if tekst:
                    st.markdown(_md(tekst))
            with col_meta:
                _meta_label("Focus-beeld", intro.get("focus_beeld"))
                _meta_label(
                    "Hermeneutische oriëntatie",
                    intro.get("hermeneutische_orientatie"),
                )

    # Moves (3-4 min taalmodules, elk met eigen perspectief)
    moves = result.get("moves", [])
    if moves:
        st.subheader("Moves")
        for move in moves:
            nr = move.get("move_nummer", "")
            kernidee = move.get("kernidee", "")
            label = f"Move {nr}: {kernidee}" if kernidee else f"Move {nr}"
            with st.expander(label, expanded=False):
                # Twee kolommen: uitgeschreven preektekst links, regie-meta
                # (Perspectief, Retorische strategie, Verbinding vorige) rechts.
                # Woordentellingen worden expliciet uitgefilterd — de gebruiker
                # heeft aangegeven dat die per (sub)analyse niet vermeld
                # hoeven te worden, omdat ze geen homiletische waarde toevoegen.
                col_main, col_meta = st.columns([2, 1], gap="medium")
                with col_main:
                    tekst = move.get("uitgeschreven_tekst")
                    if tekst:
                        st.markdown(_md(tekst))
                with col_meta:
                    _meta_label("Perspectief", move.get("perspectief"))
                    _meta_label(
                        "Retorische strategie",
                        move.get("retorische_strategie"),
                    )
                    _meta_label(
                        "Verbinding vorige move",
                        move.get("verbinding_vorige"),
                    )
                # Extra velden uit toekomstige schema-uitbreidingen — woord-
                # tellers altijd skippen, overige als compacte meta tonen.
                skip = {"move_nummer", "kernidee", "perspectief",
                        "retorische_strategie", "verbinding_vorige",
                        "uitgeschreven_tekst"}
                for k, v in move.items():
                    if k in skip or not v or _is_woordtelling_key(k):
                        continue
                    _meta_label(k.replace("_", " ").capitalize(), v)

    # Conclusie
    conclusie = result.get("conclusie", {})
    if conclusie:
        with st.expander("Conclusie", expanded=False):
            for k, v in conclusie.items():
                _section(k.replace("_", " ").capitalize(), v)

    # Samenvatting / overige context-velden (beweging_samenvatting e.d.)
    # De agent levert deze velden soms als string, soms als dict met
    # sub-velden (bv. logische_lijn + perspectief_variatie). Beide vormen
    # leesbaar renderen — dict uitpakken naar sub-secties i.p.v. de ruwe
    # Python-repr tonen.
    # Divider alleen *tussen* blokken plaatsen, niet na het laatste —
    # anders blijft er een lege horizontale lijn onder de laatste sectie staan.
    extra_blocks = [(k, result.get(k, "")) for k in ("beweging_samenvatting", "contextuele_integratie")]
    extra_blocks = [(k, v) for k, v in extra_blocks if v]
    for idx, (key, val) in enumerate(extra_blocks):
        if idx > 0:
            st.divider()
        st.markdown(f"**{key.replace('_', ' ').capitalize()}**")
        if isinstance(val, dict):
            for sub_key, sub_val in val.items():
                if sub_val:
                    _section(sub_key.replace("_", " ").capitalize(), sub_val)
        else:
            st.markdown(_md(val))



# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

# Per analyse-naam een type-specifieke renderer. Namen zonder entry vallen
# terug op het generieke preek_onderdelen-schema (Noordmans-stijl).
_RENDERERS = {
    "homiletische_lowry":    render_homiletische_lowry,
    "homiletische_buttrick": render_homiletische_buttrick,
}


def preekschets(analysis: dict[str, Any], analysis_type_name: str = "") -> None:
    """Dispatch naar de juiste preekschets-renderer.

    Args:
        analysis: Het analyse-dict (bevat 'result' met de JSON-uitvoer).
        analysis_type_name: Naam van het AnalysisType; bepaalt welke renderer
            wordt gekozen. Lege of onbekende namen vallen terug op het
            generieke preek_onderdelen-schema.
    """
    renderer = _RENDERERS.get(analysis_type_name)
    if renderer:
        renderer(analysis)
    else:
        _render_noordmans_schema(analysis)
