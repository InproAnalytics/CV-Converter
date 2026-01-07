import copy
import json
import os

import streamlit as st

from constants import (
    BTN_AUTOFILL_PROJECT_DOMAINS,
    BTN_GENERATE_V3_SUMMARY,
    BTN_SAVE_ALL_PROJECTS_AND_PDF,
    DATA_HARD_SKILLS_ROWS,
    DATA_PROJECTS_ROWS,
    DATA_SKILLS_OVERVIEW_ROWS,
    DATA_LANGUAGES_ROWS,
    DATA_EDUCATION_ROWS,
    DL_JSON,
    DL_PDF,
    KEY_COMPUTED_COMPANIES_TEXT_FILTERED_UI,
    KEY_COMPUTED_DOMAINS_TEXT_FILTERED_UI,
    KEY_EDITED_JSON,
    KEY_FILLED_JSON,
    KEY_FILTERED_PROJECTS_FOR_PDF,
    KEY_JSON_BYTES,
    KEY_PDF_BYTES,
    KEY_PDF_COMPANIES_LIST,
    KEY_PDF_DOMAINS_LIST,
    KEY_PDF_NAME,
    KEY_PDF_NEEDS_REFRESH,
    KEY_SELECTED_DOMAINS_FOR_PDF,
    KEY_V3_SUMMARY_TEXT,
    W_EDUCATION_EDITOR_MAIN,
    W_FULL_NAME,
    W_FIRST_NAME,
    W_HARD_SKILLS_EDITOR,
    W_LANGUAGES_EDITOR_MAIN,
    W_PROFILE_SUMMARY,
    W_PROJECTS_EDITOR,
    W_SKILLS_OVERVIEW_EDITOR,
    W_TITLE,
    W_V3_SUMMARY_AREA,
)

from cv_pdf_generator import create_pretty_first_section
from cv_normalization import (
    _extract_companies_from_projects,
    _extract_domains_from_projects,
    _filter_projects_by_domains,
    _norm_list,
    _project_has_content,
    _remove_empty_fields,
    _responsibilities_to_list,
    _responsibilities_to_text,
    languages_to_pdf_format,
)
from domains_config import _load_domains_config, _save_domains_config
from streamlit_state import (
    _apply_data_editor_deltas,
    _ensure_data_rows,
    _reset_editor_widget_key_if_corrupt,
)


def _project_row_to_ui(p: dict) -> dict:
    if not isinstance(p, dict):
        return {
            "project_title": "",
            "company": "",
            "overview": "",
            "role": "",
            "duration": "",
            "responsibilities": "",
            "tech_stack": [],
            "domains": [],
        }
    return {
        "project_title": str(p.get("project_title", "") or ""),
        "company": str(p.get("company", "") or ""),
        "overview": str(p.get("overview", "") or ""),
        "role": str(p.get("role", "") or ""),
        "duration": str(p.get("duration", "") or ""),
        "responsibilities": _responsibilities_to_text(p.get("responsibilities")),
        "tech_stack": _norm_list(p.get("tech_stack")),
        "domains": _norm_list(p.get("domains")),
    }


def _hard_skills_row_to_ui(row: dict) -> dict:
    if not isinstance(row, dict):
        return {"Kategorie": "", "Werkzeuge": []}
    cat = row.get("Kategorie", "") or row.get("category", "") or ""
    tools = row.get("Werkzeuge", None)
    if tools is None:
        tools = row.get("tools", [])
    tools_list = tools if isinstance(tools, list) else _norm_list(tools)
    tools_list = [str(t).strip() for t in tools_list if str(t).strip()]
    return {"Kategorie": str(cat or ""), "Werkzeuge": tools_list}


def _skills_overview_row_to_ui(row: dict) -> dict:
    if not isinstance(row, dict):
        return {"Kategorie": "", "Werkzeuge": [], "Jahre Erfahrung": ""}
    cat = row.get("Kategorie", "") or row.get("category", "") or ""
    tools = row.get("Werkzeuge", None)
    if tools is None:
        tools = row.get("tools", [])
    years = row.get("Jahre Erfahrung", "") or row.get("years_of_experience", "") or ""
    tools_list = tools if isinstance(tools, list) else _norm_list(tools)
    tools_list = [str(t).strip() for t in tools_list if str(t).strip()]
    return {
        "Kategorie": str(cat or ""),
        "Werkzeuge": tools_list,
        "Jahre Erfahrung": str(years or ""),
    }


