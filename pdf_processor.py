import os
import re
import fitz  # PyMuPDF

# ============================================================
# 1️⃣ PDF → Text Extraktion (seitenweise)
# ============================================================
def extract_text_by_page(pdf_path: str) -> list[str]:
    """Extrahiert den Text jeder Seite aus dem PDF."""
    doc = fitz.open(pdf_path)
    pages_text = []

    for page in doc:
        blocks = page.get_text("blocks") or page.get_text("text")
        if isinstance(blocks, list):
            text = "\n".join([b[4] for b in blocks if b[4].strip()])
        else:
            text = blocks

        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{2,}", "\n", text)
        pages_text.append(text.strip())

    doc.close()
    return pages_text


# ============================================================
# 2️⃣ Datumserkennung (inkl. Deutschformate)
# ============================================================
def tag_dates(text: str) -> str:
    """Markiert Zeiträume und einzelne Datumsangaben mit [DATE]...[/DATE]."""
    patterns = [
        r"\b(0?[1-9]|1[0-2])\.(\d{2})\s*[-–]\s*(0?[1-9]|1[0-2])\.(\d{2})\b",
        r"\b(0?[1-9]|1[0-2])\.(\d{2})\s*[-–]\s*(Jetzt|Derzeit|Heute|Present|Now|Aktuell)\b",
        r"\b(0?[1-9]|1[0-2])\.\d{2}\b\s*[-–]\s*$",
        r"\b(0?[1-9]|1[0-2])\/(\d{4})\s*[-–]\s*(0?[1-9]|1[0-2])\/(\d{4})\b",
        r"\b(0?[1-9]|1[0-2])\/(\d{4})\s*[-–]\s*(Jetzt|Derzeit|Heute|Present|Now|Aktuell)\b",
        r"(?i)\b(seit|since)\s+(0?[1-9]|1[0-2])[./](\d{2,4})\b",
        r"\b(20\d{2}|19\d{2})\s*[-–]\s*(20\d{2}|Present|Now|Heute|Jetzt|Aktuell)\b",
        r"(?:(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*)\s+\d{4}\s*[-–]\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)?[a-z]*\s*\d{4}",
        r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\s*[-–]\s*(Present|Now|\d{4})",
        r"\b(0?[1-9]|1[0-2])[./-](\d{2,4})\s*[-–]\s*(0?[1-9]|1[0-2])[./-](\d{2,4})\b",
    ]

    for pattern in patterns:
        text = re.sub(pattern, lambda m: f"[DATE]{m.group(0)}[/DATE]", text, flags=re.IGNORECASE)

    text = re.sub(r"\bn(Jetzt|Heute)\b", r"\1", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(Jetzt|Derzeit|Aktuell|Heute)\b", "Present", text, flags=re.IGNORECASE)
    return text


def merge_floating_dates(text: str) -> str:
    """Fügt Datumsteile zusammen, die durch Zeilenumbrüche getrennt wurden."""
    text = re.sub(r'(?<!\d)(\d{2}\.\d{2})\s*\n\s*(\d{2}\.\d{2})(?!\d)', r'\1 – \2', text)
    text = re.sub(r'(?<!\d)(\d{2}/\d{4})\s*\n\s*(\d{2}/\d{4})(?!\d)', r'\1 – \2', text)
    return text

# ============================================================
# 2️⃣.5️⃣ Projekte mit Datumszeilen verbinden
# ============================================================
def merge_project_blocks(text: str) -> str:
    """
    Combines role lines and date lines into a single block:
    'Lead BI Developer - Inpro Analytics GmbH' + '01.23 – Jetzt'
    → 'Lead BI Developer - Inpro Analytics GmbH 01.23 – Jetzt'
    """
    # Join dates that appear on a separate line with the previous line
    text = re.sub(r'(\n)(\d{1,2}[./]\d{2}\s*[–-]\s*(Jetzt|Heute|Present|\d{1,2}[./]\d{2}))', r' \2', text)
    text = re.sub(r'(\n)(\d{4}\s*[–-]\s*(Present|\d{4}))', r' \2', text)

    # Instead of lookbehind, use a safe pattern with a backreference
    text = re.sub(
        r'(\b(?:Developer|Engineer|Architect|Consultant|Manager|Lead|Analyst|Director|Specialist))\s*\n\s*(\d{1,2}[./]\d{2}\s*[–-]\s*(?:Jetzt|Heute|Present|\d{1,2}[./]\d{2}))',
        r'\1 \2',
        text,
        flags=re.IGNORECASE,
    )

    return text


# ============================================================
# 3️⃣ Sektionen markieren & strukturieren
# ============================================================
def clean_text(text: str) -> str:
    """Erkennt und markiert Hauptsektionen wie [PROJECTS], [SKILLS], usw."""
    text = re.sub(r"\[\d+\]|\(\d+\)", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)

    section_markers = {
        r"(?i)(Domains?|Industries):?": "[DOMAINS]",
        r"(?i)(Languages?|Sprachen|Sprachkenntnisse):?": "[LANGUAGES]",
        r"(?i)(Education|Studium|Ausbildung|Academic Background):?": "[EDUCATION]",
        r"(?i)(Profile|Summary|Über mich|Professional Summary):": "[PROFILE_SUMMARY]",
        r"(?i)(Projects?|Experience|Berufserfahrung|Work Experience):?": "[PROJECTS]",
        r"(?i)(Skills|Technologies|Kompetenzen|Tools):?": "[SKILLS]",
    }

    for pattern, marker in section_markers.items():
        text = re.sub(pattern, f"\n{marker}\n\\1", text)

    tags = ["DOMAINS", "SKILLS", "LANGUAGES", "EDUCATION", "PROJECTS", "PROFILE_SUMMARY"]
    for i, tag in enumerate(tags):
        next_tags = tags[i + 1:]
        next_pattern = "|".join(f"\\[{t}\\]" for t in next_tags) if next_tags else "$"

        # Explicitly close the section so it doesn't consume the rest of the text
        text = re.sub(
            rf"(\[{tag}\])(.*?)(?=\n({next_pattern})|\Z)",
            rf"\1\2[/{tag}]\n",
            text,
            flags=re.DOTALL,
        )
    text = re.sub(r"\]\s*\[", "]\n\n[", text)

    # Zusätzliche GPT-Hilfen
    text = re.sub(
        r"\[EDUCATION\]",
        "[EDUCATION]\nKontext: Dies sind akademische Qualifikationen, keine Berufserfahrung.\n",
        text,
    )
    text = re.sub(
        r"\[PROJECTS\]",
        "[PROJECTS]\nKontext: Dies sind berufliche Projekte, oft im Rahmen von Tätigkeiten.\n",
        text,
    )

    return text.strip()


def normalize_structure(text: str) -> str:
    """
    Fügt semantische Tags für schwach strukturierte Lebensläufe hinzu.
    Zum Beispiel: "worked on several projects..." → [PROJECTS]
    """
    replacements = {
        r"(?i)\b(profile|about me|summary)\b": "[PROFILE_SUMMARY]",
        r"(?i)\b(experience|employment|projects?|career)\b": "[PROJECTS]",
        r"(?i)\b(education|studies|academic background)\b": "[EDUCATION]",
        r"(?i)\b(skills|technologies|competencies|tools)\b": "[SKILLS]",
        r"(?i)\b(languages|sprachkenntnisse)\b": "[LANGUAGES]",
    }

    for pattern, tag in replacements.items():
        text = re.sub(pattern, tag, text)

    return text

# ============================================================
# 4️⃣ Deterministic input compression (token reduction)
# ============================================================
def clean_cv_text(text: str) -> str:
    """
    Compress text for LLM input: remove noise while preserving all semantic content.
    - Removes page markers, long URLs, duplicate lines, closing section tags.
    - Removes German context hints (no value for English extraction).
    - Collapses whitespace and empty lines.
    """
    # Remove page markers (English/German)
    text = re.sub(r"(?i)\b(page|seite)\s+\d+\s+(of|von)\s+\d+\b", "", text)

    # Remove long URLs (>40 chars) — they waste tokens, GPT doesn't need them
    text = re.sub(r"https?://\S{40,}", "", text)

    # Remove German context hints injected by clean_text()
    text = re.sub(r"Kontext:.*?\n", "", text)

    # Remove closing section tags — opening tags are sufficient for GPT
    text = re.sub(r"\[/[A-Z_]+\]", "", text)

    # Remove decorative separator lines (--- or ===)
    text = re.sub(r"^[-–—=]{3,}\s*$", "", text, flags=re.MULTILINE)

    # Deduplicate consecutive identical lines
    lines = text.split("\n")
    deduped = []
    prev = None
    for line in lines:
        stripped = line.strip()
        if stripped and stripped == prev:
            continue
        deduped.append(stripped)
        prev = stripped
    text = "\n".join(deduped)

    # Collapse multiple empty lines into one
    text = re.sub(r"\n{3,}", "\n", text)

    # Collapse multiple spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Remove remaining empty lines
    text = "\n".join(line for line in text.split("\n") if line.strip())

    return text.strip()


# ============================================================
# 5️⃣ Hauptfunktion zur Vorbereitung des CV-Texts
# ============================================================
def prepare_cv_text(pdf_path: str, cache_dir="data_output") -> tuple[str, str]:
    """
    Extracts text from the PDF, normalizes structure, and prepares it for GPT.
    Translation is handled by the GPT extraction prompt itself (multilingual input supported).
    Returns: (prepared_text, raw_text).
    """
    import os

    os.makedirs(cache_dir, exist_ok=True)

    pages = extract_text_by_page(pdf_path)
    raw_text = "\n\n".join(pages)

    tagged_text = raw_text
    tagged_text = merge_project_blocks(tagged_text)
    
    # Remove any existing date tags
    tagged_text = re.sub(r'\[DATE\]|\[/DATE\]', '', tagged_text)

    tagged_text = re.sub(r"[^\w\s\.\-/–—:,#+]", " ", tagged_text)
    tagged_text = re.sub(r"\s{3,}", "\n", tagged_text)
    tagged_text = re.sub(r"[ \t]+", " ", tagged_text)
    tagged_text = re.sub(r"\n{2,}", "\n", tagged_text)

    cleaned_text = clean_text(tagged_text)

    # normalized_text = normalize_structure(cleaned_text)
    normalized_text = cleaned_text
    
    final_text = (
        "[CV_START]\n"
        "The following is a professional CV. Detect all project durations accurately.\n"
        + normalized_text +
        "\n[CV_END]"
    )
    with open(os.path.join(cache_dir, "prepared_text.txt"), "w", encoding="utf-8") as f:
        f.write(final_text)

    # Lightweight cleanup for raw_text
    raw_text = re.sub(r"[^\w\s\.\-/–—:,#+]", " ", raw_text)
    raw_text = re.sub(r"\s{3,}", "\n", raw_text)
    raw_text = re.sub(r"[ \t]+", " ", raw_text)
    raw_text = re.sub(r"\n{2,}", "\n", raw_text)

    return final_text, raw_text


# ============================================================
# 🧪 Lokaler Testlauf
# ============================================================
if __name__ == "__main__":
    path = "data_input/CV Manuel Wolfsgruber.pdf"
    os.makedirs("debug", exist_ok=True)

    prepared, raw = prepare_cv_text(path)

    with open("debug/full_prepared_text.txt", "w", encoding="utf-8") as f:
        f.write(prepared)
    with open("debug/raw_extracted_text.txt", "w", encoding="utf-8") as f:
        f.write(raw)

    print("\n✅ Alles fertig!")
    print("📄 full_prepared_text.txt — vorbereiteter Text")
    print("🗒 raw_extracted_text.txt — Rohtext aus dem PDF")
