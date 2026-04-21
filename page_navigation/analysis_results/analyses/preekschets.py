"""Renderers voor Preekschetsen: generiek (preek_onderdelen) + specifieke
structuur-preekschetsen zoals Lowry (Homiletical Plot) en Buttrick (Moves
and Structures). Dispatch per analyse-naam."""

import json
from typing import Any

import streamlit as st

from src.utils.utils import clean_md


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
    else:
        st.markdown(_md(text))


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

        header = f"{volgorde}. {titel} ({type_label})" if volgorde else f"{titel} ({type_label})"
        with st.expander(header, expanded=True):
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

    # Tekstkeuze
    tk = result.get("tekstkeuze", {})
    if tk:
        with st.expander("Tekstkeuze", expanded=True):
            _section("Gekozen lezing", tk.get("gekozen_lezing"))
            _section("Onderbouwing", tk.get("onderbouwing"))
            _section("Omkerings-potentie", tk.get("omkerings_potentie"))

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
                _section("Inhoud", stap.get("inhoud"))
                _section("Doel", stap.get("doel"))
                _section("Type omkering", stap.get("type_omkering"))
                _section("Toelichting", stap.get("toelichting_type") or stap.get("toelichting"))
                # Overige velden dynamisch; skip de al gerenderde
                skip = {"titel", "inhoud", "doel", "type_omkering", "toelichting_type", "toelichting", "ambiguiteit"}
                for k, v in stap.items():
                    if k not in skip and v:
                        _section(k.replace("_", " ").capitalize(), v)
                # Ambiguïteit apart onderaan om de volgorde leesbaar te houden
                amb = stap.get("ambiguiteit", "")
                if amb:
                    _section("Ambiguïteit / spanning", amb)

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

    # Tekstkeuze
    tk = result.get("tekstkeuze", {})
    if tk:
        with st.expander("Tekstkeuze", expanded=True):
            _section("Gekozen lezing", tk.get("gekozen_lezing"))
            _section("Onderbouwing", tk.get("onderbouwing"))
            _section("Aansluiting context", tk.get("aansluiting_context"))
            alt = tk.get("alternatieve_lezingen", [])
            if alt:
                st.markdown("**Alternatieve lezingen:** " + ", ".join(str(a) for a in alt))

    # Introductie
    intro = result.get("introductie", {})
    if intro:
        with st.expander("Introductie", expanded=True):
            _section("Focus-beeld", intro.get("focus_beeld"))
            _section("Hermeneutische oriëntatie", intro.get("hermeneutische_orientatie"))
            _section("Uitgeschreven tekst", intro.get("uitgeschreven_tekst"))

    # Moves (3-4 min taalmodules, elk met eigen perspectief)
    moves = result.get("moves", [])
    if moves:
        st.subheader("Moves")
        for move in moves:
            nr = move.get("move_nummer", "")
            kernidee = move.get("kernidee", "")
            label = f"Move {nr}: {kernidee}" if kernidee else f"Move {nr}"
            with st.expander(label, expanded=False):
                _section("Perspectief", move.get("perspectief"))
                _section("Retorische strategie", move.get("retorische_strategie"))
                _section("Verbinding vorige move", move.get("verbinding_vorige"))
                _section("Uitgeschreven tekst", move.get("uitgeschreven_tekst"))
                # Extra velden (bv. woorden_telling, verbinding_volgende)
                skip = {"move_nummer", "kernidee", "perspectief", "retorische_strategie",
                        "verbinding_vorige", "uitgeschreven_tekst"}
                for k, v in move.items():
                    if k not in skip and v:
                        _section(k.replace("_", " ").capitalize(), v)

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
