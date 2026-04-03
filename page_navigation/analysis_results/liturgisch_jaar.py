from typing import Any

import streamlit as st

from src.utils.utils import get_cached_data, redirect_to_login


redirect_to_login()


EXAMPLE_DATA: dict[str, Any] = {
    "lezingen": {
        "eerste_lezing": {
            "boek": "Genesis",
            "thema": "De val van de mens en de eerste zonde",
            "verzen": "1-7",
            "context": "Het verhaal van de verleiding en de ongehoorzaamheid van Adam en Eva in de tuin van Eden, waarin de slang Eva misleidt om de verboden vrucht te eten.",
            "hoofdstuk": 3,
            "referentie": "Genesis 3:1-7",
            "relatie_tot_thema": "Genesis 3 is een kerntekst over zonde en ongehoorzaamheid: de keuze van de mens om tegen Gods gebod in te gaan.",
            "theologische_accenten": "De tekst legt nadruk op verleiding, de menselijke zwakte en het verlies van onschuld.",
            "relatie_liturgische_periode": "De lezing past bij de Veertigdagentijd, een periode van bezinning over zonde en bekering.",
        },
        "evangelie": {
            "boek": "Johannes",
            "thema": "Gods liefde en verlossing door Christus",
            "verzen": "16-18",
            "context": "Jezus spreekt over zijn missie van redding en de betekenis van geloof binnen de context van zijn gesprek met Nicodemus.",
            "hoofdstuk": 3,
            "referentie": "Johannes 3:16-18",
            "relatie_tot_thema": "Johannes 3:16-18 benadrukt de gegeven genade en liefde van God, een tegenwicht voor de zondigheid van de mens zoals beschreven in Genesis 3.",
            "theologische_accenten": "Klemtoon op Gods liefde, genade en de weg naar redding door geloof in Christus.",
            "relatie_liturgische_periode": "Het evangelie roept op tot geloof en bekering, passend bij de Veertigdagentijd als voorbereiding op Pasen.",
        },
        "thematische_samenhang": "De lezingen behandelen het thema van zonde en verlossing: Genesis 3 beschrijft de val van de mens en Johannes 3 de oplossing in Christus.",
        "relatie_tot_liturgische_periode": "Bezinning op zonde en redding tijdens de Veertigdagentijd, waarbij de lezingen aansporen tot inkeer en vernieuwing door Christus.",
    },
    "thematiek": {
        "stemming": "Inkeer",
        "centraal_thema": "Zonde en Verlossing",
        "karakter_zondag": "Een moment van reflectie over de menselijke natuur en Gods antwoord daarop.",
        "centrale_geloofsvragen": [
            "Wat betekent zonde in ons leven?",
            "Hoe ervaren we Gods liefde en verlossing?",
            "Hoe kunnen we ons verdiepen in geloof tijdens de lijdenstijd?",
        ],
        "rode_draad_liturgisch_jaar": "De lezingen nodigen uit tot reflectie en bekering als voorbereiding op de viering van Pasen.",
    },
    "liturgische_kleur": {
        "kleur": "paars",
        "symboliek": "Boete, bezinning en voorbereiding",
        "praktische_suggesties": [
            "Gebruik paarse antependia en stola's in de dienst.",
            "Overweeg sobere bloemstukken of takken zonder bloemen.",
            "Gebruik donkere tinten in kaarsen en andere zaalversieringen.",
        ],
    },
    "traditionele_naam": {
        "oorsprong": "Geen specifieke traditionele naam geassocieerd met deze zondag buiten het reguliere liturgische schema.",
        "volksnamen": [],
        "latijnse_naam": None,
        "nederlandse_vertaling": "n.v.t.",
    },
    "preekvoorbereiding": {
        "reden_keuze": "De gekozen lezingen reflecteren de thematiek van zonde en verlossing, passend bij de Veertigdagentijd.",
        "aanbevolen_preektekst": "Genesis 3:1-7",
        "actuele_aanknopingspunten": [
            "Verleiding en morele keuzes in onze moderne context.",
            "De rol van schuld en boetedoening in ons persoonlijk en gemeenschappelijk leven.",
            "Hoe de boodschap van Johannes 3:16 onze kijk op zonde kan veranderen.",
        ],
        "exegetische_aandachtspunten": [
            "Contrasten tussen zondeval in Genesis en verlossing in Johannes.",
            "De literaire structuren en symboliek in het verhaal van Genesis.",
            "Betekenis van geloof in de context van Johannes' boodschap.",
        ],
        "verbindingen_tussen_lezingen": [
            "De tegenstelling tussen de val in Genesis en de verlossing door Christus in Johannes.",
            "De invloed van menselijke keuzes op de verhouding met God en elkaar.",
        ],
    },
    "bijzondere_zondag_pkn": {
        "naam": None,
        "toelichting": None,
        "is_bijzonder": False,
    },
    "praktische_handvatten": {
        "gebedsmotieven": [
            "Zondebesef en de vraag om vergeving.",
            "Dankbaarheid voor Gods liefde en genade.",
            "Verantwoordelijkheid in onze levenskeuzes.",
        ],
        "kindernevendienst": {
            "thema": "Verleiding en Keuze",
            "suggesties": [
                "Vertel het verhaal van Adam en Eva op een kindvriendelijke manier.",
                "Bespreek wat verleiding is en hoe we goede keuzes kunnen maken.",
            ],
        },
        "visuele_elementen": [
            "Gebruik afbeeldingen van de tuin van Eden en kruisen als symbolen voor zonde en verlossing.",
            "Toon kunstwerken of projecties die 'verleiding' en 'redding' uitbeelden.",
        ],
        "aanpassingen_periode": [
            {
                "reden": "Focus op boete en inkeer in de Lijdenstijd",
                "element": "Gloria",
                "aanpassing": "niet gebruiken",
            },
            {
                "reden": "Focus op boete en inkeer in de Lijdenstijd",
                "element": "Halleluja voor evangelie",
                "aanpassing": "niet gebruiken",
            },
        ],
        "liturgische_orde_suggestie": "Begin met de intochtspsalm, gevolgd door de schriftlezingen. Gebruik een verkorte of ingetogen lofprijzing, gericht op wat tijdens de Veertigdagentijd passend is. Laat de preek duidelijke verbindingen maken tussen de aard van zonde en noodzaak van verlossing.",
    },
    "positie_kerkelijk_jaar": {
        "zondag_naam": "3e zondag van de Veertigdagentijd",
        "leesrooster_jaar": "Eigen lezingen (n.v.t.)",
        "dominant_evangelie": "Johannes",
        "liturgische_periode": "Veertigdagentijd",
        "weken_tot_hoofdfeest": "5 weken voor Pasen",
    },
    "historische_achtergrond": {
        "lutherse_traditie": "De Veertigdagentijd is een periode van inkeer en vernieuwing, een tijd waarin de gelovige zijn relatie met God door Christus verdiept.",
        "hervormde_traditie": "De Veertigdagentijd wordt gezien als een tijd voor spirituele reflectie gericht op de lijdensweg van Christus.",
        "oecumenische_dimensie": "De periode wordt wereldwijd gevierd in vele tradities als een overgang van zonde naar verlossing door Christus.",
        "oorsprong_vroege_kerk": "De Veertigdagentijd vindt zijn oorsprong in de voorbereidingstijd voor Pasen in de vroege kerk, een tijd van vasten en gebed.",
        "gereformeerde_traditie": "Het accent ligt op het persoonlijke geloof en de erkenning van zonde, met de focus op innerlijke boetvaardigheid en vernieuwing.",
    },
}


