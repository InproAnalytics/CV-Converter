import streamlit as st
import json, os, tempfile, time
import ast
import threading
import copy
import hashlib

from pdf_processor import prepare_cv_text
from chatgpt_client import ask_chatgpt
from postprocess import postprocess_filled_cv
from cv_pdf_generator import create_pretty_first_section

# -------------------------
# Page
# -------------------------
st.set_page_config(page_title="CV-Konverter", page_icon="📄")
st.title("📄 CV-Konverter")

uploaded_file = st.file_uploader("Wähle eine PDF-Datei aus", type=["pdf"])


# -------------------------
# Helpers
# -------------------------
def _norm_list(x):
    """Normalize values that should be list[str]."""
    if x is None:
        return []
    if isinstance(x, list):
        return [str(v).strip() for v in x if str(v).strip()]
    if isinstance(x, str):
        parts = [p.strip() for p in x.split(",")]
        return [p for p in parts if p]
    s = str(x).strip()
    return [s] if s else []


def _responsibilities_to_text(value) -> str:
    """Normalize responsibilities value for UI display/editing (multiline string)."""
    if value is None:
        return ""
    if isinstance(value, list):
        items = [str(x).strip() for x in value if str(x).strip()]
        return "\n".join(items)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return ""
        # Handle stringified list, e.g. "['a', 'b']"
        if s.startswith("[") and s.endswith("]"):
            try:
                parsed = ast.literal_eval(s)
                if isinstance(parsed, list):
                    items = [str(x).strip() for x in parsed if str(x).strip()]
                    return "\n".join(items)
            except Exception:
                pass
        return s
    return str(value).strip()


