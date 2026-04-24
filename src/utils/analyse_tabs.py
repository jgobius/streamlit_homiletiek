"""Categorisatie van analyse-types per tabblad.

Deze module is de enige bron van waarheid voor de vraag "welke analyse-naam
hoort bij welk tabblad?". Ze is bewust vrij van Streamlit-imports en andere
side-effects, zodat zowel `page_navigation/analysis_results/overview.py`
als `src/utils/word_export.py` de sets kunnen importeren zonder Streamlit-UI
te triggeren op importtijd.

De *namen* (sleutels) komen overeen met `analysis_type.name` in de backend
(`homiletiek`). De tabbladvolgorde en groepering spiegelt wat de gebruiker
in de Streamlit-UI ziet wanneer een kerkdienstanalyse wordt geopend.
"""

# Perspectieven: 14 culturele/wetenschappelijke invalshoeken. Worden parallel
# aan de basis-analyses uitgevoerd en gegroepeerd onder één tabblad.
_PERSPECTIEVEN_NAMEN: set[str] = {
    "filosofie",
    "culturele_antropologie",
    "receptiegeschiedenis",
    "literaire_theorie",
    "psychologie",
    "ecologie",
    "postkoloniaal",
    "rechtswetenschap",
    "natuurwetenschappen",
    "politieke_speltheorie",
    "mystagogiek",
    "gender_queer_body",
    "digitale_cultuur",
    "ruimtelijke_ordening",
}

# Verdieping: contextduidende en Tavily-gedreven analyses die boven de basis
# uitstijgen. Sociaal-maatschappelijk, waardenoriëntatie en interpretatieve
# synthese zijn hierheen verhuisd uit Basis; zie overview.py voor historie.
_VERDIEPING_NAMEN: set[str] = {
    "kunst_cultuur",
    "kindermoment",
    "wetslezing",
    "kalender",
    "bezinningsmoment",
    "sociaal_maatschappelijk",
    "gemeente_spiritualiteit",
    "politieke_orientatie",
    "waardenorientatie",
    "interpretatieve_synthese",
}

# Gebeden: vier varianten (klassiek, profetisch, dialogisch, eenvoudig) die
# dezelfde renderer delen maar verschillende prompts hebben.
_GEBEDEN_NAMEN: set[str] = {
    "gebeden",
    "gebeden_profetisch",
    "gebeden_dialogisch",
    "gebeden_eenvoudig",
}

# Preekschetsen: de daadwerkelijke homiletische schetsen (Lowry, Buttrick,
# Noordmans, etc.).
_PREEKSCHETSEN_NAMEN: set[str] = {
    "homiletische_lowry",
    "homiletische_buttrick",
    "preek_jungel",
    "preek_fleming_rutledge",
    "preek_brueggemann_poet",
    "preek_literair",
    "preek_noordmans",
    "preek_kosuke_koyama",
    "preek_zornberg",
    "preek_brueggemann",
    "preek_drewermann",
    "preek_gardner_taylor",
    "preek_solle",
    "preek_peterson",
    "preek_standup",
}

# Hulpstukken die visueel onder Preekschetsen horen maar zelf *geen* preek
# zijn: ze leveren input (focus-en-functie, illustraties, representatieve
# aanwezigen) die de predikant gebruikt bij het opstellen van de schets.
_PREEKSCHETS_HULPSTUKKEN: set[str] = {
    "focus_en_functie",
    "illustraties",
    "representatieve_aanwezigen",
}

# Alle analyses die onder het Preekschetsen-tabblad vallen (schetsen +
# hulpstukken). Wordt los gehouden van _PREEKSCHETSEN_NAMEN omdat de
# preekschets-specifieke lock-logica en triggers in overview.py alleen
# op de 'echte' schetsen moeten letten.
_PREEKSCHETSEN_TAB: set[str] = _PREEKSCHETSEN_NAMEN | _PREEKSCHETS_HULPSTUKKEN

# Feedback-analyses: volledige preek + 10 feedback-methoden.
_FEEDBACK_NAMEN: set[str] = {
    "volledige_preek",
    "feedback_adversarial",
    "feedback_dekker",
    "feedback_aristoteles",
    "feedback_kolb",
    "feedback_schulz_von_thun",
    "feedback_transactional",
    "feedback_esthetiek",
    "feedback_metafoor",
    "feedback_narratief",
    "feedback_taalhandeling",
}

# Gewenste volgorde van basis-analyses in de zijbalk en in exports. Postille
# staat altijd onderaan (zie _basis_sort_key in overview.py). Let op: enkele
# backend-namen (theology, commentaries) gebruiken Engels, terwijl de Python
# module-naam Nederlands is — niet harmoniseren, de API is leidend.
_BASIS_ORDER: list[str] = [
    "bijbelteksten",
    "liturgisch_jaar",
    "structuralistische_exegese",
    "theology",
    "commentaries",
    "liedsuggesties",
    "geloofsorientatie",
    "representatieve_hoorders",
    "wereldnieuws",
    "lokaal_nieuws",
]

# Basis-namen als set: _BASIS_ORDER + postille. Expliciet gedefinieerd zodat
# TAB_NAAR_ANALYSES compleet is en de Word-export niet hoeft te filteren via
# "alles wat niet in andere tabs zit".
_BASIS_NAMEN: set[str] = set(_BASIS_ORDER) | {"postille"}

# Alle niet-basis namen, gebruikt in overview.py om basis-analyses te filteren.
_ALL_NON_BASIS: set[str] = (
    _PERSPECTIEVEN_NAMEN
    | _VERDIEPING_NAMEN
    | _PREEKSCHETSEN_TAB
    | _GEBEDEN_NAMEN
    | _FEEDBACK_NAMEN
)

# Volgorde van de tabbladen zoals de gebruiker ze ziet. Exports en andere
# consumers moeten deze volgorde respecteren.
TAB_VOLGORDE: list[str] = [
    "Basis",
    "Verdieping",
    "Perspectieven",
    "Preekschetsen",
    "Gebeden",
    "Feedback",
]

# Publieke mapping tab-label → set van analyse-namen. Het Preekschetsen-
# tabblad bundelt hier zowel de schetsen als hun hulpstukken omdat de
# gebruiker ze onder één tab ziet.
TAB_NAAR_ANALYSES: dict[str, set[str]] = {
    "Basis": _BASIS_NAMEN,
    "Verdieping": _VERDIEPING_NAMEN,
    "Perspectieven": _PERSPECTIEVEN_NAMEN,
    "Preekschetsen": _PREEKSCHETSEN_TAB,
    "Gebeden": _GEBEDEN_NAMEN,
    "Feedback": _FEEDBACK_NAMEN,
}
