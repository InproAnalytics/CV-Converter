import re
import json
from collections import defaultdict
from datetime import datetime
from utils import normalize_year

# ===============================================
# 🔤 Языки
# ===============================================

def unify_languages(langs, original_text=None):
    normalized = []

    for entry in langs:
        if isinstance(entry, str):
            entry = {"language": entry, "level": ""}
        if not isinstance(entry, dict):
            continue

        lang = entry.get("language", "").strip().capitalize()
        level = entry.get("level", "").strip()
        if not level:
            level = "Unspecified"
        if lang:
            normalized.append({"language": lang, "level": level})

    if not normalized and original_text:
        text = original_text.lower()
        known_langs = [
            "english", "german", "french", "spanish", "italian",
            "russian", "polish", "czech", "portuguese", "chinese",
            "japanese", "korean", "dutch", "turkish", "swedish"
        ]
        for lang in known_langs:
            if re.search(rf"\b{lang}\b", text):
                snippet = text[max(0, text.find(lang) - 40): text.find(lang) + 60]
                match = re.search(r"\b([ABC][12]\+?)\b", snippet, re.I)
                level = match.group(1).upper() if match else "Unspecified"
                normalized.append({"language": lang.capitalize(), "level": level})

    seen = set()
    unique = []
    for item in normalized:
        key = item["language"].lower()
        if key not in seen:
            unique.append(item)
            seen.add(key)

    return unique

# ===============================================
# 🗓 Даты
# ===============================================

def unify_durations(projects):
    months = {
        "01": "Jan", "1": "Jan", "02": "Feb", "2": "Feb", "03": "Mar", "3": "Mar",
        "04": "Apr", "4": "Apr", "05": "May", "5": "May", "06": "Jun", "6": "Jun",
        "07": "Jul", "7": "Jul", "08": "Aug", "8": "Aug", "09": "Sep", "9": "Sep",
        "10": "Oct", "11": "Nov", "12": "Dec"
    }

    for project in projects:
        duration = project.get("duration", "").strip()
        if not duration:
            continue

        duration = re.sub(r"[–—−]+", "-", duration)
        duration = re.sub(r"\s*-\s*", " - ", duration)
        duration = re.sub(r"(?i)\b(Jetzt|Heute|Aktuell|Now|Present|Gegenwärtig|Momentan|Derzeit)\b", "Present", duration)

        # 1: "07.21 - 12.23"
        m = re.match(r"^\s*(\d{1,2})[./-](\d{2,4})\s*-\s*(\d{1,2})[./-](\d{2,4}|Present)\s*$", duration)
        if m:
            sm, sy, em, ey = m.groups()
            sy = normalize_year(sy)
            ey = "Present" if "Present" in ey else normalize_year(ey)
            project["duration"] = f"{months.get(sm.zfill(2), 'Jan')} {sy} – {months.get(em.zfill(2), 'Jan')} {ey}"
            continue

        # 2: "07.21 –"
        m = re.match(r"^\s*(\d{1,2})[./-](\d{2,4})\s*-\s*$", duration)
        if m:
            sm, sy = m.groups()
            sy = normalize_year(sy)
            project["duration"] = f"{months.get(sm.zfill(2), 'Jan')} {sy} – Present"
            continue

        # 3: "2020 – 2023"
        m = re.match(r"^\s*((19|20)\d{2})\s*-\s*((?:19|20)?\d{2}|Present)\s*$", duration)
        if m:
            sy, _, ey = m.groups()
            if len(ey) == 2:
                ey = "20" + ey
            if int(sy) > int(ey.replace("Present", str(datetime.now().year))):
                sy, ey = ey, sy
            project["duration"] = f"{sy} – {ey}"
            continue

        # 4: Already valid "Mar 2020 - Oct 2023"
        m = re.match(r"(?i)^\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4} - .*", duration)
        if m:
            project["duration"] = duration.replace("-", "–").strip()
            continue

        # 5: Fallback from text overview
        overview = project.get("overview", "")
        match = re.search(r"(\b\d{4}\b).{0,20}?(\b\d{4}\b|Present)", overview)
        if match:
            y1, y2 = match.groups()
            if int(y1) > int(y2.replace("Present", str(datetime.now().year))):
                y1, y2 = y2, y1
            project["duration"] = f"{y1} – {y2}"

    return projects

