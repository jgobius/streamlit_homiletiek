from typing import Any

import streamlit as st


def _fmt(key: str) -> str:
    return key.replace("_", " ").capitalize()


def _render_list(values: list) -> None:
    for item in values:
        st.markdown(f"- {item}")


def liturgisch_jaar(analysis: dict[str, Any]) -> None:
    """Render liturgisch jaar analysis result."""
    result: dict[str, Any] = analysis.get("result", {})
    sermon: dict[str, Any] = analysis.get("sermon_analysis", {})

    positie: dict = result.get("positie_kerkelijk_jaar", {})
    traditionele_naam: dict = result.get("traditionele_naam", {})
    kleur: dict = result.get("liturgische_kleur", {})
    thematiek: dict = result.get("thematiek", {})
    lezingen: dict = result.get("lezingen", {})
    historisch: dict = result.get("historische_achtergrond", {})
    praktisch: dict = result.get("praktische_handvatten", {})
    preekvoorbereiding: dict = result.get("preekvoorbereiding", {})
    bijzonder: dict = result.get("bijzondere_zondag_pkn", {})

    # ── Header ────────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        if positie.get("zondag_naam"):
            st.metric("Zondag", positie["zondag_naam"])
    with col2:
        if kleur.get("kleur"):
            st.metric("Liturgische kleur", kleur["kleur"].capitalize())
    with col3:
        if positie.get("weken_tot_hoofdfeest"):
            st.metric("Feest", positie["weken_tot_hoofdfeest"])

    if traditionele_naam.get("latijnse_naam"):
        latijn = traditionele_naam["latijnse_naam"]
        vertaling = traditionele_naam.get("nederlandse_vertaling", "")
        st.info(f"**{latijn}** — *{vertaling}*")

    if bijzonder.get("is_bijzonder") and bijzonder.get("naam"):
        st.warning(f"Bijzondere zondag PKN: **{bijzonder['naam']}** — {bijzonder.get('toelichting', '')}")

    st.divider()

    # ── Thematiek ────────────────────────────────────────────────────────────
    with st.expander("🎯 Thematiek", expanded=False):
        if thematiek.get("centraal_thema"):
            st.markdown(f"**Centraal thema:** {thematiek['centraal_thema']}")
        if thematiek.get("stemming"):
            st.markdown(f"**Stemming:** {thematiek['stemming']}")
        if thematiek.get("karakter_zondag"):
            st.markdown(f"**Karakter:** {thematiek['karakter_zondag']}")
        if thematiek.get("rode_draad_liturgisch_jaar"):
            st.markdown(f"**Rode draad:** {thematiek['rode_draad_liturgisch_jaar']}")
        vragen: list = thematiek.get("centrale_geloofsvragen", [])
        if vragen:
            st.markdown("**Centrale geloofsvragen:**")
            _render_list(vragen)

    # ── Lezingen ─────────────────────────────────────────────────────────────
    with st.expander("📖 Lezingen", expanded=False):
        lezing_keys = ["eerste_lezing", "epistel", "evangelie", "psalm"]
        labels = {
            "eerste_lezing": "Eerste lezing",
            "epistel": "Epistel",
            "evangelie": "Evangelie",
            "psalm": "Psalm",
        }
        for key in lezing_keys:
            lezing = lezingen.get(key)
            if not lezing:
                continue
            with st.container(border=True):
                ref = lezing.get("referentie", labels[key])
                thema = lezing.get("thema", "")
                st.markdown(f"**{labels[key]}: {ref}**" + (f" — *{thema}*" if thema else ""))
                for field in ("context", "theologische_accenten", "relatie_tot_thema", "relatie_liturgische_periode"):
                    val = lezing.get(field)
                    if val:
                        st.markdown(f"*{_fmt(field)}:* {val}")

        samenhang = lezingen.get("thematische_samenhang")
        if samenhang:
            st.markdown(f"**Thematische samenhang:** {samenhang}")
        relatie = lezingen.get("relatie_tot_liturgische_periode")
        if relatie:
            st.markdown(f"**Relatie tot liturgische periode:** {relatie}")

    # ── Preekvoorbereiding ────────────────────────────────────────────────────
    with st.expander("✍️ Preekvoorbereiding", expanded=False):
        if preekvoorbereiding.get("aanbevolen_preektekst"):
            st.markdown(f"**Aanbevolen preektekst:** {preekvoorbereiding['aanbevolen_preektekst']}")
        if preekvoorbereiding.get("reden_keuze"):
            st.markdown(f"**Reden keuze:** {preekvoorbereiding['reden_keuze']}")
        punten: list = preekvoorbereiding.get("actuele_aanknopingspunten", [])
        if punten:
            st.markdown("**Actuele aanknopingspunten:**")
            _render_list(punten)
        exegese: list = preekvoorbereiding.get("exegetische_aandachtspunten", [])
        if exegese:
            st.markdown("**Exegetische aandachtspunten:**")
            _render_list(exegese)
        verbindingen: list = preekvoorbereiding.get("verbindingen_tussen_lezingen", [])
        if verbindingen:
            st.markdown("**Verbindingen tussen lezingen:**")
            _render_list(verbindingen)

    # ── Lijurgische kleur ─────────────────────────────────────────────────────
    with st.expander("🎨 Liturgische kleur", expanded=False):
        if kleur.get("symboliek"):
            st.markdown(f"**Symboliek:** {kleur['symboliek']}")
        suggesties: list = kleur.get("praktische_suggesties", [])
        if suggesties:
            st.markdown("**Praktische suggesties:**")
            _render_list(suggesties)

    # ── Praktische handvatten ─────────────────────────────────────────────────
    with st.expander("🛠️ Praktische handvatten", expanded=False):
        if praktisch.get("liturgische_orde_suggestie"):
            st.markdown(f"**Liturgische orde:** {praktisch['liturgische_orde_suggestie']}")

        aanpassingen: list[dict] = praktisch.get("aanpassingen_periode", [])
        if aanpassingen:
            st.markdown("**Aanpassingen voor de periode:**")
            for a in aanpassingen:
                st.markdown(f"- *{a.get('element', '')}*: {a.get('aanpassing', '')} *(reden: {a.get('reden', '')})*")

        gebeden: list = praktisch.get("gebedsmotieven", [])
        if gebeden:
            st.markdown("**Gebedsmotieven:**")
            _render_list(gebeden)

        visueel: list = praktisch.get("visuele_elementen", [])
        if visueel:
            st.markdown("**Visuele elementen:**")
            _render_list(visueel)

        knd: dict = praktisch.get("kindernevendienst", {})
        if knd:
            st.markdown("**Kindernevendienst:**")
            if knd.get("thema"):
                st.markdown(f"*Thema:* {knd['thema']}")
            for s in knd.get("suggesties", []):
                st.markdown(f"- {s}")

    # ── Historische achtergrond ───────────────────────────────────────────────
    with st.expander("📜 Historische achtergrond", expanded=False):
        for key in ("oorsprong_vroege_kerk", "hervormde_traditie", "gereformeerde_traditie", "lutherse_traditie", "oecumenische_dimensie"):
            val = historisch.get(key)
            if val:
                st.markdown(f"**{_fmt(key)}:** {val}")

    # ── Traditionele naam ─────────────────────────────────────────────────────
    with st.expander("🏷️ Traditionele naam", expanded=False):
        if traditionele_naam.get("oorsprong"):
            st.markdown(f"**Oorsprong:** {traditionele_naam['oorsprong']}")
        volksnamen: list = traditionele_naam.get("volksnamen", [])
        if volksnamen:
            st.markdown("**Volksnamen:**")
            _render_list(volksnamen)
