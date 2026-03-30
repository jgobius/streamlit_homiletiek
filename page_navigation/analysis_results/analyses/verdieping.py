"""Renderers voor Verdieping-analyses (gebeden, homiletisch, kunst, liturgisch)."""

import json
from typing import Any

import streamlit as st

from src.utils.utils import clean_md


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _result(analysis: dict) -> dict:
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
# Gebeden (36 / 37 / 38 / 39)
# ---------------------------------------------------------------------------

_GEBED_LABELS = {
    "drempelgebed":  "Drempelgebed",
    "kyrie":         "Kyrie",
    "epiclese":      "Epiclese",
    "dankgebed":     "Dankgebed / Grote dankzegging",
    "voorbeden":     "Voorbeden",
}


def _render_voorbeden(g: dict) -> None:
    for cirkel_naam, cirkel in g.get("cirkels", {}).items():
        label = cirkel_naam.replace("_", " ").capitalize()
        with st.expander(label, expanded=False):
            tekst = cirkel.get("tekst", "")
            if tekst:
                st.markdown(_md(tekst))
            themas = cirkel.get("themas", [])
            if themas:
                st.caption("Thema's: " + " · ".join(themas))

    onze_vader = g.get("onze_vader", "")
    if onze_vader:
        with st.expander("Onze Vader", expanded=False):
            overgang = g.get("overgang_onze_vader", "")
            if overgang:
                st.caption(_md(overgang))
            st.markdown(_md(onze_vader))


def _render_gebed(naam: str, g: dict) -> None:
    label = _GEBED_LABELS.get(naam, naam.replace("_", " ").capitalize())
    with st.expander(label, expanded=naam == "drempelgebed"):
        aanspraak = g.get("aanspraak", "")
        if aanspraak:
            st.caption(f"Aanspraak: *{_md(aanspraak)}*")

        tekst = g.get("tekst", "")
        if tekst:
            st.markdown(_md(tekst))
        elif naam == "voorbeden":
            _render_voorbeden(g)

        stilte = g.get("stilte_instructie", "")
        if stilte:
            st.caption(_md(stilte))

        taalveld = g.get("bijbels_taalveld", "")
        if taalveld:
            st.caption(f"Bijbels taalveld: {_md(taalveld)}")

        amen = g.get("amen")
        if amen is True:
            st.caption("— Amen.")


def render_gebeden(analysis: dict) -> None:
    result = _result(analysis)
    if not result:
        st.info("Geen resultaat beschikbaar.")
        return

    scenario = result.get("gekozen_scenario", "")
    if scenario:
        st.info(f"**Scenario:** {_md(scenario)}")

    gebeden = result.get("gebeden", {})
    if gebeden:
        for naam, g in gebeden.items():
            if isinstance(g, dict):
                _render_gebed(naam, g)

    echo = result.get("echo_techniek", "")
    if echo:
        with st.expander("Echo-techniek", expanded=False):
            st.markdown(_md(echo))

    technieken = result.get("poetische_technieken_gebruikt", {})
    if technieken:
        with st.expander("Poëtische technieken", expanded=False):
            for tech, omschr in technieken.items():
                st.markdown(f"**{tech.replace('_', ' ').capitalize()}:** {_md(omschr)}")


# ---------------------------------------------------------------------------
# Homiletische Lowry (15)
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
                # Overige velden dynamisch
                skip = {"titel", "inhoud", "doel", "type_omkering", "toelichting_type", "toelichting", "ambiguiteit"}
                for k, v in stap.items():
                    if k not in skip and v:
                        _section(k.replace("_", " ").capitalize(), v)
                # ambiguiteit apart
                amb = stap.get("ambiguiteit", "")
                if amb:
                    _section("Ambiguïteit / spanning", amb)

    # Logica check
    lc = result.get("logica_check", {})
    if lc:
        klopt = lc.get("diagnose_remedie_klopt")
        toelichting = lc.get("toelichting", "")
        status = "✅ Diagnose–remedie klopt" if klopt else "⚠️ Controleer diagnose–remedie"
        st.caption(f"{status} — {_md(toelichting)}")