def _responsibilities_to_list(value) -> list[str]:
    """Normalize responsibilities value for storage/PDF generation (list[str])."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]

    s = str(value).strip()
    if not s:
        return []

    # Handle stringified list, e.g. "['a', 'b']" or "[\"a\", \"b\"]"
    if s.startswith("[") and s.endswith("]"):
        for parser in (ast.literal_eval, json.loads):
            try:
                parsed = parser(s)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            except Exception:
                continue

    # Split multiline / bullet-like text into items
    lines = []
    for line in s.splitlines():
        line = line.strip()
        if not line:
            continue
        line = line.lstrip("•*-·–— ").strip()
        if line:
            lines.append(line)

    # If user pasted bullets inline separated by "•"
    if len(lines) <= 1 and "•" in s:
        parts = [p.strip() for p in s.split("•") if p.strip()]
        parts = [p.lstrip("•*-·–— ").strip() for p in parts]
        lines = [p for p in parts if p]

    return lines


def _load_domains_config() -> list[str]:
    config_file = "domains.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return sorted(set(d.strip().title() for d in data.get("domains", []) if str(d).strip()))
        except Exception as e:
            print(f"Error loading domains: {e}")
    return []


def _save_domains_config(domains: list) -> bool:
    config_file = "domains.json"
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump({"domains": sorted(set(domains))}, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving domains: {e}")
        return False


def _stable_dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(obj) -> str:
    return hashlib.sha256(_stable_dumps(obj).encode("utf-8")).hexdigest()


def _project_has_content(p: dict) -> bool:
    if not isinstance(p, dict):
        return False
    keys = [
        "project_title",
        "company",
        "role",
        "overview",
        "duration",
        "tech_stack",
        "responsibilities",
        "domains",
    ]
    for k in keys:
        v = p.get(k)
        if isinstance(v, list):
            if any(str(x).strip() for x in v if x is not None):
                return True
        elif v is not None and str(v).strip():
            return True
    return False


def _extract_domains_from_projects(rows: list[dict]) -> list[str]:
    out = set()
    for p in rows if isinstance(rows, list) else []:
        if not isinstance(p, dict):
            continue
        for d in _norm_list(p.get("domains")):
            dd = str(d).strip()
            if dd:
                out.add(dd.title())
    return sorted(out)


def _extract_companies_from_projects(rows: list[dict]) -> list[str]:
    out = set()
    for p in rows if isinstance(rows, list) else []:
        if not isinstance(p, dict):
            continue
        c = str(p.get("company", "") or "").strip()
        if c:
            out.add(c)
    return sorted(out)


def _filter_projects_by_domains(rows: list[dict], selected_domains: list[str]) -> list[dict]:
    sel = {str(d).strip().casefold() for d in (selected_domains or []) if str(d).strip()}
    if not sel:
        return list(rows) if isinstance(rows, list) else []
    out = []
    for p in rows if isinstance(rows, list) else []:
        if not isinstance(p, dict):
            continue
        p_domains = {str(d).strip().casefold() for d in _norm_list(p.get("domains")) if str(d).strip()}
        if p_domains & sel:
            out.append(p)
    return out


def is_new_candidate(uploaded_file) -> bool:
    if not uploaded_file:
        return False
    last_file = st.session_state.get("last_uploaded_file_name", None)
    return uploaded_file.name != last_file


def _remove_empty_fields(x):
    if isinstance(x, dict):
        out = {}
        for k, v in x.items():
            vv = _remove_empty_fields(v)
            if vv in (None, "", [], {}):
                continue
            out[k] = vv
        return out
    if isinstance(x, list):
        out = []
        for it in x:
            vv = _remove_empty_fields(it)
            if vv in (None, "", [], {}):
                continue
            out.append(vv)
        return out
    return x


def languages_to_pdf_format(rows):
    """Return list of {language, level}."""
    out = []
    for r in rows if isinstance(rows, list) else []:
        if not isinstance(r, dict):
            continue
        if "Sprache" in r or "Niveau" in r:
            out.append({"language": str(r.get("Sprache", "")).strip(), "level": str(r.get("Niveau", "")).strip()})
        else:
            out.append({"language": str(r.get("language", "")).strip(), "level": str(r.get("level", "")).strip()})
    return out


def ensure_edited_json_initialized():
    """Guarantee a single source-of-truth draft for UI edits."""
    if "filled_json" in st.session_state and isinstance(st.session_state["filled_json"], dict):
        if "edited_json" not in st.session_state or not isinstance(st.session_state["edited_json"], dict):
            st.session_state["edited_json"] = copy.deepcopy(st.session_state["filled_json"])


# -------------------------
# Data-editor safe state pattern
# -------------------------
def _ensure_data_rows(data_key: str, initial_rows: list[dict]) -> list[dict]:
    """
    Store editor DATA (list[dict]) under a dedicated data_key.
    Never store list[dict] in the widget key itself.
    """
    v = st.session_state.get(data_key, None)
    if isinstance(v, list) and all(isinstance(r, dict) for r in v):
        return v
    st.session_state[data_key] = copy.deepcopy(initial_rows)
    return st.session_state[data_key]


def _reset_editor_widget_key_if_corrupt(widget_key: str):
    """
    Streamlit keeps INTERNAL widget state in st.session_state[widget_key] (dict).
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


# -------------------------
# Clear candidate data
# -------------------------
def clear_candidate_data():
    keys_to_clear = [
        # core
        "filled_json",
        "edited_json",
        "json_bytes",
        "pdf_bytes",
        "pdf_name",
        "raw_text",
        "pdf_path",
        "pdf_needs_refresh",
        # project filters
        "filtered_projects_for_pdf",
        "selected_domains_for_pdf",
        "project_domains_filter_main",
        "pdf_domains_list",
        "pdf_companies_list",
        "computed_domains_text_filtered_ui",
        "computed_companies_text_filtered_ui",
        "pdf_filter_sel",
        # UI widgets for basic fields
        "w_full_name", "w_first_name", "w_title", "w_profile_summary",
        # model
        "selected_model", "model_label",
        # ---- editor DATA keys (our source of truth)
        "DATA_projects_rows",
        "DATA_hard_skills_rows",
        "DATA_skills_overview_rows",
        "DATA_languages_rows",
        "DATA_education_rows",
        # ---- editor WIDGET keys (internal widget state)
        "W_projects_editor",
        "W_hard_skills_editor",
        "W_skills_overview_editor",
        "W_languages_editor",
        "W_education_editor",
    ]

    # also clear dynamic contact keys
    for k in list(st.session_state.keys()):
        if k.startswith("w_contacts_"):
            keys_to_clear.append(k)

    for key in keys_to_clear:
        st.session_state.pop(key, None)


