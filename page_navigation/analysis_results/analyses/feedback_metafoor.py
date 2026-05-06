import re
from typing import Any

import streamlit as st

from src.utils.utils import clean_md


# Kleurmapping voor severity-georiënteerde enums in de Metafoor-output.
# Doel: enum-tokens als ZEER_COHERENT of VERBETERING_NODIG niet meer in CAPS
# laten schreeuwen, maar tonen als kleine gekleurde badge ("Zeer coherent").
# Type-enums (sterkte_type, risico_type, strategie) staan hier bewust NIET in:
# die zitten al in een st.success/st.warning-kader en krijgen alleen een
# nettere labelvariant zonder extra kleur.
_ENUM_KLEUREN: dict[str, str] = {
    # Positief / sterk
    "EXCELLENT": "green",
    "GOED": "green",
    "LEVEND": "green",
    "ZEER_COHERENT": "green",
    "GROTENDEELS_COHERENT": "green",
    "GERING": "green",
    # Tussenliggend
    "ADEQUAAT": "blue",
    "CONVENTIONEEL": "blue",
    "GEMENGD": "blue",
    "MATIG": "orange",
    # Zwak / problematisch
    "VERBETERING_NODIG": "orange",
    "ERNSTIG": "orange",
    "ZWAK": "red",
    "DOOD": "red",
    "INCOHERENT": "red",
    "KRITIEK": "red",
}


def _format_enum_label(value: str) -> str:
    """ZEER_COHERENT -> 'Zeer coherent'. Underscores worden vervangen door
    spaties en alleen de eerste letter krijgt een hoofdletter, zodat
    enum-waarden niet meer in CAPS schreeuwen in de UI."""
    if not value:
        return ""
    schoon = value.replace("_", " ").strip().lower()
    return schoon[:1].upper() + schoon[1:] if schoon else ""


def _is_enum_waarde(s: Any) -> bool:
    """Heuristiek: lijkt deze waarde op een enum-token (ALLE_HOOFDLETTERS_MET_UNDERSCORE)?
    Wordt gebruikt door de generieke list-renderer om losse enum-velden te
    detecteren en dezelfde nettere weergave te geven."""
    if not isinstance(s, str) or len(s) < 2:
        return False
    if not s.isupper():
        return False
    return all(c.isalpha() or c == "_" for c in s)


def _enum_markdown(value: str) -> str:
    """Geef een markdownsnippet terug: een gekleurd Streamlit-badge voor
    severity-enums, anders de platte (hoofdletter-bescheiden) labelvariant."""
    if not value:
        return ""
    label = _format_enum_label(value)
    kleur = _ENUM_KLEUREN.get(value.upper())
    return f":{kleur}[{label}]" if kleur else label


# Aaneengesloten 'shouty' frase: minstens twee opeenvolgende hoofdletters,
# eventueel onderbroken door spaties, /, _ of -. Vangt CMT-conceptnamen op zoals
# 'HET CHRISTELIJK LEVEN IS OORLOGVOERING' en losse inline CAPS in prose
# zoals 'MILITAIR/ECONOMISCH', maar laat losse één-letterwoorden ('I', 'A')
# en woorden-met-één-hoofdletter ('David') ongemoeid.
_SHOUTY_PHRASE_RE = re.compile(r"[A-Z]{2,}(?:[ /_\-]+[A-Z]{2,})*")


def _is_caps_phrase(s: Any) -> bool:
    """Detecteer een 'schreeuwende' meerwoordsfrase (CMT-conceptmetafoor of
    domeinnaam): álle alfabetische tekens zijn hoofdletters en er zijn er minstens
    drie. Komt los van _is_enum_waarde, die alleen pure enum-tokens vangt."""
    if not isinstance(s, str):
        return False
    letters = [c for c in s if c.isalpha()]
    if len(letters) < 3:
        return False
    return all(c.isupper() for c in letters)


def _format_caps_phrase_md(s: str) -> str:
    """Verzachte weergave voor een entire-CAPS waarde: lowercase, eerste letter
    een hoofdletter, gewikkeld in violet zodat het als concept- of domeinnaam
    visueel onderscheidt zonder te schreeuwen.
    'OPSLAG EN TRANSPORT VAN OBJECTEN' -> ':violet[Opslag en transport van objecten]'."""
    if not s:
        return ""
    laag = s.lower()
    schoon = laag[:1].upper() + laag[1:]
    return f":violet[{schoon}]"


