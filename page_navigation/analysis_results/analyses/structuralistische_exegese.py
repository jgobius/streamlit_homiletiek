from typing import Any

import streamlit as st


def _render_woordstudie(woorden: list[dict]) -> None:
    for woord in woorden:
        with st.container(border=True):
            orig = woord.get("woord_origineel", "")
            translit = woord.get("transliteratie", "")
            vertaling = woord.get("vertaling", "")
            heading = f"**{orig}**"
            if translit:
                heading += f" *({translit})*"
            if vertaling:
                heading += f" — {vertaling}"
            st.markdown(heading)
            if woord.get("semantische_range"):
                st.caption(f"🔤 {woord['semantische_range']}")
            if woord.get("gebruik_elders"):
                st.markdown(f"*Gebruik elders:* {woord['gebruik_elders']}")
            if woord.get("meerduidigheid"):
                st.markdown(f"*Meerduidigheid:* {woord['meerduidigheid']}")


def _render_scenarios(scenarios: list[dict]) -> None:
    for i, s in enumerate(scenarios, 1):
        with st.container(border=True):
            col_left, col_right = st.columns([3, 2])
            with col_left:
                st.markdown(f"**{i}. {s.get('scène', '')}**")
                st.caption(f"🕐 {s.get('tijd', '')}  ·  📍 {s.get('plaats', '')}")
                st.markdown(f"*Actant:* {s.get('actant', '')}")
                st.markdown(f"*Handeling:* {s.get('handeling', '')}")
            with col_right:
                medewerkers = s.get("medewerker", [])
                if medewerkers:
                    st.caption("🤝 " + ", ".join(medewerkers))
                opponenten = s.get("opponent", [])
                if opponenten:
                    st.caption("⚔️ " + ", ".join(opponenten))


