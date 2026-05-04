import streamlit as st


def _render_home():
    st.title("Voorbereid voorgaan")
    st.markdown("*Een preek die raakt, begint bij wie er zit*")
    st.markdown(
        "VoorbereidVoorgaan.nl is een experimenteel platform voor contextuele homiletische analyses, "
        "speciaal ontwikkeld voor predikanten en voorgangers. Op basis van locatie, gemeente en datum genereert "
        "het platform een uitgebreide set voorzetten die u helpt aansluiting te vinden tussen de Bijbeltekst en de "
        "concrete levenswereld van uw gemeente."
    )
    st.caption("Een initiatief van Jan-Jaap Gobius du Sart en Wim Otte – zonder commercieel oogmerk.")

    st.divider()
    st.subheader("Drie kernpunten")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Contextueel**")
        st.markdown(
            "Het platform houdt rekening met wie er in uw kerkzaal zit: demografische gegevens, "
            "mentaliteitsprofielen en lokale context worden systematisch meegewogen."
        )
    with col2:
        st.markdown("**Theologisch rigoureus**")
        st.markdown(
            "Het platform put uit een brede homiletische traditie – van Lowry tot Brueggemann, van Noordmans "
            "tot Rutledge – en verbindt exegetische inzichten met hedendaagse preekleer."
        )
    with col3:
        st.markdown("**Uw gemeente**")
        st.markdown(
            "Elke analyse is afgestemd op de specifieke gemeente en locatie die u invoert. "
            "Geen twee analyses zijn gelijk."
        )

    st.divider()
    st.info(
        "**Disclaimer.** De output van VoorbereidVoorgaan.nl is uitsluitend bedoeld als inspiratiemateriaal "
        "ter ondersteuning van uw voorbereiding. De verantwoordelijkheid voor de preek – inhoudelijk, "
        "theologisch en pastoraal – blijft te allen tijde bij de voorganger. Het platform vervangt geen eigen "
        "studie, gebed of pastorale betrokkenheid."
    )

    st.subheader("Aanmelden als early tester")
    st.markdown(
        "VoorbereidVoorgaan.nl is momenteel beschikbaar voor een beperkte groep genodigden. "
        "Aanmelding is alleen mogelijk via een persoonlijke uitnodiging."
    )
    # Voor reeds ingelogde gebruikers (api_handler aanwezig in session_state)
    # vervangen we de inlog-/registreerknoppen door één 'Naar dashboard'-knop.
    # Anders zou een ingelogde gebruiker die via deze landingpage komt opnieuw
    # door een login-flow moeten — onnodig en verwarrend, omdat de sessie al
    # actief is. De auth-check `'api_handler' in st.session_state` is dezelfde
    # die main.py gebruikt om tussen de auth- en gast-navigatielijst te kiezen.
    if 'api_handler' in st.session_state:
        if st.button("Naar dashboard", type="primary", use_container_width=True):
            st.switch_page(
                f"{st.session_state['page_navigation_dir']}/analyses/dashboard.py"
            )
    else:
        # Twee losse knoppen voor gasten: een primaire knop voor inloggen (de
        # meest voorkomende actie voor reeds uitgenodigde gebruikers) en een
        # secundaire knop naar de registratiepagina voor wie nog geen account
        # heeft.
        col_login, col_register = st.columns([1, 1])
        with col_login:
            if st.button("Inloggen", type="primary", use_container_width=True):
                st.switch_page(f"{st.session_state['page_navigation_dir']}/login.py")
        with col_register:
            if st.button("Registreren", type="secondary", use_container_width=True):
                st.switch_page(f"{st.session_state['page_navigation_dir']}/register.py")

    st.divider()
    st.markdown(
        "💳 **Kosten & betaling.** [Gratis voor testgebruikers!] Het platform werkt op basis van kostprijsberekening: u betaalt uitsluitend "
        "de werkelijke kosten van de analyse, zonder winstopslag. De exacte prijs wordt vooraf getoond. "
        "Betaling verloopt veilig via **Mollie / iDEAL**."
    )


