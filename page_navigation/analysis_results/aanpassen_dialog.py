import copy
import json

import requests
import streamlit as st

from src.utils.utils import valideer_tekstinvoer

_RENDER_SKIP: set[str] = {"_meta", "_usage"}

# Woorden-limieten voor de aanpassen-dialog. extra_context is het vrije veld
# dat ook elders voor 500 woorden gecapt wordt; per JSON-veld geven we meer
# ruimte (2000 woorden) omdat sommige velden een volledig bijbelcitaat of
# langer uitgewerkte analyse bevatten.
_MAX_WOORDEN_EXTRA_CONTEXT = 500
_MAX_WOORDEN_JSON_VELD = 2000

# Max_chars voor de widgets in _render_json_field. text_input is bedoeld
# voor korte enkelregelwaardes (labels, kopjes), text_area voor langere
# tekstblokken (citaten, uitleg).
_MAX_CHARS_JSON_INPUT = 500
_MAX_CHARS_JSON_AREA = 12000


def _render_json_field(data, key_prefix: str, ses: int):
    """Recursief renderen van JSON-velden met bevroren keys en bewerkbare waarden."""
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            child_prefix = f"{key_prefix}.{k}" if key_prefix else k
            if k in _RENDER_SKIP:
                result[k] = v
                continue
            k_label = k.replace("_", " ").capitalize()
            if isinstance(v, (dict, list)):
                with st.container(border=True):
                    st.markdown(f"**{k_label}**")
                    result[k] = _render_json_field(v, child_prefix, ses)
            else:
                st.caption(k_label)
                result[k] = _render_json_field(v, child_prefix, ses)
        return result
    elif isinstance(data, list):
        result = []
        for i, item in enumerate(data):
            child_prefix = f"{key_prefix}[{i}]"
            if isinstance(item, dict):
                with st.expander(f"Item {i + 1}", expanded=False):
                    result.append(_render_json_field(item, child_prefix, ses))
            else:
                result.append(_render_json_field(item, child_prefix, ses))
        return result
    elif isinstance(data, bool):
        return st.checkbox(" ", value=data, key=f"je_{ses}_{key_prefix}")
    elif isinstance(data, (int, float)):
        return st.number_input(" ", value=data, step=1 if isinstance(data, int) else None, key=f"je_{ses}_{key_prefix}", label_visibility="collapsed")
    elif isinstance(data, str):
        if len(data) > 80 or "\n" in data:
            h = min(max(len(data) // 3, 68), 400)
            # max_chars geeft een harde cap aan de widget; voorkomt dat de
            # gebruiker ongelimiteerd plakt. De woorden-/SQL-validatie
            # gebeurt aanvullend bij Opslaan zodat de typ-ervaring niet
            # bij elke toetsaanslag onderbroken wordt.
            return st.text_area(" ", value=data, key=f"je_{ses}_{key_prefix}", label_visibility="collapsed", height=h, max_chars=_MAX_CHARS_JSON_AREA)
        else:
            return st.text_input(" ", value=data, key=f"je_{ses}_{key_prefix}", label_visibility="collapsed", max_chars=_MAX_CHARS_JSON_INPUT)
    elif data is None:
        val = st.text_input(" ", value="", key=f"je_{ses}_{key_prefix}", label_visibility="collapsed", placeholder="(leeg)", max_chars=_MAX_CHARS_JSON_INPUT)
        return None if not val else val
    else:
        st.code(json.dumps(data, ensure_ascii=False, indent=2))
        return data


def _valideer_edited_data(data, pad: str = "") -> tuple[bool, str]:
    """Recursief elke string-waarde in de bewerkte JSON-structuur valideren.

    De aanpassen-dialog rendert willekeurig geneste dict/list-structuren
    als invoervelden; bij Opslaan moeten we elke string-waarde afzonderlijk
    door dezelfde woorden- en SQL-injectie-check halen. Het pad (bv.
    'bijbelteksten[0].uitleg') wordt meegegeven in de foutmelding zodat de
    prediker meteen ziet welk veld de melding veroorzaakte.
    """
    if isinstance(data, dict):
        for sleutel, waarde in data.items():
            if sleutel in _RENDER_SKIP:
                continue
            kind_pad = f"{pad}.{sleutel}" if pad else sleutel
            ok, foutmelding = _valideer_edited_data(waarde, kind_pad)
            if not ok:
                return False, foutmelding
        return True, ""
    if isinstance(data, list):
        for i, item in enumerate(data):
            ok, foutmelding = _valideer_edited_data(item, f"{pad}[{i}]")
            if not ok:
                return False, foutmelding
        return True, ""
    if isinstance(data, str):
        return valideer_tekstinvoer(
            data,
            max_woorden=_MAX_WOORDEN_JSON_VELD,
            veldnaam=pad or "Veld",
        )
    return True, ""


@st.dialog("Aanpassen", width="large")
def aanpassen_dialog(result: dict) -> None:
    result_id = result.get("id")
    if st.session_state.get("aanpassen_result_id") != result_id:
        _raw = result.get("result", {})
        if isinstance(_raw, str):
            cleaned = _raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
                if cleaned.endswith("```"):
                    cleaned = cleaned[: cleaned.rfind("```")]
            try:
                _raw = json.loads(cleaned)
            except (json.JSONDecodeError, ValueError):
                pass
        st.session_state["aanpassen_original"] = copy.deepcopy(_raw)
        st.session_state["aanpassen_session"] = st.session_state.get("aanpassen_session", 0) + 1
        st.session_state["aanpassen_result_id"] = result_id
        # Vul extra_context voor uit het sermon_analysis-object
        st.session_state["extra_context"] = result.get("sermon_analysis", {}).get("extra_context", "")

    ses = st.session_state["aanpassen_session"]
    original_data = st.session_state["aanpassen_original"]

    st.markdown("**Extra algemene context**")
    extra_context_val = st.text_area(
        "Geef extra algemene context voor deze analyse",
        value=st.session_state.get("extra_context", ""),
        key="aanpassen_extra_context_input",
        label_visibility="collapsed",
        height=100,
        max_chars=4096,
    )

    st.divider()
    st.markdown("**Analyseresultaten aanpassen**")
    edited_data = _render_json_field(original_data, "", ses)

    col_save, col_cancel = st.columns(2)
    if col_save.button("Opslaan", type="primary", use_container_width=True):
        # Valideer vrije context én elk aangepast JSON-veld vóór we patchen;
        # sluit niets af als de check faalt zodat de gebruiker kan corrigeren.
        ok_ctx, fout_ctx = valideer_tekstinvoer(
            extra_context_val or "",
            max_woorden=_MAX_WOORDEN_EXTRA_CONTEXT,
            veldnaam="Extra context",
        )
        if not ok_ctx:
            st.error(fout_ctx)
            st.stop()
        ok_data, fout_data = _valideer_edited_data(edited_data)
        if not ok_data:
            st.error(fout_data)
            st.stop()
        st.session_state["extra_context"] = extra_context_val
        try:
            handler = st.session_state["api_handler"]
            sermon_analysis_id = result["sermon_analysis"]["id"]

            # Werk de algemene context bij op het preekanalyse-niveau
            handler.patch(f"api/sermon-analyses/{sermon_analysis_id}/", data={"extra_context": extra_context_val})

            # Werk het specifieke analyseresultaat bij
            url = f"api/analysis-results/{result['id']}/?sermon_analysis_id={sermon_analysis_id}"
            handler.patch(url, data={"result": edited_data})

            st.session_state["aanpassen_original"] = None
            st.session_state["aanpassen_result_id"] = None
            st.session_state["analysis_data_dirty"] = True
            st.toast("Opgeslagen.")
            st.rerun()
        except Exception as e:
            st.error(f"Fout bij opslaan: {e}")
    if col_cancel.button("Annuleren", use_container_width=True):
        st.session_state["aanpassen_original"] = None
        st.session_state["aanpassen_result_id"] = None
        st.rerun()