# -------------------------
# Upload + Convert
# -------------------------
if uploaded_file:
    if is_new_candidate(uploaded_file):
        clear_candidate_data()
        st.session_state["last_uploaded_file_name"] = uploaded_file.name
        st.session_state["pdf_needs_refresh"] = False

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        pdf_path = tmp.name

    st.success(f"✅ Datei hochgeladen: {uploaded_file.name}")

    st.session_state.setdefault("selected_model", "gpt-4o-mini")
    MODEL_OPTIONS = {
        "Schnell (geringere Qualität)": "gpt-4o-mini",
        "Langsamer (Genauer)": "gpt-5-mini",
    }
    st.radio("Modell auswählen", options=list(MODEL_OPTIONS.keys()), key="model_label")
    st.session_state["selected_model"] = MODEL_OPTIONS[st.session_state["model_label"]]

    if st.button("🚀 Konvertierung starten"):
        progress_box = st.container()
        with progress_box:
            progress = st.progress(1)

        progress_value = 1
        status_text = st.empty()
        time_info = st.empty()
        start_time = time.time()

        try:
            status_text.text("📖 Text wird extrahiert…")
            prepared_text, raw_text = prepare_cv_text(pdf_path)
            st.session_state["raw_text"] = raw_text
            st.session_state["pdf_path"] = pdf_path

            for i in range(1, 26, 2):
                time.sleep(0.05)
                progress.progress(i)
                progress_value = i
                time_info.text(f"⏱ {round(time.time() - start_time, 1)} Sekunden vergangen")

            status_text.text("🤖 Anfrage wird an ChatGPT gesendet…")
            holder = {"value": None, "error": None}
            selected_model = st.session_state["selected_model"]

            def _run_gpt():
                try:
                    holder["value"] = ask_chatgpt(prepared_text, mode="details", model=selected_model)
                except Exception as e:
                    holder["error"] = e

            t = threading.Thread(target=_run_gpt, daemon=True)
            t.start()

            with st.spinner("Modell arbeitet…"):
                while t.is_alive():
                    elapsed = time.time() - start_time
                    progress_value = min(progress_value + 1, 95)
                    progress.progress(progress_value)
                    time_info.text(f"⏱ {round(elapsed, 1)} Sekunden vergangen")
                    time.sleep(0.15)

            if holder.get("error"):
                raise holder["error"]

            result = holder.get("value") or {}

            if "raw_response" in result and result["raw_response"]:
                status_text.text("🧩 Daten werden verarbeitet…")
                filled_json = json.loads(result["raw_response"])
                filled_json = postprocess_filled_cv(filled_json, raw_text)

                if not filled_json.get("title"):
                    filled_json["title"] = filled_json.get("position") or filled_json.get("role") or ""

                st.session_state["filled_json"] = filled_json
                st.session_state["edited_json"] = copy.deepcopy(filled_json)
                st.session_state["json_bytes"] = json.dumps(filled_json, indent=2, ensure_ascii=False).encode("utf-8")

                for i in range(56, 76, 2):
                    time.sleep(0.05)
                    progress.progress(i)
                    progress_value = i
                    time_info.text(f"⏱ {round(time.time() - start_time, 1)} Sekunden vergangen")

                status_text.text("📝 PDF wird erstellt…")
                output_dir = "data_output"
                os.makedirs(output_dir, exist_ok=True)

                full_name = str(filled_json.get("full_name", "")).strip()
                position = str(filled_json.get("title") or filled_json.get("position") or filled_json.get("role") or "").strip()

                first_name = full_name.split(" ")[0].title() if full_name else "Unbekannt"
                position_tc = position.title() if position else "Unbekannte Position"
                pdf_name = f"CV Inpro {first_name} {position_tc}"

                for i in range(76, 96, 2):
                    time.sleep(0.03)
                    progress.progress(i)
                    progress_value = i
                    time_info.text(f"⏱ {round(time.time() - start_time, 1)} Sekunden vergangen")

                pdf_path_out = create_pretty_first_section(filled_json, output_dir=output_dir, prefix=pdf_name)
                with open(pdf_path_out, "rb") as f:
                    st.session_state["pdf_bytes"] = f.read()

                st.session_state["pdf_name"] = pdf_name
                st.session_state["last_pdf_fingerprint"] = _fingerprint(_remove_empty_fields(filled_json))
                st.session_state["pdf_needs_refresh"] = False
                progress.progress(100)
            else:
                st.error("⚠️ Das Modell hat keine Daten zurückgegeben.")
        except Exception as e:
            st.error(f"❌ Fehler bei der Verarbeitung: {e}")