def _render_over_ons():
    st.header("Over ons")
    st.markdown(
        "VoorbereidVoorgaan.nl is een initiatief van twee mensen met verschillende maar complementaire "
        "achtergronden, verbonden door een gedeelde overtuiging: dat contextuele prediking er toe doet, "
        "en dat technologie daar op een verantwoorde manier bij kan helpen."
    )

    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.subheader("Jan-Jaap Gobius du Sart")
        st.caption("Technisch architect · Ondernemer · CGK")
        st.markdown(
            "Jan-Jaap is professioneel softwareontwikkelaar, fiscaal jurist en ondernemer. Als technisch "
            "architect van VoorbereidVoorgaan.nl heeft hij het systeem ontworpen en gebouwd: van de "
            "infrastructuur tot de integratie van databronnen en taalmodellen."
        )
        st.markdown(
            "Hij is lid van de Christelijke Gereformeerde Kerken (CGK). De overtuiging dat prediking mensen "
            "werkelijk kan bereiken, vormt de drijfveer voor de technische investering die dit platform vergt."
        )
    with col2:
        st.subheader("Wim Otte")
        st.caption("Predikant · Onderzoeker · PKN")
        st.markdown(
            "Wim is PKN-predikant en universitair hoofddocent klinische epidemiologie aan de Universiteit "
            "Utrecht. Hij combineert praktijkervaring als voorganger met wetenschappelijke expertise "
            "op het gebied van predictiemodellen en generatieve modellen. Hij heeft de databronnen en taalmodellen opgezet."
        )
        st.markdown(
            "Als voorganger kent hij de praktijk van de "
            "wekelijkse preekvoorbereiding van binnenuit."
        )

    st.subheader("Waarom dit project?")
    st.markdown(
        "Beide initiatiefnemers zijn geraakt door hetzelfde probleem: predikanten besteden aanzienlijke tijd "
        "aan voorbereiding, maar de aansluiting tussen preek en gemeente blijft een kwetsbaar punt. De "
        "informatie over de concrete leefwereld van gemeenteleden is moeilijk toegankelijk, en de homiletische "
        "traditie is veelal gefragmenteerd beschikbaar. VoorbereidVoorgaan.nl is een poging om dat gat te "
        "dichten door de voorbereiding te verrijken."
    )

    st.subheader("Non-profit karakter")
    st.markdown(
        "Het platform heeft geen commercieel oogmerk. Alle kosten worden direct doorberekend aan gebruikers, "
        "zonder winstopslag. Er is geen externe investeerder, geen advertentiemodel en geen dataverzameling "
        "voor commerciële doeleinden."
    )