# ---------------------------------------------------------------------------
# Homiletische Buttrick (16)
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

    # Moves
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
                # Extra velden
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

    # Samenvatting / overige velden
    for key in ("beweging_samenvatting", "contextuele_integratie"):
        val = result.get(key, "")
        if val:
            st.markdown(f"**{key.replace('_', ' ').capitalize()}**")
            st.markdown(_md(val))
            st.divider()

    woorden = result.get("woorden_telling_totaal")
    if woorden:
        st.caption(f"Geschat woordenaantal: {woorden:,}")


# ---------------------------------------------------------------------------
# Kunst, Cultuur en Film (18)
# ---------------------------------------------------------------------------

_KUNST_SECTIES = [
    ("moderne_hedendaagse_kunst",   "Moderne & hedendaagse kunst"),
    ("klassieke_christelijke_kunst","Klassieke christelijke kunst"),
    ("film_documentaire",           "Film & documentaire"),
    ("literatuur",                  "Literatuur"),
    ("jongeren_cultuur",            "Jongerencultuur"),
]

_MUZIEK_SUBCATS = [
    ("hedendaags", "Hedendaagse muziek"),
    ("klassiek",   "Klassieke muziek"),
    ("liturgisch", "Liturgische muziek"),
]


def _render_kunst_items(items: list) -> None:
    for item in items:
        titel = item.get("titel", "Onbekend")
        maker = (item.get("kunstenaar") or item.get("regisseur") or
                 item.get("auteur") or item.get("artiest") or
                 item.get("componist") or "")
        jaar = item.get("jaar", "")
        header = f"{titel}"
        if maker:
            header += f" — {maker}"
        if jaar:
            header += f" ({jaar})"
        with st.expander(header, expanded=False):
            for key in ("beschrijving", "relevante_scene", "relevantie", "verbinding",
                        "locatie", "type", "genre", "specifiek_deel",
                        "gebruik", "zoekterm", "zoekterm_hoge_resolutie"):
                val = item.get(key, "")
                if val:
                    _section(key.replace("_", " ").capitalize(), val)


def render_kunst_cultuur(analysis: dict) -> None:
    result = _result(analysis)
    if not result:
        st.info("Geen resultaat beschikbaar.")
        return

    # Hoofdsecties: kunst / film / literatuur
    for key, label in _KUNST_SECTIES:
        items = result.get(key, [])
        if not items:
            continue
        st.subheader(label)
        if isinstance(items, list):
            _render_kunst_items(items)
        st.divider()

    # Muziek (dict met subcategorieën)
    muziek = result.get("muziek", {})
    if muziek:
        st.subheader("Muziek")
        if isinstance(muziek, dict):
            for subkey, sublabel in _MUZIEK_SUBCATS:
                subitems = muziek.get(subkey, [])
                if subitems:
                    st.markdown(f"**{sublabel}**")
                    _render_kunst_items(subitems if isinstance(subitems, list) else [subitems])
        elif isinstance(muziek, list):
            _render_kunst_items(muziek)
        st.divider()

    # Aansluiting gemeente
    ag = result.get("aansluiting_gemeente", {})
    if ag:
        st.subheader("Aansluiting bij de gemeente")
        if isinstance(ag, str):
            st.markdown(_md(ag))
        elif isinstance(ag, dict):
            for k, v in ag.items():
                _section(k.replace("_", " ").capitalize(), v)
        st.divider()

    # Praktische handvatten
    ph = result.get("praktische_handvatten", {})
    if ph:
        st.subheader("Praktische handvatten")
        if isinstance(ph, dict):
            proj = ph.get("voor_projectie", [])
            if proj:
                st.markdown("**Voor projectie**")
                for item in proj:
                    kunstwerk = item.get("kunstwerk", "")
                    moment = item.get("liturgisch_moment", "")
                    duur = item.get("duur", "")
                    zoek = item.get("zoekterm_hoge_resolutie", "")
                    st.markdown(f"- **{kunstwerk}** — {moment}" +
                                (f" ({duur})" if duur else "") +
                                (f"\n  *Zoekterm:* `{zoek}`" if zoek else ""))

            med = ph.get("voor_meditatie", {})
            if med:
                st.markdown("**Voor meditatie**")
                for k, v in med.items():
                    if v:
                        st.markdown(f"- **{k.replace('_', ' ').capitalize()}:** {_md(str(v))}")

            rechten = ph.get("rechten", {})
            if rechten:
                with st.expander("Auteursrechten", expanded=False):
                    for k, v in rechten.items():
                        if v:
                            label = k.replace("_", " ").capitalize()
                            if isinstance(v, list):
                                st.markdown(f"**{label}:** " + ", ".join(v))
                            else:
                                st.markdown(f"**{label}:** {_md(str(v))}")
        elif isinstance(ph, list):
            for item in ph:
                st.markdown(f"- {_md(str(item))}")
        elif isinstance(ph, str):
            st.markdown(_md(ph))


