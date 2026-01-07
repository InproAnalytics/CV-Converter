import os
import glob
from difflib import SequenceMatcher
from PyPDF2 import PdfReader
import streamlit as st


def extract_text_from_pdf(path: str) -> str:
    """Extract text page-by-page from a PDF file."""
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def text_similarity(a: str, b: str) -> float:
    """Compute percentage text similarity between two strings."""
    return round(SequenceMatcher(None, a.lower(), b.lower()).ratio() * 100, 1)


def compare_sections(original_text: str, inpro_text: str):
    """Compare original and generated CV content by sections and return similarity scores."""
    sections = {
        "Profil / Zusammenfassung": ["summary", "profil", "über mich"],
        "Ausbildung": ["education", "ausbildung", "fh"],
        "Sprachen": ["languages", "sprachen"],
        "Fachbereiche / Domains": ["domains", "bereiche"],
        "Projekte & Berufserfahrung": ["project", "experience", "erfahrung", "berufliche"],
        "Technische Kompetenzen (Hard Skills)": ["skills", "technologies", "hard", "overview"],
    }

    results = []
    for name, keywords in sections.items():
        import re
        pattern = re.compile("|".join(keywords), re.IGNORECASE)
        orig_block = "\n".join([l for l in original_text.splitlines() if pattern.search(l)])
        inpro_block = "\n".join([l for l in inpro_text.splitlines() if pattern.search(l)])
        score = text_similarity(orig_block, inpro_block)
        results.append((name, score))
    return results


essential_glob_prefix = "CV_Streamlit"

def show_similarity_results(original_pdf_path: str, generated_pdf_path: str):
    """Render similarity results inside Streamlit app."""
    if not (os.path.exists(original_pdf_path) and os.path.exists(generated_pdf_path)):
        st.warning("⚠️ Die Dateien zum Vergleich wurden nicht gefunden.")
        return

    st.subheader("📊 Ähnlichkeitsbewertung der CVs nach Abschnitten")

    orig_text = extract_text_from_pdf(original_pdf_path)
    gen_text = extract_text_from_pdf(generated_pdf_path)
    comparison = compare_sections(orig_text, gen_text)

    table_data = []
    for section, score in comparison:
        table_data.append({"Abschnitt": section, "Übereinstimmung (%)": score})
    if table_data:
        avg = round(sum(x["Übereinstimmung (%)"] for x in table_data) / len(table_data), 1)
    else:
        avg = 0.0

    st.table(table_data)
    st.markdown(f"### 🟩 Durchschnittliche Übereinstimmung: **{avg}%**")


def generate_report_pdf_bytes(create_pdf_func, filled_json: dict, original_pdf_path: str | None = None, output_dir: str = "data_output", prefix: str = "CV_Streamlit") -> bytes:
    """
    Generate PDF via provided create_pdf_func() and optionally render similarity results.
    - create_pdf_func: callable like cv_pdf_generator.create_pretty_first_section
    - filled_json: data for PDF
    - original_pdf_path: if provided, will compute and show similarity inside Streamlit
    Returns PDF bytes.
    """
    os.makedirs(output_dir, exist_ok=True)

    # create PDF
    create_pdf_func(filled_json, output_dir=output_dir, prefix=prefix)

    # find latest generated file
    pdf_files = sorted(
        glob.glob(os.path.join(output_dir, f"{prefix}*.pdf")),
        key=os.path.getmtime,
        reverse=True
    )
    if not pdf_files:
        raise FileNotFoundError("No generated PDF file found after creation.")

    latest_pdf = pdf_files[0]

    # show similarity if original provided
    if original_pdf_path and os.path.exists(original_pdf_path):
        try:
            show_similarity_results(original_pdf_path, latest_pdf)
        except Exception as e:
            st.warning(f"⚠️ Fehler bei der Ähnlichkeitsbewertung: {e}")

    with open(latest_pdf, "rb") as f:
        return f.read()