def _render_methode():
    st.header("Methodische achtergrond")

    st.subheader("Kernvraag")
    st.markdown(
        "Waar hebben voorgangers werkelijk behoefte aan tijdens de voorbereiding van een dienst? Die vraag "
        "staat centraal in de opzet van VoorbereidVoorgaan.nl. Het antwoord is niet voor alle predikanten "
        "gelijk. Er zijn echter structurele patronen te identificeren, en die patronen zijn de grondslag voor "
        "het systeem dat wij hebben gebouwd."
    )

    st.subheader("Het probleem: preken die vragen beantwoorden die niemand stelt")
    st.markdown(
        "De Duitse homileticus Friedrich Niebergall (1866–1932) formuleerde al aan het begin van de twintigste eeuw een "
        "diagnose van de prediking: veel preken beantwoorden vragen die niemand stelt. Ze zijn "
        "theologisch solide, exegetisch doordacht – maar ze landen niet, omdat ze geen verbinding maken met "
        "wat gemeenteleden werkelijk bezighoudt."
    )
    st.markdown(
        "Dit inzicht is sindsdien verdiept door decennia van homiletisch onderzoek, maar het probleem is "
        "hardnekkig. Contextuele informatie over de gemeente als geheel is beschikbaar – maar versnipperd, "
        "soms moeilijk toegankelijk en zelden systematisch ontsloten voor de preekvoorbereiding."
    )

    st.subheader("De twee werelden")
    st.markdown("Elke preek speelt zich af op het snijvlak van twee werelden:")
    col1, col2 = st.columns(2, gap="medium")
    with col1:
        st.markdown("**De wereld van de hoorder**")
        st.markdown(
            "Wie zijn de mensen die zondag bij elkaar komen? Wat zijn hun zorgen, hun levensvragen, "
            "hun culturele referentiekader? Welke maatschappelijke thema's spelen in hun directe omgeving?"
        )
    with col2:
        st.markdown("**De wereld van de tekst**")
        st.markdown(
            "Wat zegt de Bijbeltekst – in haar literaire, historische en canonieke context? Welke "
            "theologische claims doet zij? Hoe heeft de kerk door de eeuwen heen met deze tekst geworsteld?"
        )
    st.markdown(
        "De uitdaging van de prediking is het overbruggen van die twee werelden. VoorbereidVoorgaan.nl legt "
        "bijzondere nadruk op de wereld van de hoorder – omdat die informatie voor de meeste voorgangers het "
        "moeilijkst toegankelijk is."
    )

    st.subheader("Homiletische tradities")
    st.markdown("Het platform put uit een brede internationale homiletische traditie, waaronder:")

    tradities = [
        ("Eugene Lowry", "De narratieve beweging van de preek als het oplossen van een spanning"),
        ("David Buttrick", "De fenomenologische analyse van hoe beelden zich in het bewustzijn vestigen"),
        ("Walter Brueggemann", "De profetische verbeelding en de subversieve kracht van de Bijbelse taal"),
        ("Fleming Rutledge", "De orthodoxe theologie van verzoening en gerechtigheid als homiletisch fundament"),
        ("Oepke Noordmans", "De dialectische theologie en de radicaliteit van genade in de Nederlandse context"),
        ("Dorothee Sölle", "De politieke theologie en de stem van de lijdende in de prediking"),
    ]
    for naam, omschrijving in tradities:
        st.markdown(f"- **{naam}** – {omschrijving}")

    st.subheader("Contextanalyse: databronnen")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**CBS-data**")
        st.markdown(
            "Demografische gegevens per gemeente en regio: leeftijdsopbouw, huishoudsamenstelling, "
            "opleidingsniveau, inkomensverdeling, migratie-achtergrond."
        )
    with col2:
        st.markdown("**Motivaction**")
        st.markdown(
            "Het Mentality-model onderscheidt acht mentaliteitsgroepen in de Nederlandse samenleving op "
            "basis van waarden, levensstijl en wereldbeeld, gekoppeld aan de locatie van de gemeente."
        )
    with col3:
        st.markdown("**Politiek stemgedrag**")
        st.markdown(
            "Uitslag van gemeenteraads- en Tweede Kamerverkiezingen per stembureau bieden inzicht in "
            "politieke cultuur en maatschappelijke oriëntatie in het directe verzorgingsgebied."
        )

    st.subheader("Kwaliteitsbewaking")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Adversarial red team**")
        st.markdown(
            "Een deel van het systeem is ingericht als kritische tegenstem: het stelt vragen bij de output, "
            "zoekt naar inconsistenties en signaleert theologische of contextuele onzorgvuldigheden."
        )
    with col2:
        st.markdown("**Feedback**")
        st.markdown(
            "Gebruikers kunnen per analysesectie feedback geven. Deze feedback wordt verwerkt en "
            "gebruikt voor doorontwikkeling van het systeem."
        )
    with col3:
        st.markdown("**Gecontroleerde bronnen**")
        st.markdown(
            "Het systeem werkt met gestructureerde databronnen om de kans op feitelijke onjuistheden te "
            "minimaliseren. Waar onzekerheid bestaat, kan de voorganger de output corrigeren of het taalmodel van extra informatie voorzien."
        )