def _soften_prose(text: str) -> str:
    """Verzacht inline CAPS-frasen in een prose-tekst. Alleen de matchende
    delen worden in violet en lowercase gezet; omliggende prose blijft intact.
    Gebruikt voor velden als slotopmerking, audit_samenvatting en
    coherentie_verklaring waar de prediker-evaluator soms inline tokens als
    'MILITAIR/ECONOMISCH' of 'GOD IS EEN TRILLING' invoegt."""
    if not text:
        return text
    return _SHOUTY_PHRASE_RE.sub(lambda m: f":violet[{m.group(0).lower()}]", text)


def _format_value(v: Any) -> str:
    """Format een losse waarde voor weergave. Enum-tokens krijgen een gekleurd
    severity-badge, CAPS-frasen (CMT-conceptnamen) krijgen een zachte violette
    weergave, en andere strings worden via clean_md gerenderd waarbij eventuele
    inline CAPS-frasen alsnog verzacht worden."""
    if _is_enum_waarde(v):
        return _enum_markdown(v)
    if _is_caps_phrase(v):
        return _format_caps_phrase_md(v)
    return _soften_prose(clean_md(str(v)))


def _beoordeling_badge(waarde: str) -> None:
    """Toon overall_beoordeling als gekleurde badge met een nette labelvariant."""
    if not waarde:
        return
    st.markdown(f"**Eindoordeel:** {_enum_markdown(waarde)}")


def _render_list_of_dicts(items: list, skip_keys: set | None = None) -> None:
    """Render een lijst van dicts als gestileerde blokken."""
    skip_keys = skip_keys or set()
    for item in items:
        if not isinstance(item, dict):
            if item:
                st.markdown(f"- {_format_value(item)}")
            continue
        lines = []
        for k, v in item.items():
            if k in skip_keys:
                continue
            k_label = k.replace("_", " ").capitalize()
            if isinstance(v, list):
                if v:
                    lines.append(f"**{k_label}:** " + ", ".join(_format_value(x) for x in v))
            elif v:
                lines.append(f"**{k_label}:** {_format_value(v)}")
        if lines:
            st.markdown("  \n".join(lines))
            st.divider()