def format_label(value: str) -> str:
    return value.replace("_", " ").capitalize()


def render_list(values: list[Any]) -> None:
    if not values:
        st.write("- Geen gegevens")
        return

    if all(not isinstance(item, dict) for item in values):
        for item in values:
            st.write(f"- {item}")
        return

    for index, item in enumerate(values, start=1):
        with st.container(border=True):
            st.markdown(f"**Item {index}**")
            if isinstance(item, dict):
                render_dict(item)
            else:
                st.write(item)


def render_dict(data: dict[str, Any]) -> None:
    for key, value in data.items():
        label = format_label(key)

        if isinstance(value, dict):
            with st.expander(label, expanded=False):
                render_dict(value)
        elif isinstance(value, list):
            st.markdown(f"**{label}:**")
            render_list(value)
        else:
            display_value = "n.v.t." if value is None else value
            st.markdown(f"**{label}:** {display_value}")


@st.cache_data
def get_liturgisch_jaar_data() -> tuple[dict[str, Any], bool]:
    # try:
    #     data = get_cached_data("api/liturgisch-jaar/")
    #     if isinstance(data, dict) and len(data) > 0:
    #         return data, True
    # except (KeyError, TypeError, ValueError):
    #     pass

    return EXAMPLE_DATA, False


st.title("Liturgisch jaar")
st.write("Overzicht van lezingen, thematiek en praktische handvatten.")

liturgisch_data, from_api = get_liturgisch_jaar_data()

if from_api:
    st.success("Data geladen via API.")
else:
    st.info("Voorbeelddata wordt getoond (fallback), omdat API-data niet beschikbaar is.")

for section, section_data in liturgisch_data.items():
    section_title = format_label(section)
    with st.expander(section_title, expanded=section == "positie_kerkelijk_jaar"):
        if isinstance(section_data, dict):
            render_dict(section_data)
        elif isinstance(section_data, list):
            render_list(section_data)
        else:
            st.write(section_data)
