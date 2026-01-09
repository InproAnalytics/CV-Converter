import fitz  # PyMuPDF
import re
import os
from langdetect import detect, DetectorFactory
from chatgpt_client import ask_chatgpt

DetectorFactory.seed = 0  # для стабильности определения языка


# ============================================================
# 1️⃣ Извлечение текста из PDF
# ============================================================
def extract_text_by_page(pdf_path: str) -> list[str]:
    """Извлекает структурированный текст из PDF постранично."""
    doc = fitz.open(pdf_path)
    pages_text = []
    for page in doc:
        text = page.get_text("blocks") or page.get_text("text")
        if isinstance(text, list):
            text = "\n".join([b[4] for b in text if b[4].strip()])
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{2,}", "\n", text)
        pages_text.append(text.strip())
    doc.close()
    return pages_text


# ============================================================
# 2️⃣ Тегирование дат
# ============================================================
def tag_dates(text: str) -> str:
    """
    Находит диапазоны и одиночные даты (включая немецкие форматы)
    и оборачивает их в [DATE]...[/DATE].
    """
    # Основные паттерны диапазонов (07.21 – 12.23, 01.23 – Jetzt)
    patterns = [
        r"\b(0?[1-9]|1[0-2])\.(\d{2})\s*[-–]\s*(0?[1-9]|1[0-2])\.(\d{2})\b",
        r"\b(0?[1-9]|1[0-2])\.(\d{2})\s*[-–]\s*(Jetzt|Derzeit|Heute|Present|Now|Aktuell)\b",
        r"\b(0?[1-9]|1[0-2])\.\d{2}\b\s*[-–]\s*$",  # открытый конец диапазона
        r"\b(0?[1-9]|1[0-2])\/(\d{4})\s*[-–]\s*(0?[1-9]|1[0-2])\/(\d{4})\b",
        r"\b(0?[1-9]|1[0-2])\/(\d{4})\s*[-–]\s*(Jetzt|Derzeit|Heute|Present|Now|Aktuell)\b",
        # слова вида "seit 07.21" или "since 07/2021"
        r"(?i)\b(seit|since)\s+(0?[1-9]|1[0-2])[./](\d{2,4})\b",
        # диапазоны с годами
        r"\b(20\d{2}|19\d{2})\s*[-–]\s*(20\d{2}|Present|Now|Heute|Jetzt|Aktuell)\b",
        # англоязычные месяцы
        r"(?:(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*)\s+\d{4}\s*[-–]\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)?[a-z]*\s*\d{4}",
    ]

    for pattern in patterns:
        text = re.sub(pattern, lambda m: f"[DATE]{m.group(0)}[/DATE]", text, flags=re.IGNORECASE)

    # Преобразуем отдельные “Jetzt”, “Derzeit” и т.п. в Present
    text = re.sub(r"\b(Jetzt|Derzeit|Aktuell|Heute)\b", "Present", text, flags=re.IGNORECASE)

    return text


def merge_floating_dates(text: str) -> str:
    """
    Объединяет даты, разделённые переносом строки, например:
    07.21
    12.23  → 07.21 – 12.23
    """
    text = re.sub(r'(?<!\d)(\d{2}\.\d{2})\s*\n\s*(\d{2}\.\d{2})(?!\d)', r'\1 – \2', text)
    text = re.sub(r'(?<!\d)(\d{2}/\d{4})\s*\n\s*(\d{2}/\d{4})(?!\d)', r'\1 – \2', text)
    return text


# ============================================================
# 3️⃣ Очистка и нормализация структуры
# ============================================================
def clean_text(text: str) -> str:
    """
    Добавляет структурные маркеры секций CV для GPT, с явными границами.
    Делит резюме по ключевым разделам: Education, Projects, Skills и т.д.
    """
    # Очистка лишних символов
    text = re.sub(r"\[\d+\]|\(\d+\)", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)

    # 🔹 Ключевые секции
    section_markers = {
        r"(?i)(Domains?|Industries):?": "[DOMAINS]",
        r"(?i)(Languages?|Sprachen|Sprachkenntnisse):?": "[LANGUAGES]",
        r"(?i)(Education|Studium|Ausbildung|Academic Background):?": "[EDUCATION]",
        r"(?i)(Profile|Summary|Über mich|Professional Summary|Career Summary):": "[PROFILE_SUMMARY]",
        r"(?i)(Projects?|Experience|Berufserfahrung|Employment|Work Experience):?": "[PROJECTS]",
        r"(?i)(Skills|Technologies|Kompetenzen|Tools|Professional skills|Technical skills):?": "[SKILLS]",
    }

    # Вставляем метки начала секции
    for pattern, marker in section_markers.items():
        text = re.sub(pattern, f"\n{marker}\n\\1", text)

    # 🧱 Явно закрываем каждую секцию
    tags = ["DOMAINS", "SKILLS", "LANGUAGES", "EDUCATION", "PROJECTS", "PROFILE_SUMMARY"]
    for i, tag in enumerate(tags):
        # Закрытие до начала следующей секции
        following_tags = tags[i + 1 :]
        if following_tags:
            next_tag_pattern = "|".join(f"\\[{t}\\]" for t in following_tags)
            text = re.sub(
                rf"\[{tag}\](.*?)(?=\n(?:{next_tag_pattern})|\Z)",
                rf"[{tag}]\1[/{tag}]\n",
                text,
                flags=re.DOTALL,
            )
        else:
            text = re.sub(
                rf"\[{tag}\](.*)",
                rf"[{tag}]\1[/{tag}]\n",
                text,
                flags=re.DOTALL,
            )

    # Убираем "приклеенные" строчки между секциями
    text = re.sub(r"\]\s*\[", "]\n\n[", text)

    # 🔹 Подсветим контекст для GPT
    text = re.sub(
        r"\[EDUCATION\]",
        "[EDUCATION]\nContext: These are academic degrees, research or study projects, not employment.\n",
        text,
    )
    text = re.sub(
        r"\[PROJECTS\]",
        "[PROJECTS]\nContext: These are professional or applied projects, often linked to employment or practical experience.\n",
        text,
    )

    return text.strip()