def _lang_row_to_editor(row: dict) -> dict:
    if not isinstance(row, dict):
        return {"Sprache": "", "Niveau": ""}
    if "language" in row or "level" in row:
        return {
            "Sprache": str(row.get("language", "") or ""),
            "Niveau": str(row.get("level", "") or ""),
        }
    return {
        "Sprache": str(row.get("Sprache", "") or ""),
        "Niveau": str(row.get("Niveau", "") or ""),
    }


def _edu_row_to_editor(row: dict) -> dict:
    if not isinstance(row, dict):
        return {"Institution": "", "Abschluss": "", "Jahr": ""}
    if any(k in row for k in ("degree", "institution", "year")):
        return {
            "Institution": str(row.get("institution", "") or ""),
            "Abschluss": str(row.get("degree", "") or ""),
            "Jahr": str(row.get("year", "") or ""),
        }
    return {
        "Institution": str(row.get("Institution", "") or ""),
        "Abschluss": str(row.get("Abschluss", "") or ""),
        "Jahr": str(row.get("Jahr", "") or ""),
    }


def render_manual_editing(edited: dict) -> None:
    st.markdown("---")
    st.subheader("🛠 Manuelle Bearbeitung")

    # --- Basic fields ---
    st.session_state.setdefault(W_FULL_NAME, str(edited.get("full_name", "")))
    st.session_state.setdefault(W_FIRST_NAME, str(edited.get("first_name", "")))
    current_title = str(edited.get("title") or edited.get("position") or edited.get("role") or "")
    st.session_state.setdefault(W_TITLE, current_title)
    st.session_state.setdefault(W_PROFILE_SUMMARY, str(edited.get("profile_summary", edited.get("summary", ""))))

    col_a, col_b = st.columns(2)
    with col_a:
        st.text_input("Vollständiger Name", key=W_FULL_NAME)
        st.text_input("Vorname", key=W_FIRST_NAME)
    with col_b:
        st.text_input("Position (title)", key=W_TITLE)

    st.text_area("Kurzbeschreibung (profile_summary)", height=140, key=W_PROFILE_SUMMARY)

    edited["full_name"] = st.session_state[W_FULL_NAME]
    edited["first_name"] = st.session_state[W_FIRST_NAME]
    edited["title"] = st.session_state[W_TITLE]
    edited["profile_summary"] = st.session_state[W_PROFILE_SUMMARY]

    # Contacts
    if isinstance(edited.get("contacts"), dict):
        with st.expander("Kontakte", expanded=False):
            contacts = dict(edited.get("contacts", {}))
            for k, v in contacts.items():
                wkey = f"w_contacts_{k}"
                st.session_state.setdefault(wkey, str(v))
                st.text_input(str(k), key=wkey)
                contacts[k] = st.session_state[wkey]
            edited["contacts"] = contacts

    _render_projects_and_pdf_filter(edited)
    _render_hard_skills(edited)
    _render_skills_overview(edited)
    _render_languages(edited)
    _render_education(edited)
    _render_text_summary()
    _render_save_and_downloads(edited)