# ===============================================
# 🧹 Очистка hard_skills
# ===============================================

def clean_duplicates_in_skills(skills):
    if not isinstance(skills, dict):
        return {}
    cleaned = {}
    for cat, items in skills.items():
        if not isinstance(items, list):
            continue
        seen = set()
        unique = []
        for item in items:
            value = item.strip().lower() if isinstance(item, str) else str(item).strip().lower()
            if value and value not in seen:
                unique.append(item)
                seen.add(value)
        cleaned[cat] = unique
    return cleaned

# ===============================================
# 📊 skills_overview: разделить инструменты
# ===============================================

def split_skills_overview_rows(skills):
    if not isinstance(skills, list):
        return []

    result = []
    for row in skills:
        if not isinstance(row, dict):
            continue

        category = row.get("category", "").strip()
        tools = row.get("tools", [])

        # 🧠 Нормализуем: если строка — разбиваем, если список — оставляем
        if isinstance(tools, str):
            tools_list = [t.strip() for t in re.split(r"[,/]", tools) if t.strip()]
        elif isinstance(tools, list):
            tools_list = [t.strip() for t in tools if isinstance(t, str) and t.strip()]
        else:
            tools_list = []

        years = row.get("years_of_experience", "").strip()

        for tool in tools_list:
            result.append({
                "category": category,
                "tool": tool,
                "years_of_experience": years
            })

    return result
   
   
def generate_skills_overview(skills_overview_raw):
    if not isinstance(skills_overview_raw, list):
        return []

    grouped = defaultdict(lambda: {"tools": [], "years": []})

    for row in skills_overview_raw:
        category = row.get("category", "").strip()
        tool = row.get("tool", "").strip()
        years = row.get("years_of_experience", "").strip()

        if not category or not tool:
            continue

        grouped[category]["tools"].append(tool)
        try:
            grouped[category]["years"].append(float(years))
        except ValueError:
            continue

    final_overview = []
    for category, data in grouped.items():
        final_overview.append({
            "category": category,
            "tools": sorted(set(data["tools"])),
            "years_of_experience": str(int(max(data["years"]))) if data["years"] else "0"
        })

    return final_overview

# ===============================================
# 🧩 Основной вызов
# ===============================================

def postprocess_filled_cv(data: dict, original_text: str = "") -> dict:
    data["languages"] = unify_languages(data.get("languages", []), original_text)
    data["projects_experience"] = unify_durations(data.get("projects_experience", []))
    data["hard_skills"] = clean_duplicates_in_skills(data.get("hard_skills", {}))

    # 🧠 Только если skills_overview отсутствует или пуст — пересчитать
    if not data.get("skills_overview"):
        flat_skills = split_skills_overview_rows(data.get("skills_overview", []))
        data["skills_overview"] = generate_skills_overview(flat_skills)

    return data

# ===============================================
# 🧼 Очистка текстов и проверка структуры
# ===============================================

def clean_text_fields(data):
    """Рекурсивно очищает строки от мусора и спецсимволов."""
    if isinstance(data, dict):
        return {k: clean_text_fields(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_text_fields(v) for v in data]
    elif isinstance(data, str):
        text = re.sub(r"[ \t]+", " ", data)
        text = re.sub(r"[\u2022\u2023\u25E6\u2043\u2219\u00B7]", "-", text)
        text = re.sub(r"\s*\n\s*", "\n", text)
        text = text.replace("\xa0", " ").strip()
        return text
    return data


def validate_cv_schema(cv_json):
    """Проверяет, что все ключевые разделы присутствуют."""
    required_fields = [
        "profile_summary",
        "education",
        "projects_experience",
        "hard_skills",
        "languages",
        "domains",
        "skills_overview"
    ]
    missing = [f for f in required_fields if f not in cv_json or not cv_json[f]]
    return missing