# -------------------------
# Editors
# -------------------------
if "filled_json" in st.session_state and isinstance(st.session_state["filled_json"], dict):
    ensure_edited_json_initialized()
    edited = st.session_state["edited_json"]

    st.markdown("---")
    st.subheader("🛠 Manuelle Bearbeitung")

    # --- Basic fields ---
    st.session_state.setdefault("w_full_name", str(edited.get("full_name", "")))
    st.session_state.setdefault("w_first_name", str(edited.get("first_name", "")))
    current_title = str(edited.get("title") or edited.get("position") or edited.get("role") or "")
    st.session_state.setdefault("w_title", current_title)
    st.session_state.setdefault("w_profile_summary", str(edited.get("profile_summary", edited.get("summary", ""))))

    # Basic fields
    col_a, col_b = st.columns(2)
    with col_a:
        st.text_input("Vollständiger Name", key="w_full_name")
        st.text_input("Vorname", key="w_first_name")
    with col_b:
        st.text_input("Position (title)", key="w_title")

    st.text_area("Kurzbeschreibung (profile_summary)", height=140, key="w_profile_summary")

    edited["full_name"] = st.session_state["w_full_name"]
    edited["first_name"] = st.session_state["w_first_name"]
    edited["title"] = st.session_state["w_title"]
    edited["profile_summary"] = st.session_state["w_profile_summary"]

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

    # Projects
    with st.expander("Projekte / Erfahrung (projects_experience)", expanded=True):
        W_PROJECTS = "W_projects_editor"
        DATA_PROJECTS = "DATA_projects_rows"

        _reset_editor_widget_key_if_corrupt(W_PROJECTS)

        base = edited.get("projects_experience", [])
        if not isinstance(base, list):
            base = []

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

        initial_projects = [_project_row_to_ui(p) for p in base if isinstance(p, dict)]
        if not initial_projects:
            initial_projects = [_project_row_to_ui({})]

        projects_rows = _ensure_data_rows(DATA_PROJECTS, initial_projects)
        projects_rows = [_project_row_to_ui(r) for r in projects_rows if isinstance(r, dict)]
        if not projects_rows:
            projects_rows = [_project_row_to_ui({})]

        # IMPORTANT: apply pending editor deltas BEFORE rendering the editor.
        # This prevents losing changes when Streamlit reruns (e.g. user clicks elsewhere).
        projects_rows = _apply_data_editor_deltas(W_PROJECTS, projects_rows)
        projects_rows = [_project_row_to_ui(r) for r in projects_rows if isinstance(r, dict)]
        st.session_state[DATA_PROJECTS] = projects_rows

        projects_edited = st.data_editor(
            projects_rows,
            num_rows="dynamic",
            width="stretch",
            hide_index=True,
            key=W_PROJECTS,
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

        # Normalize rows, then apply any pending deltas so edits are not lost on a direct button click.
        normalized_now = [_project_row_to_ui(r) for r in projects_edited if isinstance(r, dict)]
        merged_now = _apply_data_editor_deltas(W_PROJECTS, normalized_now)
        merged_now = [_project_row_to_ui(r) for r in merged_now if isinstance(r, dict)]
        st.session_state[DATA_PROJECTS] = merged_now

        # Store responsibilities as list[str] (not a stringified Python list)
        data_projects = []
        for r in merged_now:
            if not isinstance(r, dict):
                continue
            data_projects.append({
                "project_title": str(r.get("project_title", "") or ""),
                "company": str(r.get("company", "") or ""),
                "overview": str(r.get("overview", "") or ""),
                "role": str(r.get("role", "") or ""),
                "duration": str(r.get("duration", "") or ""),
                "responsibilities": _responsibilities_to_list(r.get("responsibilities")),
                "tech_stack": _norm_list(r.get("tech_stack")),
                "domains": _norm_list(r.get("domains")),
            })
        edited["projects_experience"] = data_projects

        def _autofill_domains_from_projects():
            rows = st.session_state.get(DATA_PROJECTS, [])
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
            key="btn_autofill_project_domains_main",
            on_click=_autofill_domains_from_projects,
        )

    # PDF Domains filter: show only domains that exist in current projects (not from domains.json)
    projects_for_filter = st.session_state.get("DATA_projects_rows", [])
    domains_options = _extract_domains_from_projects(projects_for_filter)
    prior_sel = st.session_state.get("selected_domains_for_pdf", [])
    safe_default = [d for d in prior_sel if d in domains_options]
    selected_domains = st.multiselect(
        "Domains-Filter (für PDF)",
        options=domains_options,
        default=safe_default,
        key="selected_domains_for_pdf",
    )

    with st.container():
        current_sel = tuple(sorted([s.strip().casefold() for s in selected_domains]))
        st.session_state["pdf_filter_sel"] = current_sel

        # compute filtered projects + lists used by PDF preview
        all_projects_now = [p for p in projects_for_filter if _project_has_content(p)]
        selected_domains_list = list(selected_domains or [])
        filtered_projects = _filter_projects_by_domains(all_projects_now, selected_domains_list)
        st.session_state["filtered_projects_for_pdf"] = filtered_projects

        # If we are NOT filtering (no domains selected), treat it as "select all projects" and
        # also auto-fill domains/companies lists from ALL projects.
        if not selected_domains_list:
            st.session_state["pdf_domains_list"] = _extract_domains_from_projects(all_projects_now)
            st.session_state["pdf_companies_list"] = _extract_companies_from_projects(all_projects_now)
        else:
            st.session_state["pdf_domains_list"] = selected_domains_list
            st.session_state["pdf_companies_list"] = _extract_companies_from_projects(filtered_projects)

        # Show the (filtered) domain/company lists again (for copying / visibility)
        st.session_state["computed_domains_text_filtered_ui"] = "\n".join(
            [str(d) for d in (st.session_state.get("pdf_domains_list", []) or []) if str(d).strip()]
        )
        st.session_state["computed_companies_text_filtered_ui"] = "\n".join(
            [str(c) for c in (st.session_state.get("pdf_companies_list", []) or []) if str(c).strip()]
        )
        col_dom, col_comp = st.columns(2)
        with col_dom:
            st.text_area(
                "Domänen (für PDF)",
                key="computed_domains_text_filtered_ui",
                height=110,
                disabled=True,
            )
        with col_comp:
            st.text_area(
                "Firmen (aus gefilterten Projekten)",
                key="computed_companies_text_filtered_ui",
                height=110,
                disabled=True,
            )

        # true/false unsaved state based on actual PDF preview content
        pdf_preview = copy.deepcopy(edited)
        pdf_preview["projects_experience"] = filtered_projects
        pdf_preview["domains"] = st.session_state.get("pdf_domains_list", [])
        pdf_preview["companies"] = st.session_state.get("pdf_companies_list", [])
        current_fp = _fingerprint(_remove_empty_fields(pdf_preview))
        last_fp = st.session_state.get("last_pdf_fingerprint")
        if last_fp is None:
            st.session_state["last_pdf_fingerprint"] = current_fp
            st.session_state["pdf_needs_refresh"] = False
        else:
            st.session_state["pdf_needs_refresh"] = (current_fp != last_fp)

        # -------------------------
        # Hard Skills
        # -------------------------
        with st.expander("Fachliche Kompetenzen (Hard Skills)", expanded=False):
            W_HS = "W_hard_skills_editor"
            DATA_HS = "DATA_hard_skills_rows"

            _reset_editor_widget_key_if_corrupt(W_HS)

            hs = edited.get("hard_skills", {})
            if not isinstance(hs, dict):
                hs = {}

            initial_rows = []
            for k, v in hs.items():
                tools = v if isinstance(v, list) else ([v] if v else [])
                initial_rows.append({"Kategorie": str(k), "Werkzeuge": [str(x).strip() for x in tools if str(x).strip()]})

            if not initial_rows:
                initial_rows = [{"Kategorie": "", "Werkzeuge": []}]

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

            hs_rows = _ensure_data_rows(DATA_HS, initial_rows)
            hs_rows = [_hard_skills_row_to_ui(r) for r in hs_rows if isinstance(r, dict)]
            if not hs_rows:
                hs_rows = [{"Kategorie": "", "Werkzeuge": []}]
            st.session_state[DATA_HS] = hs_rows

            hs_edited = st.data_editor(
                hs_rows,
                num_rows="dynamic",
                width="stretch",
                hide_index=True,
                key=W_HS,
                column_config={
                    "Kategorie": st.column_config.TextColumn("Kategorie"),
                    "Werkzeuge": st.column_config.ListColumn("Werkzeuge/Technologien"),
                },
            )

            merged_hs = _apply_data_editor_deltas(W_HS, hs_edited if isinstance(hs_edited, list) else hs_rows)
            st.session_state[DATA_HS] = merged_hs

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

        # -------------------------
        # Skills overview
        # -------------------------
        with st.expander("Kompetenzübersicht (Skills Overview)", expanded=False):
            W_SK = "W_skills_overview_editor"
            DATA_SK = "DATA_skills_overview_rows"

            _reset_editor_widget_key_if_corrupt(W_SK)

            initial = edited.get("skills_overview", [])
            if not isinstance(initial, list):
                initial = []

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

            initial_rows = []
            for row in initial:
                if not isinstance(row, dict):
                    continue
                initial_rows.append(_skills_overview_row_to_ui(row))

            if not initial_rows:
                initial_rows = [{"Kategorie": "", "Werkzeuge": [], "Jahre Erfahrung": ""}]

            sk_rows = _ensure_data_rows(DATA_SK, initial_rows)
            # Normalize any previously stored rows to avoid showing legacy/empty columns.
            sk_rows = [_skills_overview_row_to_ui(r) for r in sk_rows if isinstance(r, dict)]
            if not sk_rows:
                sk_rows = [{"Kategorie": "", "Werkzeuge": [], "Jahre Erfahrung": ""}]
            st.session_state[DATA_SK] = sk_rows

            sk_edited = st.data_editor(
                sk_rows,
                num_rows="dynamic",
                width="stretch",
                hide_index=True,
                key=W_SK,
                column_config={
                    "Kategorie": st.column_config.TextColumn("Kategorie"),
                    "Werkzeuge": st.column_config.ListColumn("Werkzeuge/Technologien"),
                    "Jahre Erfahrung": st.column_config.TextColumn("Jahre Erfahrung"),
                },
            )

            merged_sk = _apply_data_editor_deltas(W_SK, sk_edited if isinstance(sk_edited, list) else sk_rows)
            st.session_state[DATA_SK] = merged_sk

            cleaned = []
            for row in merged_sk:
                if not isinstance(row, dict):
                    continue
                cleaned.append(_skills_overview_row_to_ui(row))

            edited["skills_overview"] = cleaned

        # -------------------------
        # Languages
        # -------------------------
        with st.expander("Sprachen", expanded=False):
            def lang_row_to_editor(row):
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

            initial_lang_rows = edited.get("languages", [])
            if not isinstance(initial_lang_rows, list):
                initial_lang_rows = []

            lang_rows = [lang_row_to_editor(r) for r in initial_lang_rows]
            if not lang_rows:
                lang_rows = [{"Sprache": "", "Niveau": ""}]

            lang_edited = st.data_editor(
                lang_rows,
                num_rows="dynamic",
                width="stretch",
                hide_index=True,
                key="ed_languages_main",
                column_config={
                    "Sprache": st.column_config.TextColumn("Sprache"),
                    "Niveau": st.column_config.TextColumn("Niveau"),
                },
            )

            merged_lang = _apply_data_editor_deltas("ed_languages_main", lang_edited if isinstance(lang_edited, list) else lang_rows)
            edited["languages"] = merged_lang

        # -------------------------
        # Education
        # -------------------------
        with st.expander("Ausbildung (Education)", expanded=False):
            def edu_row_to_editor(row):
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

            initial_edu = edited.get("education", [])
            if not isinstance(initial_edu, list):
                initial_edu = []

            edu_rows = [edu_row_to_editor(r) for r in initial_edu]
            if not edu_rows:
                edu_rows = [{"Institution": "", "Abschluss": "", "Jahr": ""}]

            edu_edited = st.data_editor(
                edu_rows,
                num_rows="dynamic",
                width="stretch",
                hide_index=True,
                key="ed_education_main",
                column_config={
                    "Institution": st.column_config.TextColumn("Institution/Universität"),
                    "Abschluss": st.column_config.TextColumn("Abschluss/Fachrichtung"),
                    "Jahr": st.column_config.TextColumn("Abschlussjahr"),
                },
            )

            merged_edu = _apply_data_editor_deltas("ed_education_main", edu_edited if isinstance(edu_edited, list) else edu_rows)
            edited["education"] = merged_edu

        # --- V3 Text Summary (optional) ---
        cv_data_for_summary = st.session_state.get("filled_json", {})
        st.markdown("### 📝 Textbasierte Zusammenfassung")
        if st.button("Zusammenfassung generieren", key="btn_generate_v3_summary"):
            with st.spinner("GPT generiert die textbasierte Zusammenfassung…"):
                from chatgpt_client import gpt_generate_text_cv_summary
                try:
                    summary_result = gpt_generate_text_cv_summary(
                        cv_data=cv_data_for_summary,
                        model="gpt-4o-mini"
                    )
                    if summary_result.get("success") and summary_result.get("output_text"):
                        st.session_state["v3_summary_text"] = summary_result["output_text"]
                        st.success("Summary erfolgreich erstellt.")
                    else:
                        st.warning("⚠️ Keine Zusammenfassung erhalten.")
                except Exception as e:
                    st.error(f"Fehler bei der Generierung: {e}")

        if "v3_summary_text" in st.session_state:
            st.text_area(
                "📄 Zusammenfassung (nur Text)",
                value=st.session_state["v3_summary_text"],
                height=300,
                disabled=False,
                key="v3_summary_area",
            )

        # -------------------------
        # Save + PDF
        # -------------------------
        st.markdown("---")
        st.subheader("⬇️ Ergebnisse herunterladen")

        # Yellow warning must always be visible when there are unsaved edits.
        # Button here commits ALL project field edits (table + filter selection) and updates the PDF.
        save_clicked_all = st.button(
            "💾 Alle Projekt-Änderungen speichern & PDF aktualisieren",
            key="btn_save_all_projects_and_pdf_footer",
        )

        save_clicked = bool(save_clicked_all)

        if st.session_state.get("pdf_needs_refresh", False) and not save_clicked:
            st.warning(
                "⚠️ Es gibt nicht gespeicherte Änderungen (Projekte). Bitte speichere, bevor du das PDF herunterlädst."
            )

        if save_clicked:
            # 1) Final JSON = edited_json (full projects, full languages normalized)
            final_json = copy.deepcopy(st.session_state["edited_json"])

            # ensure projects: source-of-truth = projects editor state (DATA_projects_rows)
            # + apply uncommitted st.data_editor deltas to avoid "every other time" saves.
            current_rows = st.session_state.get("DATA_projects_rows", final_json.get("projects_experience", []))
            projects_full_now = _apply_data_editor_deltas("W_projects_editor", current_rows if isinstance(current_rows, list) else [])
            st.session_state["DATA_projects_rows"] = projects_full_now
            if isinstance(projects_full_now, list):
                projects_full_now = [p for p in projects_full_now if _project_has_content(p)]
            else:
                projects_full_now = []
            final_json["projects_experience"] = projects_full_now

            # sync other editor tables (captures uncommitted edits on first click)
            hs_rows_now = st.session_state.get("DATA_hard_skills_rows", [])
            hs_rows_now = _apply_data_editor_deltas("W_hard_skills_editor", hs_rows_now if isinstance(hs_rows_now, list) else [])
            st.session_state["DATA_hard_skills_rows"] = hs_rows_now

            sk_rows_now = st.session_state.get("DATA_skills_overview_rows", [])
            sk_rows_now = _apply_data_editor_deltas("W_skills_overview_editor", sk_rows_now if isinstance(sk_rows_now, list) else [])
            st.session_state["DATA_skills_overview_rows"] = sk_rows_now

            lang_rows_now = final_json.get("languages", [])
            lang_rows_now = _apply_data_editor_deltas("ed_languages_main", lang_rows_now if isinstance(lang_rows_now, list) else [])
            final_json["languages"] = lang_rows_now

            edu_rows_now = final_json.get("education", [])
            edu_rows_now = _apply_data_editor_deltas("ed_education_main", edu_rows_now if isinstance(edu_rows_now, list) else [])
            final_json["education"] = edu_rows_now

            # normalize languages to {language, level}
            if isinstance(final_json.get("languages"), list):
                final_json["languages"] = languages_to_pdf_format(final_json["languages"])

            # title safety
            if not final_json.get("title"):
                final_json["title"] = final_json.get("position") or final_json.get("role") or ""

            st.session_state["filled_json"] = final_json
            st.session_state["edited_json"] = copy.deepcopy(final_json)  # keep in sync after save
            st.session_state["json_bytes"] = json.dumps(final_json, indent=2, ensure_ascii=False).encode("utf-8")

            # 2) Build PDF preview with filtered projects + domains/companies lists
            filtered_projects_now = st.session_state.get(
                "filtered_projects_for_pdf", final_json.get("projects_experience", [])
            )
            if isinstance(filtered_projects_now, list):
                filtered_projects_now = [p for p in filtered_projects_now if _project_has_content(p)]
            else:
                filtered_projects_now = []
            pdf_preview = copy.deepcopy(final_json)
            pdf_preview["projects_experience"] = filtered_projects_now
            pdf_preview["domains"] = st.session_state.get("pdf_domains_list", [])
            pdf_preview["companies"] = st.session_state.get("pdf_companies_list", [])

            # remove empty fields for pdf generation
            pdf_json = _remove_empty_fields(pdf_preview)

            if not pdf_json.get("title"):
                pdf_json["title"] = pdf_json.get("position") or pdf_json.get("role") or ""

            output_dir = "data_output"
            os.makedirs(output_dir, exist_ok=True)
            pdf_name = st.session_state.get("pdf_name", "CV_Streamlit")

            pdf_path_out = create_pretty_first_section(pdf_json, output_dir=output_dir, prefix=pdf_name)
            with open(pdf_path_out, "rb") as f:
                st.session_state["pdf_bytes"] = f.read()

            st.session_state["last_pdf_fingerprint"] = _fingerprint(pdf_json)
            st.session_state["pdf_needs_refresh"] = False
            st.success("Alle Änderungen wurden gespeichert und das PDF wurde aktualisiert.")

    # Downloads
    pdf_name = st.session_state.get("pdf_name", "CV_Streamlit")

    st.download_button(
        label="📘 JSON herunterladen",
        data=st.session_state.get("json_bytes", b""),
        file_name=f"{pdf_name}_result.json",
        mime="application/json",
        key="download_json",
    )

    if "pdf_bytes" in st.session_state:
        st.download_button(
            label="📄 PDF herunterladen",
            data=st.session_state["pdf_bytes"],
            file_name=f"{pdf_name}.pdf",
            mime="application/pdf",
            key="download_pdf",
            disabled=st.session_state.get("pdf_needs_refresh", False),
        )