def _render_projects_and_pdf_filter(edited: dict) -> None:
    def _mark_pdf_dirty() -> None:
        st.session_state[KEY_PDF_NEEDS_REFRESH] = True

    def _normalize_project_rows(rows) -> list[dict]:
        if not isinstance(rows, list):
            return []
        out = []
        for r in rows:
            if isinstance(r, dict):
                out.append(_project_row_to_ui(r))
        return out

    def _rows_to_records(value):
        if isinstance(value, list):
            return value
        # st.data_editor may return a pandas DataFrame depending on Streamlit version.
        if hasattr(value, "to_dict"):
            try:
                recs = value.to_dict("records")
                return recs if isinstance(recs, list) else []
            except Exception:
                return []
        return []

    with st.expander("Projekte / Erfahrung (projects_experience)", expanded=True):
        _reset_editor_widget_key_if_corrupt(W_PROJECTS_EDITOR)

        base = edited.get("projects_experience", [])
        if not isinstance(base, list):
            base = []

        initial_projects = [_project_row_to_ui(p) for p in base if isinstance(p, dict)]
        if not initial_projects:
            initial_projects = [_project_row_to_ui({})]

        projects_rows = _ensure_data_rows(DATA_PROJECTS_ROWS, initial_projects)
        projects_rows = _normalize_project_rows(projects_rows)
        if not projects_rows:
            projects_rows = [_project_row_to_ui({})]

        # Apply pending editor deltas BEFORE rendering the editor (captures uncommitted edits).
        projects_rows = _normalize_project_rows(_apply_data_editor_deltas(W_PROJECTS_EDITOR, projects_rows))
        if not projects_rows:
            projects_rows = [_project_row_to_ui({})]
        st.session_state[DATA_PROJECTS_ROWS] = projects_rows

        projects_edited = st.data_editor(
            projects_rows,
            num_rows="dynamic",
            width="stretch",
            hide_index=True,
            key=W_PROJECTS_EDITOR,
            on_change=_mark_pdf_dirty,
            column_config={
                "project_title": st.column_config.TextColumn("Projekt"),
                "company": st.column_config.TextColumn("Firma"),
                "overview": st.column_config.TextColumn("Überblick"),
                "role": st.column_config.TextColumn("Rolle"),
                "duration": st.column_config.TextColumn("Dauer"),
                "responsibilities": st.column_config.TextColumn("Responsibilities"),
                "tech_stack": st.column_config.ListColumn("Tech Stack"),
                "domains": st.column_config.ListColumn("Domains"),
            },
        )

        projects_edited_records = _rows_to_records(projects_edited)
        merged_now = _normalize_project_rows(_apply_data_editor_deltas(W_PROJECTS_EDITOR, projects_edited_records))
        if not merged_now:
            merged_now = [_project_row_to_ui({})]
        st.session_state[DATA_PROJECTS_ROWS] = merged_now

        data_projects = []
        for r in merged_now:
            if not isinstance(r, dict):
                continue
            data_projects.append(
                {
                    "project_title": str(r.get("project_title", "") or ""),
                    "company": str(r.get("company", "") or ""),
                    "overview": str(r.get("overview", "") or ""),
                    "role": str(r.get("role", "") or ""),
                    "duration": str(r.get("duration", "") or ""),
                    "responsibilities": _responsibilities_to_list(r.get("responsibilities")),
                    "tech_stack": _norm_list(r.get("tech_stack")),
                    "domains": _norm_list(r.get("domains")),
                }
            )
        edited["projects_experience"] = data_projects

        def _autofill_domains_from_projects():
            rows = st.session_state.get(DATA_PROJECTS_ROWS, [])
            new_domains = set()
            for p in rows:
                if not isinstance(p, dict):
                    continue
                for d in _norm_list(p.get("domains")):
                    if d:
                        new_domains.add(d.strip().title())
            config_domains = set(_load_domains_config())
            _save_domains_config(sorted(config_domains | new_domains))

        st.button(
            "Domänen aus Projekten in domains.json übernehmen",
            key=BTN_AUTOFILL_PROJECT_DOMAINS,
            on_click=_autofill_domains_from_projects,
        )

    projects_for_filter = st.session_state.get(DATA_PROJECTS_ROWS, [])
    domains_options = _extract_domains_from_projects(projects_for_filter)
    prior_sel = st.session_state.get(KEY_SELECTED_DOMAINS_FOR_PDF, [])
    safe_default = [d for d in prior_sel if d in domains_options]
    selected_domains = st.multiselect(
        "Domains-Filter (für PDF)",
        options=domains_options,
        default=safe_default,
        key=KEY_SELECTED_DOMAINS_FOR_PDF,
        on_change=_mark_pdf_dirty,
    )

    with st.container():
        all_projects_now = [p for p in projects_for_filter if _project_has_content(p)]
        selected_domains_list = list(selected_domains or [])
        filtered_projects = _filter_projects_by_domains(all_projects_now, selected_domains_list)
        st.session_state[KEY_FILTERED_PROJECTS_FOR_PDF] = filtered_projects

        if not selected_domains_list:
            st.session_state[KEY_PDF_DOMAINS_LIST] = _extract_domains_from_projects(all_projects_now)
            st.session_state[KEY_PDF_COMPANIES_LIST] = _extract_companies_from_projects(all_projects_now)
        else:
            st.session_state[KEY_PDF_DOMAINS_LIST] = selected_domains_list
            st.session_state[KEY_PDF_COMPANIES_LIST] = _extract_companies_from_projects(filtered_projects)

        st.session_state[KEY_COMPUTED_DOMAINS_TEXT_FILTERED_UI] = "\n".join(
            [str(d) for d in (st.session_state.get(KEY_PDF_DOMAINS_LIST, []) or []) if str(d).strip()]
        )
        st.session_state[KEY_COMPUTED_COMPANIES_TEXT_FILTERED_UI] = "\n".join(
            [str(c) for c in (st.session_state.get(KEY_PDF_COMPANIES_LIST, []) or []) if str(c).strip()]
        )

        col_dom, col_comp = st.columns(2)
        with col_dom:
            st.text_area(
                "Domänen (für PDF)",
                key=KEY_COMPUTED_DOMAINS_TEXT_FILTERED_UI,
                height=110,
                disabled=True,
            )
        with col_comp:
            st.text_area(
                "Firmen (aus gefilterten Projekten)",
                key=KEY_COMPUTED_COMPANIES_TEXT_FILTERED_UI,
                height=110,
                disabled=True,
            )


