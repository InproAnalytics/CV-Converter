import streamlit as st
import json, os, tempfile, time
from pdf_processor import prepare_cv_text
from chatgpt_client import ask_chatgpt
from postprocess import postprocess_filled_cv
from cv_pdf_generator import create_pretty_first_section

# --- Seiteneinstellungen ---
st.set_page_config(page_title="CV-Konverter", page_icon="📄")
st.title("📄 CV-Konverter")

# 1️⃣ Datei-Upload
uploaded_file = st.file_uploader("Wähle eine PDF-Datei aus", type=["pdf"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        pdf_path = tmp.name
    st.success(f"✅ Datei hochgeladen: {uploaded_file.name}")

    # 2️⃣ Konvertierung starten
    if st.button("🚀 Konvertierung starten"):
        progress = st.progress(0)
        status_text = st.empty()
        time_info = st.empty()
        start_time = time.time()

        try:
            # --- Schritt 1: Text extrahieren ---
            status_text.text("📖 Text wird extrahiert…")
            prepared_text, raw_text = prepare_cv_text(pdf_path)
            for i in range(1, 26, 2):
                time.sleep(0.1)
                progress.progress(i)
                time_info.text(f"⏱ {round(time.time() - start_time, 1)} Sekunden vergangen")

            # --- Schritt 2: Anfrage an ChatGPT ---
            status_text.text("🤖 Anfrage wird an ChatGPT gesendet…")
            for i in range(26, 56, 2):
                time.sleep(0.3)
                progress.progress(i)
                time_info.text(f"⏱ {round(time.time() - start_time, 1)} Sekunden vergangen")

            result = ask_chatgpt(prepared_text, mode="details")

            # --- Schritt 3: JSON verarbeiten ---
            if "raw_response" in result and result["raw_response"]:
                status_text.text("🧩 Daten werden verarbeitet…")
                filled_json = json.loads(result["raw_response"])
                filled_json = postprocess_filled_cv(filled_json, raw_text)

                for i in range(56, 76, 2):
                    time.sleep(0.15)
                    progress.progress(i)
                    time_info.text(f"⏱ {round(time.time() - start_time, 1)} Sekunden vergangen")

                # --- Schritt 4: PDF generieren ---
                status_text.text("📝 PDF wird erstellt…")
                output_dir = "data_output"
                os.makedirs(output_dir, exist_ok=True)

                first_name = filled_json.get("first_name", "").strip().title() or "Unbekannt"
                position = filled_json.get("position", "").strip().title() or "Unbekannte Position"
                pdf_name = f"CV Inpro {first_name} {position}"

                pdf_path = create_pretty_first_section(filled_json, output_dir=output_dir, prefix=pdf_name)
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()

                for i in range(76, 100, 2):
                    time.sleep(0.05)
                    progress.progress(i)
                    time_info.text(f"⏱ {round(time.time() - start_time, 1)} Sekunden vergangen")

                progress.progress(100)
                elapsed = round(time.time() - start_time, 1)
                status_text.text(f"✅ Fertig in {elapsed} Sekunden!")
                st.success("✅ Konvertierung abgeschlossen!")

                # --- Automatische Benennung des Dokuments ---
                full_name = filled_json.get("full_name", "").strip()
                position = (
                    filled_json.get("position")
                    or filled_json.get("title")
                    or filled_json.get("role")
                    or ""
                ).strip()

                first_name = full_name.split(" ")[0].title() if full_name else "Unbekannt"
                position = position.title() if position else "Unbekannte Position"
                pdf_name = f"CV Inpro {first_name} {position}"

                # --- PDF generieren mit richtigem Namen ---
                output_dir = "data_output"
                os.makedirs(output_dir, exist_ok=True)
                pdf_path = create_pretty_first_section(
                    filled_json, output_dir=output_dir, prefix=pdf_name
                )

                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()

                # 💾 Ergebnisse speichern
                st.session_state["filled_json"] = filled_json
                st.session_state["json_bytes"] = json.dumps(
                    filled_json, indent=2, ensure_ascii=False
                ).encode("utf-8")
                st.session_state["pdf_bytes"] = pdf_bytes
                st.session_state["pdf_name"] = pdf_name


            else:
                st.error("⚠️ Das Modell hat keine Daten zurückgegeben.")

        except Exception as e:
            st.error(f"❌ Fehler bei der Verarbeitung: {e}")

# 3️⃣ Downloadbereich
if "filled_json" in st.session_state:
    st.markdown("---")
    st.subheader("⬇️ Ergebnisse herunterladen")

    pdf_name = st.session_state.get("pdf_name", "CV_Streamlit")

    st.download_button(
        label="📘 JSON herunterladen",
        data=st.session_state["json_bytes"],
        file_name=f"{pdf_name}_result.json",
        mime="application/json",
        key="download_json"
    )

    if "pdf_bytes" in st.session_state:
        st.download_button(
            label="📄 PDF herunterladen",
            data=st.session_state["pdf_bytes"],
            file_name=f"{pdf_name}.pdf",
            mime="application/pdf",
            key="download_pdf"
        )
