import copy
import json

import requests
import streamlit as st

_RENDER_SKIP: set[str] = {"_meta", "_usage"}


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
            return st.text_area(" ", value=data, key=f"je_{ses}_{key_prefix}", label_visibility="collapsed", height=h)
        else:
            return st.text_input(" ", value=data, key=f"je_{ses}_{key_prefix}", label_visibility="collapsed")
    elif data is None:
        val = st.text_input(" ", value="", key=f"je_{ses}_{key_prefix}", label_visibility="collapsed", placeholder="(leeg)")
        return None if not val else val
    else:
        st.code(json.dumps(data, ensure_ascii=False, indent=2))
        return data


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
        # Pre-fill extra_context from the sermon_analysis object
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
    )

    st.divider()
    st.markdown("**Analyseresultaten aanpassen**")
    edited_data = _render_json_field(original_data, "", ses)

    col_save, col_cancel = st.columns(2)
    if col_save.button("Opslaan", type="primary", use_container_width=True):
        st.session_state["extra_context"] = extra_context_val
        try:
            handler = st.session_state["api_handler"]
            sermon_analysis_id = result["sermon_analysis"]["id"]
            
            # Update the sermon-wide extra context
            handler.patch(f"api/sermon-analyses/{sermon_analysis_id}/", data={"extra_context": extra_context_val})
            
            # Update the specific analysis result
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
