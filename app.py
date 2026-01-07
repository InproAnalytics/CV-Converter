import streamlit as st
import json, os, tempfile, time
import threading
import copy

from constants import (
    KEY_EDITED_JSON,
    KEY_FILLED_JSON,
    KEY_JSON_BYTES,
    KEY_LAST_UPLOADED_FILE_NAME,
    KEY_MODEL_LABEL,
    KEY_PDF_BYTES,
    KEY_PDF_NAME,
    KEY_PDF_NEEDS_REFRESH,
    KEY_PDF_PATH,
    KEY_RAW_TEXT,
    KEY_SELECTED_MODEL,
)

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
# Helpers (moved into modules)
# -------------------------
from cv_normalization import (
    _fingerprint,
    _remove_empty_fields,
)
from streamlit_state import (
    clear_candidate_data,
    ensure_edited_json_initialized,
    is_new_candidate,
)
from ui.editors import render_manual_editing


# -------------------------
# Upload + Convert
# -------------------------
if uploaded_file:
    if is_new_candidate(uploaded_file):
        clear_candidate_data()
        st.session_state[KEY_LAST_UPLOADED_FILE_NAME] = uploaded_file.name
        st.session_state[KEY_PDF_NEEDS_REFRESH] = False

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        pdf_path = tmp.name

    st.success(f"✅ Datei hochgeladen: {uploaded_file.name}")

    st.session_state.setdefault(KEY_SELECTED_MODEL, "gpt-4o-mini")
    MODEL_OPTIONS = {
        "Schnell (geringere Qualität)": "gpt-4o-mini",
        "Langsamer (Genauer)": "gpt-5-mini",
    }
    st.radio("Modell auswählen", options=list(MODEL_OPTIONS.keys()), key=KEY_MODEL_LABEL)
    st.session_state[KEY_SELECTED_MODEL] = MODEL_OPTIONS[st.session_state[KEY_MODEL_LABEL]]

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
            st.session_state[KEY_RAW_TEXT] = raw_text
            st.session_state[KEY_PDF_PATH] = pdf_path

            for i in range(1, 26, 2):
                time.sleep(0.05)
                progress.progress(i)
                progress_value = i
                time_info.text(f"⏱ {round(time.time() - start_time, 1)} Sekunden vergangen")

            status_text.text("🤖 Anfrage wird an ChatGPT gesendet…")
            holder = {"value": None, "error": None}
            selected_model = st.session_state[KEY_SELECTED_MODEL]

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

                st.session_state[KEY_FILLED_JSON] = filled_json
                st.session_state[KEY_EDITED_JSON] = copy.deepcopy(filled_json)
                st.session_state[KEY_JSON_BYTES] = json.dumps(filled_json, indent=2, ensure_ascii=False).encode("utf-8")

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
                    st.session_state[KEY_PDF_BYTES] = f.read()

                st.session_state[KEY_PDF_NAME] = pdf_name
                st.session_state[KEY_PDF_NEEDS_REFRESH] = False
                progress.progress(100)
            else:
                st.error("⚠️ Das Modell hat keine Daten zurückgegeben.")
        except Exception as e:
            st.error(f"❌ Fehler bei der Verarbeitung: {e}")


# -------------------------
# Editors
# -------------------------
if KEY_FILLED_JSON in st.session_state and isinstance(st.session_state[KEY_FILLED_JSON], dict):
    ensure_edited_json_initialized()
    edited = st.session_state[KEY_EDITED_JSON]

    render_manual_editing(edited)