def _render_hard_skills(edited: dict) -> None:
    with st.expander("Fachliche Kompetenzen (Hard Skills)", expanded=False):
        _reset_editor_widget_key_if_corrupt(W_HARD_SKILLS_EDITOR)

        hs = edited.get("hard_skills", {})
        if not isinstance(hs, dict):
            hs = {}

        initial_rows = []
        for k, v in hs.items():
            tools = v if isinstance(v, list) else ([v] if v else [])
            initial_rows.append({"Kategorie": str(k), "Werkzeuge": [str(x).strip() for x in tools if str(x).strip()]})

        if not initial_rows:
            initial_rows = [{"Kategorie": "", "Werkzeuge": []}]

        hs_rows = _ensure_data_rows(DATA_HARD_SKILLS_ROWS, initial_rows)
        hs_rows = [_hard_skills_row_to_ui(r) for r in hs_rows if isinstance(r, dict)]
        if not hs_rows:
            hs_rows = [{"Kategorie": "", "Werkzeuge": []}]
        st.session_state[DATA_HARD_SKILLS_ROWS] = hs_rows

        hs_edited = st.data_editor(
            hs_rows,
            num_rows="dynamic",
            width="stretch",
            hide_index=True,
            key=W_HARD_SKILLS_EDITOR,
            column_config={
                "Kategorie": st.column_config.TextColumn("Kategorie"),
                "Werkzeuge": st.column_config.ListColumn("Werkzeuge/Technologien"),
            },
        )

        merged_hs = _apply_data_editor_deltas(
            W_HARD_SKILLS_EDITOR, hs_edited if isinstance(hs_edited, list) else hs_rows
        )
        st.session_state[DATA_HARD_SKILLS_ROWS] = merged_hs

        new_hard_skills = {}
        for row in merged_hs:
            if not isinstance(row, dict):
                continue
            cat = str(row.get("Kategorie", "")).strip()
            if not cat:
                continue
            tools = row.get("Werkzeuge", [])
            if not isinstance(tools, list):
                tools = _norm_list(tools)
            tools = [str(t).strip() for t in tools if str(t).strip()]
            new_hard_skills[cat] = tools

        edited["hard_skills"] = new_hard_skills


