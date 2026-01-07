import copy
import streamlit as st
from constants import (
    DATA_EDUCATION_ROWS,
    DATA_HARD_SKILLS_ROWS,
    DATA_LANGUAGES_ROWS,
    DATA_PROJECTS_ROWS,
    DATA_SKILLS_OVERVIEW_ROWS,
    KEY_EDITED_JSON,
    KEY_FILLED_JSON,
    KEY_FILTERED_PROJECTS_FOR_PDF,
    KEY_JSON_BYTES,
    KEY_LAST_UPLOADED_FILE_NAME,
    KEY_MODEL_LABEL,
    KEY_PDF_BYTES,
    KEY_PDF_COMPANIES_LIST,
    KEY_PDF_DOMAINS_LIST,
    KEY_PDF_NAME,
    KEY_PDF_NEEDS_REFRESH,
    KEY_PDF_PATH,
    KEY_PDF_FILTER_SEL,
    KEY_PROJECT_DOMAINS_FILTER_MAIN,
    KEY_RAW_TEXT,
    KEY_SELECTED_DOMAINS_FOR_PDF,
    KEY_SELECTED_MODEL,
    KEY_COMPUTED_COMPANIES_TEXT_FILTERED_UI,
    KEY_COMPUTED_DOMAINS_TEXT_FILTERED_UI,
    W_CONTACT_PREFIX,
    W_EDUCATION_EDITOR,
    W_FULL_NAME,
    W_HARD_SKILLS_EDITOR,
    W_LANGUAGES_EDITOR,
    W_PROFILE_SUMMARY,
    W_PROJECTS_EDITOR,
    W_SKILLS_OVERVIEW_EDITOR,
    W_TITLE,
    W_FIRST_NAME,
)


def is_new_candidate(uploaded_file) -> bool:
    if not uploaded_file:
        return False
    last_file = st.session_state.get(KEY_LAST_UPLOADED_FILE_NAME, None)
    return uploaded_file.name != last_file


def ensure_edited_json_initialized():
    """Guarantee a single source-of-truth draft for UI edits."""
    if KEY_FILLED_JSON in st.session_state and isinstance(st.session_state[KEY_FILLED_JSON], dict):
        if KEY_EDITED_JSON not in st.session_state or not isinstance(st.session_state[KEY_EDITED_JSON], dict):
            st.session_state[KEY_EDITED_JSON] = copy.deepcopy(st.session_state[KEY_FILLED_JSON])


def _ensure_data_rows(data_key: str, initial_rows: list[dict]) -> list[dict]:
    """Store editor DATA (list[dict]) under a dedicated data_key.

    Never store list[dict] in the widget key itself.
    """
    v = st.session_state.get(data_key, None)
    if isinstance(v, list) and all(isinstance(r, dict) for r in v):
        return v
    st.session_state[data_key] = copy.deepcopy(initial_rows)
    return st.session_state[data_key]


def _reset_editor_widget_key_if_corrupt(widget_key: str):
    """Reset corrupt Streamlit widget state.

    Streamlit keeps internal widget state in st.session_state[widget_key] (dict).
    If something else is there -> editor can crash. We only delete corrupt values.
    """
    v = st.session_state.get(widget_key, None)
    if v is None:
        return
    if not isinstance(v, dict):
        st.session_state.pop(widget_key, None)


def _apply_data_editor_deltas(widget_key: str, rows: list[dict]) -> list[dict]:
    """Apply st.data_editor internal deltas from st.session_state[widget_key] onto rows.

    This helps capture edits that haven't been committed into the returned DataFrame/list yet.
    Works best for simple list[dict] tables.
    """
    state = st.session_state.get(widget_key)
    if not isinstance(state, dict):
        return rows

    out = [dict(r) for r in (rows if isinstance(rows, list) else []) if isinstance(r, dict)]

    deleted = state.get("deleted_rows")
    if isinstance(deleted, list) and deleted:
        # delete highest indices first
        for idx in sorted([i for i in deleted if isinstance(i, int)], reverse=True):
            if 0 <= idx < len(out):
                out.pop(idx)

    edited = state.get("edited_rows")
    if isinstance(edited, dict):
        for idx_str, patch in edited.items():
            try:
                idx = int(idx_str)
            except Exception:
                continue
            if 0 <= idx < len(out) and isinstance(patch, dict):
                out[idx].update(patch)

    added = state.get("added_rows")
    if isinstance(added, list) and added:
        for r in added:
            if isinstance(r, dict):
                out.append(dict(r))

    return out


def clear_candidate_data():
    keys_to_clear = [
        # core
        KEY_FILLED_JSON,
        KEY_EDITED_JSON,
        KEY_JSON_BYTES,
        KEY_PDF_BYTES,
        KEY_PDF_NAME,
        KEY_RAW_TEXT,
        KEY_PDF_PATH,
        KEY_PDF_NEEDS_REFRESH,
        # project filters
        KEY_FILTERED_PROJECTS_FOR_PDF,
        KEY_SELECTED_DOMAINS_FOR_PDF,
        KEY_PROJECT_DOMAINS_FILTER_MAIN,
        KEY_PDF_DOMAINS_LIST,
        KEY_PDF_COMPANIES_LIST,
        KEY_COMPUTED_DOMAINS_TEXT_FILTERED_UI,
        KEY_COMPUTED_COMPANIES_TEXT_FILTERED_UI,
        KEY_PDF_FILTER_SEL,
        # UI widgets for basic fields
        W_FULL_NAME,
        W_FIRST_NAME,
        W_TITLE,
        W_PROFILE_SUMMARY,
        # model
        KEY_SELECTED_MODEL,
        KEY_MODEL_LABEL,
        # ---- editor DATA keys (our source of truth)
        DATA_PROJECTS_ROWS,
        DATA_HARD_SKILLS_ROWS,
        DATA_SKILLS_OVERVIEW_ROWS,
        DATA_LANGUAGES_ROWS,
        DATA_EDUCATION_ROWS,
        # ---- editor WIDGET keys (internal widget state)
        W_PROJECTS_EDITOR,
        W_HARD_SKILLS_EDITOR,
        W_SKILLS_OVERVIEW_EDITOR,
        W_LANGUAGES_EDITOR,
        W_EDUCATION_EDITOR,
    ]

    # also clear dynamic contact keys
    for k in list(st.session_state.keys()):
        if k.startswith(W_CONTACT_PREFIX):
            keys_to_clear.append(k)

    for key in keys_to_clear:
        st.session_state.pop(key, None)
