"""Centralized Streamlit session/widget keys.

These constants are used across `app.py`, `streamlit_state.py`, and `ui/` modules
so keys stay consistent and easy to refactor.
"""

# Core candidate/session data
KEY_LAST_UPLOADED_FILE_NAME = "last_uploaded_file_name"
KEY_RAW_TEXT = "raw_text"
KEY_PDF_PATH = "pdf_path"

# JSON/PDF artifacts
KEY_FILLED_JSON = "filled_json"
KEY_EDITED_JSON = "edited_json"
KEY_JSON_BYTES = "json_bytes"
KEY_PDF_BYTES = "pdf_bytes"
KEY_PDF_NAME = "pdf_name"
KEY_LAST_PDF_FINGERPRINT = "last_pdf_fingerprint"
KEY_PDF_NEEDS_REFRESH = "pdf_needs_refresh"

# Model selection
KEY_SELECTED_MODEL = "selected_model"
KEY_MODEL_LABEL = "model_label"

# PDF filter/session helpers
KEY_FILTERED_PROJECTS_FOR_PDF = "filtered_projects_for_pdf"
KEY_SELECTED_DOMAINS_FOR_PDF = "selected_domains_for_pdf"
KEY_PROJECT_DOMAINS_FILTER_MAIN = "project_domains_filter_main"
KEY_PDF_DOMAINS_LIST = "pdf_domains_list"
KEY_PDF_COMPANIES_LIST = "pdf_companies_list"
KEY_COMPUTED_DOMAINS_TEXT_FILTERED_UI = "computed_domains_text_filtered_ui"
KEY_COMPUTED_COMPANIES_TEXT_FILTERED_UI = "computed_companies_text_filtered_ui"
KEY_PDF_FILTER_SEL = "pdf_filter_sel"

# Basic-field widget keys
W_FULL_NAME = "w_full_name"
W_FIRST_NAME = "w_first_name"
W_TITLE = "w_title"
W_PROFILE_SUMMARY = "w_profile_summary"
W_CONTACT_PREFIX = "w_contacts_"

# Editor DATA keys (our source of truth)
DATA_PROJECTS_ROWS = "DATA_projects_rows"
DATA_HARD_SKILLS_ROWS = "DATA_hard_skills_rows"
DATA_SKILLS_OVERVIEW_ROWS = "DATA_skills_overview_rows"
DATA_LANGUAGES_ROWS = "DATA_languages_rows"
DATA_EDUCATION_ROWS = "DATA_education_rows"

# Editor WIDGET keys (internal Streamlit widget state)
W_PROJECTS_EDITOR = "W_projects_editor"
W_HARD_SKILLS_EDITOR = "W_hard_skills_editor"
W_SKILLS_OVERVIEW_EDITOR = "W_skills_overview_editor"
W_LANGUAGES_EDITOR = "W_languages_editor"
W_EDUCATION_EDITOR = "W_education_editor"

# Other UI widget keys
W_SELECTED_DOMAINS_FOR_PDF = KEY_SELECTED_DOMAINS_FOR_PDF
W_LANGUAGES_EDITOR_MAIN = "ed_languages_main"
W_EDUCATION_EDITOR_MAIN = "ed_education_main"

# Summary widgets
KEY_V3_SUMMARY_TEXT = "v3_summary_text"
W_V3_SUMMARY_AREA = "v3_summary_area"

# Button/download widget keys
BTN_AUTOFILL_PROJECT_DOMAINS = "btn_autofill_project_domains_main"
BTN_GENERATE_V3_SUMMARY = "btn_generate_v3_summary"
BTN_SAVE_ALL_PROJECTS_AND_PDF = "btn_save_all_projects_and_pdf_footer"
DL_JSON = "download_json"
DL_PDF = "download_pdf"