def _render_skills_overview(edited: dict) -> None:
    with st.expander("Kompetenzübersicht (Skills Overview)", expanded=False):
        _reset_editor_widget_key_if_corrupt(W_SKILLS_OVERVIEW_EDITOR)

        initial = edited.get("skills_overview", [])
        if not isinstance(initial, list):
            initial = []

        initial_rows = []
        for row in initial:
            if not isinstance(row, dict):
                continue
            initial_rows.append(_skills_overview_row_to_ui(row))

        if not initial_rows:
            initial_rows = [{"Kategorie": "", "Werkzeuge": [], "Jahre Erfahrung": ""}]

        sk_rows = _ensure_data_rows(DATA_SKILLS_OVERVIEW_ROWS, initial_rows)
        sk_rows = [_skills_overview_row_to_ui(r) for r in sk_rows if isinstance(r, dict)]
        if not sk_rows:
            sk_rows = [{"Kategorie": "", "Werkzeuge": [], "Jahre Erfahrung": ""}]
        st.session_state[DATA_SKILLS_OVERVIEW_ROWS] = sk_rows

        sk_edited = st.data_editor(
            sk_rows,
            num_rows="dynamic",
            width="stretch",
            hide_index=True,
            key=W_SKILLS_OVERVIEW_EDITOR,
            column_config={
                "Kategorie": st.column_config.TextColumn("Kategorie"),
                "Werkzeuge": st.column_config.ListColumn("Werkzeuge/Technologien"),
                "Jahre Erfahrung": st.column_config.TextColumn("Jahre Erfahrung"),
            },
        )

        merged_sk = _apply_data_editor_deltas(
            W_SKILLS_OVERVIEW_EDITOR, sk_edited if isinstance(sk_edited, list) else sk_rows
        )
        st.session_state[DATA_SKILLS_OVERVIEW_ROWS] = merged_sk

        cleaned = []
        for row in merged_sk:
            if not isinstance(row, dict):
                continue
            cleaned.append(_skills_overview_row_to_ui(row))

        edited["skills_overview"] = cleaned


def _render_languages(edited: dict) -> None:
    with st.expander("Sprachen", expanded=False):
        def _rows_to_records(value):
            if isinstance(value, list):
                return value
            if hasattr(value, "to_dict"):
                try:
                    recs = value.to_dict("records")
                    return recs if isinstance(recs, list) else []
                except Exception:
                    return []
            return []

        _reset_editor_widget_key_if_corrupt(W_LANGUAGES_EDITOR_MAIN)

        initial_lang = edited.get("languages", [])
        if not isinstance(initial_lang, list):
            initial_lang = []

        initial_rows = [_lang_row_to_editor(r) for r in initial_lang]
        if not initial_rows:
            initial_rows = [{"Sprache": "", "Niveau": ""}]

        lang_rows = _ensure_data_rows(DATA_LANGUAGES_ROWS, initial_rows)
        lang_rows = [_lang_row_to_editor(r) for r in _rows_to_records(lang_rows) if isinstance(r, dict)]
        if not lang_rows:
            lang_rows = [{"Sprache": "", "Niveau": ""}]

        # Apply pending editor deltas BEFORE rendering, so the UI reflects the latest typed values.
        lang_rows = [_lang_row_to_editor(r) for r in _apply_data_editor_deltas(W_LANGUAGES_EDITOR_MAIN, lang_rows)]
        if not lang_rows:
            lang_rows = [{"Sprache": "", "Niveau": ""}]
        st.session_state[DATA_LANGUAGES_ROWS] = lang_rows

        lang_edited = st.data_editor(
            lang_rows,
            num_rows="dynamic",
            width="stretch",
            hide_index=True,
            key=W_LANGUAGES_EDITOR_MAIN,
            column_config={
                "Sprache": st.column_config.TextColumn("Sprache"),
                "Niveau": st.column_config.TextColumn("Niveau"),
            },
        )

        lang_edited_records = _rows_to_records(lang_edited)
        merged_lang = _apply_data_editor_deltas(W_LANGUAGES_EDITOR_MAIN, lang_edited_records)
        merged_lang = [_lang_row_to_editor(r) for r in merged_lang if isinstance(r, dict)]
        st.session_state[DATA_LANGUAGES_ROWS] = merged_lang
        edited["languages"] = merged_lang


