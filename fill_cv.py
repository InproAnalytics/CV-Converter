import json
import re
import logging
from utils import has_empty_fields
from chatgpt_client import ask_chatgpt


# ============================================================
# 1️⃣ Автозаполнение с GPT
# ============================================================
def auto_fill_with_gpt(data: dict) -> dict:
    try:
        filled = ask_chatgpt(data, mode="fix")
        if isinstance(filled, dict):
            logging.info("✅ GPT-based autofill completed.")
            return filled
        return data
    except Exception as e:
        logging.warning(f"⚠️ GPT autofill failed: {e}")
        return fill_missing_fields(data)


# ============================================================
# 2️⃣ Fallback — локальное заполнение
# ============================================================
def fill_missing_fields(data, prefix=""):
    if isinstance(data, dict):
        for key, value in data.items():
            full_key = f"{prefix}{key}"
            if isinstance(value, str) and value.strip() == "":
                data[key] = _default_value_for_key(key)
            elif isinstance(value, list):
                if not value:
                    data[key] = []
                else:
                    for i, item in enumerate(value):
                        fill_missing_fields(item, prefix=f"{full_key}[{i}].")
            elif isinstance(value, dict):
                fill_missing_fields(value, prefix=f"{full_key}.")
    return data


# ============================================================
# 3️⃣ Значения по умолчанию
# ============================================================
def _default_value_for_key(key: str):
    key_lower = key.lower()
    if "name" in key_lower:
        return "Unknown"
    if "title" in key_lower:
        return "Specialist"
    if "education" in key_lower:
        return "Not specified"
    if "language" in key_lower:
        return []
    if "domain" in key_lower:
        return []
    if "summary" in key_lower:
        return "No profile summary available."
    if "skills" in key_lower:
        return {}
    if "projects" in key_lower:
        return []
    if "website" in key_lower:
        return ""
    return ""


# ============================================================
# 4️⃣ Главная точка запуска
# ============================================================
def fill_cv_data(data: dict) -> dict:
    if not has_empty_fields(data):
        logging.info("ℹ️ No empty fields detected — skipping autofill.")
        return data

    logging.info("🚀 Starting autofill process...")
    try:
        return auto_fill_with_gpt(data)
    except Exception as e:
        logging.error(f"❌ Unexpected error in autofill: {e}")
        return fill_missing_fields(data)


# ============================================================
# 5️⃣ Коррекция дат по оригинальному тексту (поиск рядом)
# ============================================================
def fix_project_dates_from_text(projects, original_text):
    for p in projects:
        title = p.get("project_title", "")
        duration = p.get("duration", "")
        if not title:
            continue

        pattern = rf"{re.escape(title)}.*?(\b\d{{4}}\b).*?(\b\d{{4}}\b|Present)"
        match = re.search(pattern, original_text, re.I | re.S)
        if match:
            real_dur = f"{match.group(1)} – {match.group(2)}"
            if real_dur != duration:
                logging.info(f"🕓 Updating duration for '{title}': {duration} → {real_dur}")
                p["duration"] = real_dur
    return projects


# ============================================================
# ✅ Локальный тест
# ============================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    test_data = {
        "full_name": "Manuel Wolfsgruber",
        "title": "",
        "education": "",
        "languages": [{"language": "", "level": ""}],
        "domains": [],
        "profile_summary": "",
        "hard_skills": {"cloud_platforms": [], "programming_languages": []},
        "projects_experience": [],
        "skills_overview": [],
        "website": ""
    }

    logging.info("📄 Input before filling:")
    print(json.dumps(test_data, indent=2, ensure_ascii=False))

    filled = fill_cv_data(test_data)

    logging.info("\n📄 Output after filling:")
    print(json.dumps(filled, indent=2, ensure_ascii=False))