# ============================================================
# 4️⃣ Расширенная нормализация структуры (semantic tags)
# ============================================================
def normalize_structure(text: str) -> str:
    """Добавляет семантические теги для слабоструктурированных резюме."""
    text = re.sub(r"(?i)\b(profile|about me|summary)\b", "[PROFILE_SUMMARY]", text)
    text = re.sub(r"(?i)\b(experience|employment|projects?|career)\b", "[PROJECTS]", text)
    text = re.sub(r"(?i)\b(education|studies|academic background)\b", "[EDUCATION]", text)
    text = re.sub(r"(?i)\b(skills|technologies|competencies|tools)\b", "[SKILLS]", text)
    text = re.sub(r"(?i)\b(languages|sprachkenntnisse)\b", "[LANGUAGES]", text)
    return text


# ============================================================
# 5️⃣ Очистка списка обязанностей
# ============================================================
def clean_responsibilities(responsibilities, max_words=18, max_items=6):
    """Сокращает и нормализует список обязанностей."""
    cleaned = []
    for i, resp in enumerate(responsibilities):
        if i >= max_items:
            break
        resp = re.sub(
            r"(?i)\b(responsible\s+for|involved\s+in|participated\s+in|helped\s+to|tasked\s+with|working\s+on|assist(ed)?\s+in|support(ed)?\s+with)\b",
            "",
            resp.strip(),
        ).strip()
        words = resp.split()
        if len(words) > max_words:
            resp = " ".join(words[:max_words]) + "..."
        if resp:
            cleaned.append(resp[0].upper() + resp[1:])
    return cleaned


# ============================================================
# 6️⃣ Основная функция подготовки CV-текста
# ============================================================
def prepare_cv_text(pdf_path: str, cache_dir="data_output") -> str:
    """
    Извлекает текст, при необходимости переводит на английский,
    размечает даты, очищает и добавляет теги секций.
    Улучшено:
    - не теряет диапазоны дат;
    - сохраняет переносы в секциях;
    - объединяет страницы аккуратно.
    """
    os.makedirs(cache_dir, exist_ok=True)

    pages = extract_text_by_page(pdf_path)
    raw_text = "\n\n".join(pages)

    # --- Языковая детекция
    try:
        detected_lang = detect(raw_text)
    except Exception:
        detected_lang = "en"

    # --- Перевод при необходимости
    if detected_lang != "en":
        translation_prompt = f"""
Translate this CV text from German to English word-by-word, preserving the exact line structure.
Do NOT split or merge projects. Do NOT add numbering or new sections.
Preserve ALL original formatting and project boundaries.
TEXT:
{raw_text[:15000]}
"""
        result = ask_chatgpt(translation_prompt, mode="details")
        if isinstance(result, dict) and "raw_response" in result:
            raw_text = result["raw_response"]
        elif isinstance(result, str):
            raw_text = result

        raw_text = re.sub(r"(?i)\b(sprachen|sprachkenntnisse)\b", "Languages", raw_text)
        raw_text = re.sub(r"(?i)\b(ausbildung|bildung)\b", "Education", raw_text)
        raw_text = re.sub(r"(?i)\b(berufserfahrung|erfahrung|projects?|projekte)\b", "Experience", raw_text)
        raw_text = re.sub(r"(?i)\b(kenntnisse|skills|kompetenzen|technologien|tools)\b", "Skills", raw_text)

    # --- Тегируем диапазоны дат ДО очистки
    tagged_text = tag_dates(raw_text)

    # --- Бережная очистка: разрешаем символы для дат и дефисы
    tagged_text = re.sub(r"[^\w\s\.\-/–—:,]", " ", tagged_text)
    tagged_text = re.sub(r"\s{3,}", "\n", tagged_text)  # сохраняем переносы
    tagged_text = re.sub(r"[ \t]+", " ", tagged_text)
    tagged_text = re.sub(r"\n{2,}", "\n", tagged_text)

    # --- Добавляем секционные теги
    cleaned_text = clean_text(tagged_text)
    normalized_text = normalize_structure(cleaned_text)

    # --- Добавляем финальную аннотацию для GPT (улучшает качество дат)
    normalized_text = (
        "[CV_START]\n"
        "The following is a professional CV. Detect all project durations accurately.\n"
        + normalized_text +
        "\n[CV_END]"
    )

    # --- Сохраняем подготовленный текст
    with open(os.path.join(cache_dir, "prepared_text.txt"), "w", encoding="utf-8") as f:
        f.write(normalized_text)

    return normalized_text, raw_text


# ============================================================
# 🧪 Debug
# ============================================================
if __name__ == "__main__":
    path = "data_input/CV Manuel Wolfsgruber.pdf"  # или .pdf
    os.makedirs("debug", exist_ok=True)

    prepared, raw = prepare_cv_text(path)

    with open("debug/full_prepared_text.txt", "w", encoding="utf-8") as f:
        f.write(prepared)
    with open("debug/raw_extracted_text.txt", "w", encoding="utf-8") as f:
        f.write(raw)

    print("\n✅ Всё готово!")
    print("📄 full_prepared_text.txt — подготовленный текст")
    print("🗒 raw_extracted_text.txt — оригинальный текст из CV")