def _render_werkwijze():
    st.header("Werkwijze")
    st.markdown(
        "Het platform vraagt weinig van u – de invoer is minimaal, de output is uitgebreid. "
        "Hieronder vindt u een overzicht van de stappen."
    )

    st.markdown("#### Stap 1 – Registreren")
    st.markdown(
        "VoorbereidVoorgaan.nl is momenteel alleen toegankelijk voor genodigden. U heeft een persoonlijke "
        "uitnodigingslink nodig om een account aan te maken."
    )

    st.markdown("#### Stap 2 – Invoer")
    st.markdown("U voert drie gegevens in:")
    st.markdown(
        "- **Locatie** – de gemeente of wijk waar uw kerk staat\n"
        "- **Gemeente** – de kerkelijke gemeenschap waarvoor u de dienst voorbereidt\n"
        "- **Datum** – de datum van de dienst\n\n"
        "Op basis van deze drie gegevens worden de bijbehorende Bijbeltekst, de demografische context en "
        "de mentaliteitsprofielen automatisch geladen. Het systeem is klaar om analyses te genereren."
    )

    st.markdown("#### Stap 3 – Analyse")
    st.markdown("Het systeem is in staat om een uitgebreide homiletische structuur te bieden. Andere handvatten zijn onder andere:")
    st.markdown(
        "- Een contextprofiel van de gemeente en omgeving\n"
        "- Demografische en sociaal-culturele duiding\n"
        "- Exegetische aantekeningen bij de perikoop\n"
        "- Relevante homiletische tradities voor deze tekst\n"
        "- Suggesties voor thematische focus en narratieve opbouw\n"
        "- Theologische aandachtspunten\n"
        "- Pastorale verbindingslijnen\n"
        "- Specifieke perspectieven (bijv. receptiegeschiedenis, ecologisch, politiek)\n\n"
        "Het genereren duurt doorgaans 1–3 minuten per onderdeel."
    )

    st.markdown("#### Stap 4 – Werken met de output")
    st.markdown(
        "De set analyses wordt stap voor stap door de voorganger gemaakt. Het systeem is niet bedoeld om een kant-en-klare preek te genereren. " \
        "Het is meer een verzameling van perspectieven, inzichten en suggesties waaruit u selectief kunt putten. De verantwoordelijkheid voor de preek – "
        "inhoudelijk, theologisch en pastoraal – blijft te allen tijde bij u als voorganger."
    )

    st.divider()
    st.subheader("Kosten en betaling")
    st.markdown(
        "VoorbereidVoorgaan.nl werkt op basis van kostprijsberekening. U betaalt uitsluitend de werkelijke "
        "kosten van het genereren van de analyse – voornamelijk de kosten van de taalmodellen die worden "
        "gebruikt en de gekoppelde databases. Er is geen abonnement en er zijn geen verborgen kosten. "
        "Testgebruikers krijgen een voorschot van twintig euro om het systeem vrijblijvend te testen."
    )
    st.info(
        "**Praktische informatie**\n\n"
        "- **Generatietijd** – doorgaans 1–3 minuten per onderdeel\n"
        "- **Output** – tientallen analyses, leesbaar in de browser\n"
        "- **Leesrooster** – standaard het Oecumenisch Leesrooster\n"
        "- **Bijbelvertaling** – standaard de Nieuwe Bijbelvertaling (NBV21), maar ook aanwezig zijn de Naardense Bijbel, de Statenvertaling en de Herziene Statenvertaling\n"
        "- **Taal** – analyses beschikbaar in het Nederlands"
    )