def _render_lezing(lezing: dict) -> None:
    referentie = lezing.get("referentie", "Lezing")
    st.subheader(referentie)

    # ── Woordstudie ───────────────────────────────────────────────────────────
    with st.expander("🔤 Woordstudie", expanded=False):
        _render_woordstudie(lezing.get("woordstudie", []))

    # ── Afbakening & vertaling ────────────────────────────────────────────────
    with st.expander("📜 Afbakening & vertaling", expanded=False):
        afbakening: dict = lezing.get("afbakening_vertaling", {})
        if afbakening.get("werkvertaling_cruciaal"):
            st.info(f"📖 *{afbakening['werkvertaling_cruciaal']}*")
        for item in afbakening.get("vertaalvergelijking", []):
            st.markdown(f"**Vertaalvergelijking:** {item.get('vertaling', '')}")
            if item.get("significante_verschillen"):
                st.markdown(f"*Significante verschillen:* {item['significante_verschillen']}")

    # ── Tekstkritiek ──────────────────────────────────────────────────────────
    with st.expander("🔍 Tekstkritiek", expanded=False):
        tekstkritiek: dict = lezing.get("tekstkritiek", {})
        if tekstkritiek.get("conclusie"):
            st.markdown(f"**Conclusie:** {tekstkritiek['conclusie']}")
        varianten: list = tekstkritiek.get("relevante_varianten", [])
        if varianten:
            for v in varianten:
                with st.container(border=True):
                    st.markdown(f"**Vers {v.get('vers', '')}:** {v.get('variant', '')}")
                    st.caption(f"Handschriften: {v.get('handschriften', '')}")
                    st.markdown(f"*Impact:* {v.get('betekenis_impact', '')}")
        else:
            st.caption("Geen relevante tekstkritische varianten.")

    # ── Literaire analyse ─────────────────────────────────────────────────────
    with st.expander("📚 Literaire analyse", expanded=False):
        lit: dict = lezing.get("literaire_analyse", {})
        if lit.get("genre"):
            st.markdown(f"**Genre:** {lit['genre']}")
        if lit.get("genre_conventies"):
            st.markdown(f"**Genre-conventies:** {lit['genre_conventies']}")

        structuur: dict = lit.get("structuur", {})
        if structuur:
            st.markdown("**Structuur**")
            if structuur.get("opbouw"):
                st.markdown(f"*Opbouw:* {structuur['opbouw']}")
            if structuur.get("centrum"):
                st.markdown(f"*Centrum:* {structuur['centrum']}")
            cesuren = structuur.get("cesuren", [])
            if cesuren:
                st.markdown("*Cesuren:*")
                for c in cesuren:
                    st.markdown(f"- {c}")
            if structuur.get("chiasme_inclusio"):
                st.markdown(f"*Chiasme/inclusio:* {structuur['chiasme_inclusio']}")

        kp: dict = lit.get("karakters_plot", {})
        if kp:
            st.markdown("**Karakters & plot**")
            personages = kp.get("personages", [])
            if personages:
                st.markdown("*Personages:* " + ", ".join(personages))
            if kp.get("verhaallijn"):
                st.markdown(f"*Verhaallijn:* {kp['verhaallijn']}")
            if kp.get("karakterisering"):
                st.markdown(f"*Karakterisering:* {kp['karakterisering']}")
            if kp.get("verzwegen_gesuggereerd"):
                st.markdown(f"*Verzwegen/gesuggereerd:* {kp['verzwegen_gesuggereerd']}")

        sr: dict = lit.get("stijl_retoriek", {})
        if sr:
            st.markdown("**Stijl & retorik**")
            middelen = sr.get("literaire_middelen", [])
            if middelen:
                st.markdown("*Literaire middelen:*")
                for m in middelen:
                    st.markdown(f"- {m}")
            if sr.get("retorische_strategie"):
                st.markdown(f"*Retorische strategie:* {sr['retorische_strategie']}")
            if sr.get("effect_lezer"):
                st.markdown(f"*Effect op lezer:* {sr['effect_lezer']}")

    # ── Structuralistische analyse ────────────────────────────────────────────
    with st.expander("🏗️ Structuralistische analyse", expanded=False):
        struct: dict = lezing.get("structuralistische_analyse", {})

        vert: dict = struct.get("verticale_analyse", {})
        if vert:
            st.markdown("**Verticale analyse**")
            for field, label in [
                ("actanten_analyse", "Actanten"),
                ("tijd_plaats_patroon", "Tijd & plaats"),
                ("handelingen_trajecten", "Handelingslijnen"),
                ("medewerkers_opponenten_analyse", "Medewerkers & opponenten"),
            ]:
                if vert.get(field):
                    st.markdown(f"*{label}:* {vert[field]}")

        schema: dict = struct.get("schema_constructie", {})
        if schema:
            st.markdown("**Scenarioschema**")
            _render_scenarios(schema.get("scenarios", []))
            if schema.get("schema_regels"):
                st.caption(f"📌 {schema['schema_regels']}")

        horiz: dict = struct.get("horizontale_analyse", {})
        if horiz:
            st.markdown("**Horizontale analyse**")
            for field, label in [
                ("karakteranalyse", "Karakteranalyse"),
                ("literaire_elementen", "Literaire elementen"),
                ("evaluatieve_dimensie", "Evaluatieve dimensie"),
                ("structurele_samenhang", "Structurele samenhang"),
                ("temporele_ontwikkeling", "Temporele ontwikkeling"),
            ]:
                if horiz.get(field):
                    st.markdown(f"*{label}:* {horiz[field]}")

        synth: dict = struct.get("synthese_interpretatie", {})
        if synth:
            st.markdown("**Synthese**")
            themas = synth.get("centrale_thema_s", [])
            if themas:
                st.markdown("*Centrale thema's:*")
                for t in themas:
                    st.markdown(f"- {t}")
            if synth.get("structurele_patroon"):
                st.markdown(f"*Structureel patroon:* {synth['structurele_patroon']}")
            if synth.get("theologische_betekenis"):
                st.markdown(f"*Theologische betekenis:* {synth['theologische_betekenis']}")

    # ── Theologische analyse ──────────────────────────────────────────────────
    with st.expander("✝️ Theologische analyse", expanded=False):
        theo: dict = lezing.get("theologische_analyse", {})
        for field, label in [
            ("centrale_boodschap", "Centrale boodschap"),
            ("godsbeeld", "Godsbeeld"),
            ("mensbeeld_wereld_heil", "Mensbeeld / wereld / heil"),
            ("plaats_heilsgeschiedenis", "Plaats in heilsgeschiedenis"),
            ("spanning_andere_teksten", "Spanning met andere teksten"),
            ("theologische_controverses", "Theologische controverses"),
        ]:
            if theo.get(field):
                st.markdown(f"**{label}:** {theo[field]}")
        dogma = theo.get("dogmatische_raakvlakken", [])
        if dogma:
            st.markdown("**Dogmatische raakvlakken:** " + " · ".join(dogma))
        lijnen = theo.get("bijbels_theologische_lijnen", [])
        if lijnen:
            st.markdown("**Bijbels-theologische lijnen:**")
            for l in lijnen:
                st.markdown(f"- {l}")


def structuralistische_exegese(analysis: dict[str, Any]) -> None:
    """Render structuralistische exegese analysis result."""
    result: dict[str, Any] = analysis.get("result", {})

    # Titel wordt centraal in overview.py getoond, boven de actieknoppen.
    st.divider()

    # ── Per lezing ────────────────────────────────────────────────────────────
    for lezing in result.get("per_lezing", []):
        _render_lezing(lezing)
        st.divider()

    # ── Samenhang lezingen ────────────────────────────────────────────────────
    samenhang: dict = result.get("samenhang_lezingen", {})
    if samenhang:
        st.subheader("🔗 Samenhang tussen de lezingen")
        if samenhang.get("rode_draad"):
            st.info(samenhang["rode_draad"])
        versterkingen: list = samenhang.get("versterkingen", [])
        if versterkingen:
            st.markdown("**Versterkingen:**")
            for v in versterkingen:
                st.markdown(f"- {v}")
        correcties: list = samenhang.get("correcties", [])
        if correcties:
            st.markdown("**Correcties:**")
            for c in correcties:
                st.markdown(f"- {c}")