# ---------------------------------------------------------------------------
# Kindermoment / Bezinningsmoment (40 / 43)
# ---------------------------------------------------------------------------

def render_kindermoment(analysis: dict) -> None:
    result = _result(analysis)
    if not result:
        st.info("Geen resultaat beschikbaar.")
        return

    opties = result.get("kindermoment_opties", [])
    if not opties:
        st.info("Geen opties beschikbaar.")
        return

    for i, optie in enumerate(opties, 1):
        titel = optie.get("titel", f"Optie {i}")
        type_naam = optie.get("type", "")
        label = f"Optie {i}: {titel}" + (f" ({type_naam})" if type_naam else "")
        with st.expander(label, expanded=(i == 1)):
            focus = optie.get("focus_schriftlezing", "")
            if focus:
                st.caption(f"Schriftlezing: {_md(focus)}")

            obj = optie.get("object", {})
            if obj:
                naam = obj.get("naam", "")
                uitleg = obj.get("uitleg", "")
                if naam:
                    st.markdown(f"**Object:** {_md(naam)}")
                if uitleg:
                    st.markdown(_md(uitleg))
                st.divider()

            script = optie.get("verhaal_script", "")
            if script:
                st.markdown(_md(script))

            afb = optie.get("afbeelding_idee", "")
            if afb:
                st.caption(f"Afbeelding-idee: {_md(afb)}")


# ---------------------------------------------------------------------------
# Wetslezing (41)
# ---------------------------------------------------------------------------

def render_wetslezing(analysis: dict) -> None:
    result = _result(analysis)
    if not result:
        st.info("Geen resultaat beschikbaar.")
        return

    inleiding = result.get("inleiding", {})
    if inleiding:
        tekst = inleiding.get("tekst", "") if isinstance(inleiding, dict) else str(inleiding)
        if tekst:
            st.info(_md(tekst))

    st.divider()

    wets = result.get("wetslezing", {})
    if wets:
        ref = wets.get("referentie", "")
        functie = wets.get("functie", "")
        motivering = wets.get("motivering", "")
        st.subheader(f"Wetslezing — {ref}")
        if functie:
            st.caption(f"Functie: {_md(functie)}")
        if motivering:
            st.markdown(_md(motivering))

    st.divider()

    psalm = result.get("psalm_gezang", {})
    if psalm:
        ref = psalm.get("referentie", "")
        verzen = psalm.get("verzen", "")
        cat = psalm.get("categorie", "")
        motivering = psalm.get("motivering", "")
        header = f"Antwoordpsalm / Gezang — {ref}"
        if verzen:
            header += f", vers {verzen}"
        st.subheader(header)
        if cat:
            st.caption(f"Categorie: {_md(cat)}")
        if motivering:
            st.markdown(_md(motivering))

    st.divider()

    genade = result.get("genadeverkondiging", {})
    if genade:
        ref = genade.get("referentie", "")
        kern = genade.get("kernboodschap", "")
        motivering = genade.get("motivering", "")
        st.subheader(f"Genadeverkondiging — {ref}")
        if kern:
            st.success(_md(kern))
        if motivering:
            st.markdown(_md(motivering))


# ---------------------------------------------------------------------------
# Kalender (42)
# ---------------------------------------------------------------------------