def _render_vragen():
    st.header("Veelgestelde vragen")

    _qa = [
        (
            "Voor wie is VoorbereidVoorgaan.nl?",
            "Het platform is primair ontwikkeld voor PKN-predikanten, maar staat open voor alle voorgangers in "
            "Nederland die regelmatig een dienst voorbereiden. Ook voorgangers uit aanverwante kerkgenootschappen "
            "(CGK, NGK, e.a.) kunnen baat hebben bij de analyses.",
        ),
        (
            "Is dit een ghostwriter?",
            "Nee – nadrukkelijk niet. VoorbereidVoorgaan.nl levert exegetische aantekeningen, liedsuggesties, "
            "preekschetsen en homiletische structuren als inspiratiemateriaal. De inhoud, de toon, de structuur "
            "en de theologische keuzes van de preek zijn en blijven de verantwoordelijkheid van de voorganger.",
        ),
        (
            "Hoe betrouwbaar is de output?",
            "De output is zorgvuldig samengesteld, maar kent beperkingen. Het systeem werkt met gecontroleerde "
            "databronnen (CBS, Motivaction, verkiezingsdata) en een brede homiletische literatuurbasis. "
            "Desondanks kunnen taalmodellen fouten maken, nuances missen of verkeerde accenten leggen. "
            "Alle output kan aangepast en verwijderd worden voordat het als input dient in de verdere analyse."
            "Behandel de output altijd als hulpmiddel dat uw eigen oordeel niet vervangt.",
        ),
        (
            "Welke gemeenten en locaties worden ondersteund?",
            "Het platform ondersteunt heel Nederland. Voor elke gemeente en elke locatie kan een analyse worden "
            "gegenereerd, op basis van beschikbare CBS-data en mentaliteitsprofielen.",
        ),
        (
            "Wat kost het?",
            "Voor testgebruikers in de testperiode is het gratis. "
            "Daarna betaalt u de werkelijke kostprijs van de analyse – uitsluitend de kosten van de taalmodellen die "
            "worden ingezet. Er is geen abonnement. De kosten liggen in de orde van enkele "
            "euro's per volledige homiletische analyse." 
            "In de praktijk zal een voorganger niet alle onderdelen willen gebruiken als aanvulling op bestaande voorbereiding.",
        ),
        (
            "Hoe betaal ik?",
            "Betaling verloopt via Mollie, met ondersteuning voor iDEAL en andere gangbare betaalmethoden. "
            "Na betaling heeft u credits om nieuwe analyses te starten binnen uw account.",
        ),
        (
            "Hoe meld ik me aan?",
            "VoorbereidVoorgaan.nl is momenteel uitsluitend toegankelijk via een persoonlijke uitnodiging. "
            "Uitnodigingen worden gefaseerd verstuurd aan early testers.",
        ),
        (
            "Is mijn data veilig?",
            "Ja. Wij verzamelen alleen de gegevens die nodig zijn voor het genereren van de analyse (locatie, "
            "gemeente, datum) en voor de verwerking van betalingen. Er vindt geen verkoop of commercieel gebruik "
            "van uw gegevens plaats. Vrijwillige feedback wordt geanonimiseerd opgeslagen en verwerkt. Wij voldoen aan de AVG/GDPR.",
        ),
        (
            "Welke bijbelvertaling wordt gebruikt?",
            "Standaard werkt het platform met de Nieuwe Bijbelvertaling (NBV21). Ook de Naardense Bijbel en de (Herziene) Statenvertaling "
            "zijn beschikbaar. Het onderliggende Grieks voor de NBV21 wordt opgehaald uit de Nestle-Aland Novum Testamentum Graece (NA28)." 
            "Het Grieks bij de (H)SV komt uit de gereconstrueerde Texus Receptus-versie. "
            "Beide vertalingen worden, wat OT-lezingen betreft, gekoppeld aan het Hebreeuws uit de Biblia Hebraica Stuttgartensia."
            "De Bijbelteksten worden bij de start van een nieuwe kerkdienstanalyse van het Internet gehaald en staan niet in een eigen database.",
        ),
        (
            "Welk leesrooster?",
            "Het platform gebruikt het Oecumenisch Leesrooster (in Nederland bekend als de Evangelielijst / RCL). "
            "Dit is het meest gebruikte leesrooster in de PKN. Het is mogelijk om eigen lezingen in te voeren en te gebruiken.",
        ),
        (
            "Kan ik zelf een preektraditie kiezen?",
            "Ja, gedeeltelijk. Bij de invoer kunt u een voorkeur opgeven voor een bepaalde homiletische "
            "benadering (bijv. narratief, thematisch, expositorisch). Een volledig vrije keuze staat op de "
            "ontwikkelroadmap. Er kan een preekschets gemaakt worden in de stijl van Noordmans, maar ook in de stijl van Sölle.",
        ),
        (
            "Hoe wordt feedback gebruikt?",
            "Uw feedback per analysesectie (en optionele toelichting) wordt anoniem verwerkt "
            "voor het verbeteren van de kwaliteit van toekomstige analyses.",
        ),
        (
            "Wat is de relatie met de universiteit?",
            "Wim Otte is verbonden aan de Universiteit Utrecht en Tilburg School of Catholic Theology. VoorbereidVoorgaan.nl is echter geen "
            "onderzoeksproject.",
        ),
    ]

    for vraag, antwoord in _qa:
        with st.expander(vraag):
            st.markdown(antwoord)


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Home", "Over ons", "Methode", "Werkwijze", "Vragen"])

with tab1:
    _render_home()
with tab2:
    _render_over_ons()
with tab3:
    _render_methode()
with tab4:
    _render_werkwijze()
with tab5:
    _render_vragen()

st.divider()
st.caption("Non-profit · Betaling via iDEAL · © 2026 VoorbereidVoorgaan.nl · Jan-Jaap Gobius du Sart & Wim Otte")