def feedback_metafoor(analysis: dict[str, Any]) -> None:
    """Renderer voor metafoor-feedback (Conceptual Metaphor Theory)."""
    result = analysis.get("result", {})
    if not isinstance(result, dict) or not result:
        st.info("Geen resultaat beschikbaar.")
        return

    aanbev = result.get("aanbevelingen", {})
    diag = result.get("diagnostische_evaluatie", {})

    # --- Koptekst: eindoordeel + slotopmerking ---
    overall = aanbev.get("overall_beoordeling", "")
    if overall:
        _beoordeling_badge(overall)

    slotopmerking = aanbev.get("slotopmerking", "")
    if slotopmerking:
        # Inline CAPS-frasen in de prose ('MILITAIR/ECONOMISCH') verzachten,
        # zodat de tekst niet meer schreeuwt midden in een lopende zin.
        st.info(_soften_prose(clean_md(slotopmerking)))

    audit_samenvatting = aanbev.get("metafoor_audit_samenvatting", "")
    if audit_samenvatting:
        st.markdown(_soften_prose(clean_md(audit_samenvatting)))

    # --- Sterktes ---
    sterktes = diag.get("sterktes", [])
    if sterktes:
        with st.expander("Sterktes", expanded=True):
            for s in sterktes:
                if not isinstance(s, dict):
                    st.markdown(f"+ {clean_md(str(s))}")
                    continue
                type_label = s.get("sterkte_type", "")
                beschrijving = s.get("beschrijving", "")
                voorbeeld = s.get("voorbeeld", "")
                # Type-enum (HELDERHEID, EMOTIONELE_RESONANTIE, ...) prettifyen zodat
                # het label niet in CAPS schreeuwt; staat al in een st.success-kader.
                header = f"**{_format_enum_label(type_label)}**" if type_label else ""
                body = _soften_prose(clean_md(beschrijving)) if beschrijving else ""
                if header or body:
                    st.success(f"{header}  \n{body}" if header and body else header or body)
                if voorbeeld:
                    st.caption(f"> {_soften_prose(clean_md(voorbeeld))}")

    # --- Risico's ---
    risicos = diag.get("risicos", [])
    if risicos:
        with st.expander("Risico's", expanded=True):
            for r in risicos:
                if not isinstance(r, dict):
                    st.markdown(f"△ {clean_md(str(r))}")
                    continue
                type_label = r.get("risico_type", "")
                beschrijving = r.get("beschrijving", "")
                ernst = r.get("ernst", "")
                voorbeeld = r.get("voorbeeld", "")
                # Type-enum prettifyen; ernst (GERING/MATIG/ERNSTIG/KRITIEK) krijgt
                # een gekleurde badge zodat de severity opvalt zonder CAPS.
                header_parts: list[str] = []
                if type_label:
                    header_parts.append(f"**{_format_enum_label(type_label)}**")
                if ernst:
                    header_parts.append(f"— {_enum_markdown(ernst)}")
                header = " ".join(header_parts)
                body = _soften_prose(clean_md(beschrijving)) if beschrijving else ""
                st.warning(f"{header}  \n{body}" if body else header)
                if voorbeeld:
                    st.caption(f"> {_soften_prose(clean_md(voorbeeld))}")

    # --- Entailment checks ---
    entailment_checks = aanbev.get("entailment_checks", [])
    if entailment_checks:
        with st.expander("Entailment checks", expanded=False):
            _render_list_of_dicts(entailment_checks)

    # --- Coherentie verbeteringen ---
    coherentie_verb = aanbev.get("coherentie_verbeteringen", [])
    if coherentie_verb:
        with st.expander("Coherentie verbeteringen", expanded=False):
            _render_list_of_dicts(coherentie_verb)

    # --- Revitalisatie suggesties ---
    revitalisatie = aanbev.get("revitalisatie_suggesties", [])
    if revitalisatie:
        with st.expander("Revitalisatie suggesties", expanded=False):
            _render_list_of_dicts(revitalisatie)

    # --- Alternatieve domeinen ---
    alt_domeinen = aanbev.get("alternatieve_domeinen", [])
    if alt_domeinen:
        with st.expander("Alternatieve domeinen", expanded=False):
            _render_list_of_dicts(alt_domeinen)

    # --- Coherentie analyse ---
    coh = diag.get("coherentie_analyse", {})
    if coh:
        with st.expander("Coherentie analyse", expanded=False):
            overall_coh = coh.get("overall_coherentie", "")
            if overall_coh:
                st.markdown(f"**Overall:** {_enum_markdown(overall_coh)}")
            verklaring = coh.get("coherentie_verklaring", "")
            if verklaring:
                st.markdown(_soften_prose(clean_md(verklaring)))
            incoherentie_punten = coh.get("incoherentie_punten", [])
            if incoherentie_punten:
                st.markdown("**Incoherentie punten:**")
                _render_list_of_dicts(incoherentie_punten)
            blending = coh.get("succesvolle_blending", [])
            if blending:
                st.markdown("**Succesvolle blending:**")
                _render_list_of_dicts(blending)

    # --- Primaire analyse: metafoor-inventaris ---
    prim = result.get("primaire_analyse", {})
    inventaris = prim.get("metafoor_inventaris", [])
    if inventaris:
        with st.expander(f"Metafoor-inventaris ({len(inventaris)} metaforen)", expanded=False):
            for i, m in enumerate(inventaris, 1):
                if not isinstance(m, dict):
                    continue
                expressie = m.get("metafoor_expressie", f"Metafoor {i}")
                vitaliteit = m.get("vitaliteit_status", "")
                # Vitaliteit (LEVEND/CONVENTIONEEL/DOOD) als gekleurde badge naast
                # de expressie, in plaats van schreeuwerige italic-CAPS.
                vitaliteit_md = f" {_enum_markdown(vitaliteit)}" if vitaliteit else ""
                # Expressie kan een quote zijn (mixed case) of soms een CAPS-frase;
                # _soften_prose laat normale tekst ongemoeid en verzacht alleen CAPS.
                st.markdown(f"**{i}. {_soften_prose(clean_md(expressie))}**{vitaliteit_md}")
                bron = m.get("brondomein", {})
                doel = m.get("doeldomein", {})
                if isinstance(bron, dict) and bron.get("naam"):
                    # Brondomein-naam staat conventioneel in CAPS; via _format_value
                    # wordt dat een violette concept-badge ("Opslag en transport...").
                    st.markdown(f"Brondomein: {_format_value(bron['naam'])}")
                if isinstance(doel, dict) and doel.get("theologisch_concept"):
                    st.markdown(f"Doeldomein: {_format_value(doel['theologisch_concept'])}")
                onbedoeld = m.get("entailments", {})
                if isinstance(onbedoeld, dict):
                    conseq = onbedoeld.get("onbedoelde_consequenties", [])
                    if conseq:
                        st.markdown("Onbedoelde consequenties: " + ", ".join(_format_value(c) for c in conseq))
                st.divider()