def render_kalender(analysis: dict) -> None:
    result = _result(analysis)
    if not result:
        st.info("Geen resultaat beschikbaar.")
        return

    week_van = result.get("week_van", "")
    if week_van:
        st.subheader(f"Week van {week_van}")

    # Aandachtspunten voor de predikant — bovenaan
    punten = result.get("aandachtspunten_predikant", [])
    if punten:
        with st.expander("Aandachtspunten voor de predikant", expanded=True):
            for punt in punten:
                st.markdown(f"- {_md(punt)}")

    st.divider()

    dagen = result.get("dagen", [])
    for dag in dagen:
        datum = dag.get("datum", dag.get("dag", ""))
        is_preek = dag.get("is_preekzondag", False)
        label = f"{'⛪ ' if is_preek else ''}{datum}"

        with st.expander(label, expanded=is_preek):
            # Kerkelijk
            kerkelijk = dag.get("kerkelijk", [])
            if kerkelijk:
                st.markdown("**Kerkelijk**")
                for item in kerkelijk:
                    naam = item.get("naam", "")
                    toelichting = item.get("toelichting", "")
                    type_k = item.get("type", "")
                    st.markdown(f"*{_md(naam)}*" + (f" ({type_k})" if type_k else ""))
                    if toelichting:
                        st.markdown(_md(toelichting))

            # Joods
            joods = dag.get("joods", {})
            if joods:
                heb = joods.get("hebreeuwse_datum", "")
                parasja = joods.get("parasja")
                feestdag = joods.get("feestdag")
                toelichting = joods.get("toelichting", "")
                parts = []
                if heb:
                    parts.append(heb)
                if parasja:
                    parts.append(f"Parasja: {parasja}")
                if feestdag:
                    parts.append(f"Feestdag: {feestdag}")
                if parts:
                    st.markdown("**Joods:** " + " · ".join(parts))
                if toelichting:
                    st.markdown(_md(toelichting))

            # Internationaal
            intern = dag.get("internationaal", [])
            if intern:
                st.markdown("**Internationaal**")
                for item in intern:
                    naam = item.get("naam", "")
                    relevantie = item.get("relevantie", "")
                    st.markdown(f"- **{_md(naam)}**" + (f" — {_md(relevantie)}" if relevantie else ""))

            # Overig
            overig = dag.get("overig", [])
            if overig:
                st.markdown("**Overig**")
                for item in overig:
                    naam = item.get("naam", "")
                    toelichting = item.get("toelichting", "")
                    cat = item.get("categorie", "")
                    st.markdown(f"- **{_md(naam)}**" + (f" ({cat})" if cat else "") +
                                (f" — {_md(toelichting)}" if toelichting else ""))

            # Astronomie
            astro = dag.get("astronomie", {})
            if astro:
                opgang = astro.get("zonsopgang", "")
                ondergang = astro.get("zonsondergang", "")
                maan = astro.get("maanfase", "")
                bijz = astro.get("bijzonderheden", "")
                astro_parts = []
                if opgang:
                    astro_parts.append(f"🌅 {opgang}")
                if ondergang:
                    astro_parts.append(f"🌇 {ondergang}")
                if maan:
                    astro_parts.append(f"🌙 {maan}")
                if astro_parts:
                    st.caption("  ".join(astro_parts))
                if bijz:
                    st.caption(_md(bijz))

            # Vakantie
            vakantie = dag.get("vakantie", {})
            if vakantie:
                schoolvakantie = vakantie.get("schoolvakantie")
                if schoolvakantie:
                    st.caption(f"🏫 Schoolvakantie: {_md(schoolvakantie)}")


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

_RENDERERS = {
    "gebeden":               render_gebeden,
    "gebeden_profetisch":    render_gebeden,
    "gebeden_dialogisch":    render_gebeden,
    "gebeden_eenvoudig":     render_gebeden,
    "homiletische_lowry":    render_homiletische_lowry,
    "homiletische_buttrick": render_homiletische_buttrick,
    "kunst_cultuur":         render_kunst_cultuur,
    "kindermoment":          render_kindermoment,
    "bezinningsmoment":      render_kindermoment,
    "wetslezing":            render_wetslezing,
    "kalender":              render_kalender,
}


def verdieping(analysis: dict[str, Any], analysis_type_name: str = "") -> None:
    """Dispatch naar de juiste type-specifieke renderer."""
    renderer = _RENDERERS.get(analysis_type_name)
    if renderer:
        renderer(analysis)
    else:
        # Fallback: generieke JSON-weergave
        result = _result(analysis)
        if not result:
            st.info("Geen resultaat beschikbaar.")
            return
        for key, value in result.items():
            if key.startswith("_"):
                continue
            st.subheader(key.replace("_", " ").capitalize())
            if isinstance(value, str):
                st.markdown(_md(value))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        st.markdown(f"- {_md(item)}")
                    else:
                        st.json(item)
            elif isinstance(value, dict):
                st.json(value)
            else:
                st.write(value)
            st.divider()