def _render_education(edited: dict) -> None:
    with st.expander("Ausbildung (Education)", expanded=False):
        def _rows_to_records(value):
            if isinstance(value, list):
                return value
            if hasattr(value, "to_dict"):
                try:
                    recs = value.to_dict("records")
                    return recs if isinstance(recs, list) else []
                except Exception:
                    return []
            return []

        _reset_editor_widget_key_if_corrupt(W_EDUCATION_EDITOR_MAIN)

        initial_edu = edited.get("education", [])
        if not isinstance(initial_edu, list):
            initial_edu = []

        initial_rows = [_edu_row_to_editor(r) for r in initial_edu]
        if not initial_rows:
            initial_rows = [{"Institution": "", "Abschluss": "", "Jahr": ""}]

        edu_rows = _ensure_data_rows(DATA_EDUCATION_ROWS, initial_rows)
        edu_rows = [_edu_row_to_editor(r) for r in _rows_to_records(edu_rows) if isinstance(r, dict)]
        if not edu_rows:
            edu_rows = [{"Institution": "", "Abschluss": "", "Jahr": ""}]

        # Apply pending editor deltas BEFORE rendering.
        edu_rows = [_edu_row_to_editor(r) for r in _apply_data_editor_deltas(W_EDUCATION_EDITOR_MAIN, edu_rows)]
        if not edu_rows:
            edu_rows = [{"Institution": "", "Abschluss": "", "Jahr": ""}]
        st.session_state[DATA_EDUCATION_ROWS] = edu_rows

        edu_edited = st.data_editor(
            edu_rows,
            num_rows="dynamic",
            width="stretch",
            hide_index=True,
            key=W_EDUCATION_EDITOR_MAIN,
            column_config={
                "Institution": st.column_config.TextColumn("Institution/Universität"),
                "Abschluss": st.column_config.TextColumn("Abschluss/Fachrichtung"),
                "Jahr": st.column_config.TextColumn("Abschlussjahr"),
            },
        )

        edu_edited_records = _rows_to_records(edu_edited)
        merged_edu = _apply_data_editor_deltas(W_EDUCATION_EDITOR_MAIN, edu_edited_records)
        merged_edu = [_edu_row_to_editor(r) for r in merged_edu if isinstance(r, dict)]
        st.session_state[DATA_EDUCATION_ROWS] = merged_edu
        edited["education"] = merged_edu


def _render_text_summary() -> None:
    cv_data_for_summary = st.session_state.get(KEY_FILLED_JSON, {})
    st.markdown("### 📝 Textbasierte Zusammenfassung")
    if st.button("Zusammenfassung generieren", key=BTN_GENERATE_V3_SUMMARY):
        with st.spinner("GPT generiert die textbasierte Zusammenfassung…"):
            from chatgpt_client import gpt_generate_text_cv_summary

            try:
                summary_result = gpt_generate_text_cv_summary(
                    cv_data=cv_data_for_summary,
                    model="gpt-4o-mini",
                )
                if summary_result.get("success") and summary_result.get("output_text"):
                    st.session_state[KEY_V3_SUMMARY_TEXT] = summary_result["output_text"]
                    st.success("Summary erfolgreich erstellt.")
                else:
                    st.warning("⚠️ Keine Zusammenfassung erhalten.")
            except Exception as e:
                st.error(f"Fehler bei der Generierung: {e}")

    if KEY_V3_SUMMARY_TEXT in st.session_state:
        st.text_area(
            "📄 Zusammenfassung (nur Text)",
            value=st.session_state[KEY_V3_SUMMARY_TEXT],
            height=300,
            disabled=False,
            key=W_V3_SUMMARY_AREA,
        )


def _render_save_and_downloads(edited: dict) -> None:
    st.markdown("---")
    st.subheader("⬇️ Ergebnisse herunterladen")

    save_clicked_all = st.button(
        "💾 Alle Projekt-Änderungen speichern & PDF aktualisieren",
        key=BTN_SAVE_ALL_PROJECTS_AND_PDF,
    )

    save_clicked = bool(save_clicked_all)

    if st.session_state.get(KEY_PDF_NEEDS_REFRESH, False) and not save_clicked:
        st.warning(
            "⚠️ Es gibt nicht gespeicherte Änderungen (Projekte). Bitte speichere, bevor du das PDF herunterlädst."
        )

    if save_clicked:
        final_json = copy.deepcopy(st.session_state[KEY_EDITED_JSON])

        current_rows = st.session_state.get(DATA_PROJECTS_ROWS, final_json.get("projects_experience", []))
        projects_full_now = _apply_data_editor_deltas(
            W_PROJECTS_EDITOR, current_rows if isinstance(current_rows, list) else []
        )
        st.session_state[DATA_PROJECTS_ROWS] = projects_full_now
        if isinstance(projects_full_now, list):
            projects_full_now = [p for p in projects_full_now if _project_has_content(p)]
        else:
            projects_full_now = []
        final_json["projects_experience"] = projects_full_now

        hs_rows_now = st.session_state.get(DATA_HARD_SKILLS_ROWS, [])
        hs_rows_now = _apply_data_editor_deltas(
            W_HARD_SKILLS_EDITOR, hs_rows_now if isinstance(hs_rows_now, list) else []
        )
        st.session_state[DATA_HARD_SKILLS_ROWS] = hs_rows_now

        sk_rows_now = st.session_state.get(DATA_SKILLS_OVERVIEW_ROWS, [])
        sk_rows_now = _apply_data_editor_deltas(
            W_SKILLS_OVERVIEW_EDITOR, sk_rows_now if isinstance(sk_rows_now, list) else []
        )
        st.session_state[DATA_SKILLS_OVERVIEW_ROWS] = sk_rows_now

        lang_rows_now = final_json.get("languages", [])
        lang_rows_now = _apply_data_editor_deltas(
            W_LANGUAGES_EDITOR_MAIN, lang_rows_now if isinstance(lang_rows_now, list) else []
        )
        final_json["languages"] = lang_rows_now

        edu_rows_now = final_json.get("education", [])
        edu_rows_now = _apply_data_editor_deltas(
            W_EDUCATION_EDITOR_MAIN, edu_rows_now if isinstance(edu_rows_now, list) else []
        )
        final_json["education"] = edu_rows_now

        if isinstance(final_json.get("languages"), list):
            final_json["languages"] = languages_to_pdf_format(final_json["languages"])

        if not final_json.get("title"):
            final_json["title"] = final_json.get("position") or final_json.get("role") or ""

        st.session_state[KEY_FILLED_JSON] = final_json
        st.session_state[KEY_EDITED_JSON] = copy.deepcopy(final_json)
        st.session_state[KEY_JSON_BYTES] = json.dumps(final_json, indent=2, ensure_ascii=False).encode("utf-8")

        filtered_projects_now = st.session_state.get(KEY_FILTERED_PROJECTS_FOR_PDF, final_json.get("projects_experience", []))
        if isinstance(filtered_projects_now, list):
            filtered_projects_now = [p for p in filtered_projects_now if _project_has_content(p)]
        else:
            filtered_projects_now = []
        pdf_preview = copy.deepcopy(final_json)
        pdf_preview["projects_experience"] = filtered_projects_now
        pdf_preview["domains"] = st.session_state.get(KEY_PDF_DOMAINS_LIST, [])
        pdf_preview["companies"] = st.session_state.get(KEY_PDF_COMPANIES_LIST, [])

        pdf_json = _remove_empty_fields(pdf_preview)

        if not pdf_json.get("title"):
            pdf_json["title"] = pdf_json.get("position") or pdf_json.get("role") or ""

        output_dir = "data_output"
        os.makedirs(output_dir, exist_ok=True)
        pdf_name = st.session_state.get(KEY_PDF_NAME, "CV_Streamlit")

        pdf_path_out = create_pretty_first_section(pdf_json, output_dir=output_dir, prefix=pdf_name)
        with open(pdf_path_out, "rb") as f:
            st.session_state[KEY_PDF_BYTES] = f.read()

        st.session_state[KEY_PDF_NEEDS_REFRESH] = False
        st.success("Alle Änderungen wurden gespeichert und das PDF wurde aktualisiert.")

    pdf_name = st.session_state.get(KEY_PDF_NAME, "CV_Streamlit")

    st.download_button(
        label="📘 JSON herunterladen",
        data=st.session_state.get(KEY_JSON_BYTES, b""),
        file_name=f"{pdf_name}_result.json",
        mime="application/json",
        key=DL_JSON,
    )

    if KEY_PDF_BYTES in st.session_state:
        st.download_button(
            label="📄 PDF herunterladen",
            data=st.session_state[KEY_PDF_BYTES],
            file_name=f"{pdf_name}.pdf",
            mime="application/pdf",
            key=DL_PDF,
            disabled=st.session_state.get(KEY_PDF_NEEDS_REFRESH, False),
        )
