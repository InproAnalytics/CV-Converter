import re
import json
import ast
from collections import defaultdict
from datetime import datetime

# ===============================================
# 🔤 Languages
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
# 🗓 Dates
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

def normalize_year(text: str) -> str:
    """
    Normalisiert Jahresangaben aus verschiedenen Formaten.
    Unterstützte Beispiele:
    '07.21' → '2021'
    '07/2021' → '2021'
    '2020' → '2020'
    '21' → '2021'
    """
    import re

    if not text:
        return ""

    text = str(text).strip()

    # Versuche, Jahr mit 4 Ziffern zu finden (z. B. 2021 oder 1999)
    match = re.search(r"\b(19|20)\d{2}\b", text)
    if match:
        return match.group(0)

    # Zweistelliges Jahr erkennen und auf 20xx mappen
    match = re.search(r"\b(\d{2})\b", text)
    if match:
        year = int(match.group(1))
        # Heuristik: falls < 30 → 2000+, sonst 1900+
        return f"20{year:02d}" if year < 30 else f"19{year:02d}"

    return ""


# ============================================================
# 📆 Fix open date ranges
# ============================================================
def fix_open_date_ranges(text_or_json):
    if isinstance(text_or_json, dict):
        for key, value in text_or_json.items():
            if isinstance(value, dict):
                text_or_json[key] = fix_open_date_ranges(value)
            elif isinstance(value, list):
                new_list = []
                for item in value:
                    if isinstance(item, (dict, str)):
                        new_list.append(fix_open_date_ranges(item))
                    else:
                        new_list.append(item)
                text_or_json[key] = new_list
            elif key.lower() in ["duration", "years_of_experience"] and isinstance(value, str):
                text_or_json[key] = fix_open_date_ranges(value)
        return text_or_json

    text = str(text_or_json)
    month_map = {
        "01": "Jan", "1": "Jan", "02": "Feb", "2": "Feb", "03": "Mar", "3": "Mar",
        "04": "Apr", "4": "Apr", "05": "May", "5": "May", "06": "Jun", "6": "Jun",
        "07": "Jul", "7": "Jul", "08": "Aug", "8": "Aug", "09": "Sep", "9": "Sep",
        "10": "Oct", "11": "Nov", "12": "Dec"
    }

    for num, name in month_map.items():
        text = re.sub(rf"\b{num}\.?\s?(\d{{2}})\b", rf"{name} 20\1", text)

    text = re.sub(r"([A-Za-z]{{3}} 20\d{{2}})\s*[–-]\s*$", r"\1 – Present", text)
    text = re.sub(r"\b(0?[1-9]|1[0-2])[./](20\d{2})\b", lambda m: f"{month_map[m.group(1).zfill(2)]} {m.group(2)}", text)

    return text

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

def split_skills_overview_rows(skills):
    if not isinstance(skills, list):
        return []

    result = []
    for row in skills:
        if not isinstance(row, dict):
            continue

        category = str(row.get("category", "")).strip()
        tools = row.get("tools", [])

        # 🧠 Normalize: if it's a string, split it; if it's a list, keep it
        if isinstance(tools, str):
            tools_list = [t.strip() for t in re.split(r"[,/]", tools) if t.strip()]
        elif isinstance(tools, list):
            tools_list = [t.strip() for t in tools if isinstance(t, str) and t.strip()]
        else:
            tools_list = []

        years_raw = row.get("years_of_experience", "")
        years = str(years_raw).strip() if years_raw is not None else ""
        
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
            years_clean = re.sub(r"[^\d.]", "", years)
            grouped[category]["years"].append(float(years_clean) if years_clean else 0)
        except Exception:
            grouped[category]["years"].append(0)


    final_overview = []
    for category, data in grouped.items():
        final_overview.append({
            "category": category,
            "tools": sorted(set(data["tools"])),
            "years_of_experience": str(int(max(data["years"]))) if data["years"] else "0"
        })

    return final_overview

def filter_skills_overview(skills):
    seen = set()
    filtered = []
    for item in skills:
        category = item.get("category")
        tools = item.get("tools", [])
        years = item.get("years_of_experience", "").strip()

        # Remove only junk: missing category or missing tools
        if not category or not tools:
            continue

        key = (category, tuple(sorted(tools)))
        if key not in seen:
            seen.add(key)
            filtered.append(item)
    return filtered

# Guard for nested string fields
def safe_parse_if_str(field):
    if isinstance(field, str):
        try:
            return json.loads(field)
        except json.JSONDecodeError:
            try:
                return ast.literal_eval(field)
            except Exception:
                return []
    return field
# ===============================================
# 🏭 Domain / industry normalization
INDUSTRY_KEYWORDS = {
    # --- Financial ---
    "bank": "banking",
    "banking": "banking",
    "financial": "financial services",
    "finance": "financial services",
    "financing": "financial services",
    "insurance": "insurance",
    "insurer": "insurance",
    "wealth": "wealth management",
    "asset management": "asset management",
    "investment": "investment management",

    # --- Consulting / Professional Services ---
    "consult": "consulting",
    "advisory": "consulting",
    "professional services": "professional services",

    # --- Telecom / Media ---
    "telecom": "telecommunications",
    "telecommunications": "telecommunications",
    "mobile operator": "telecommunications",
    "isp": "telecommunications",

    # --- Education ---
    "university": "education",
    "school": "education",
    "college": "education",
    "kindergarten": "education",
    "academy": "education",
    "educational institution": "education",

    # --- Healthcare ---
    "hospital": "healthcare",
    "clinic": "healthcare",
    "medical": "healthcare",
    "healthcare": "healthcare",
    "pharma": "pharmaceuticals",
    "pharmaceutical": "pharmaceuticals",

    # --- Manufacturing / Industry ---
    "manufacturing": "manufacturing",
    "factory": "manufacturing",
    "industrial": "manufacturing",
    "production": "manufacturing",

    # --- Retail / Commerce ---
    "retail": "retail",
    "wholesale": "retail",
    "store": "retail",
    "e-commerce": "e-commerce",
    "ecommerce": "e-commerce",
    "online shop": "e-commerce",
    "marketplace": "e-commerce",

    # --- Public / Government ---
    "government": "public sector",
    "public sector": "public sector",
    "municipality": "public sector",
    "ministry": "public sector",

    # --- IT companies (use with extra caution) ---
    # Add ONLY if explicitly stated as the company's business domain
    "software company": "software industry",
    "it company": "software industry",
    "saas provider": "software industry",
}


def normalize_domains(domains, data):
    text = json.dumps(data, ensure_ascii=False).lower()
    result = set()

    # 1️⃣ If GPT provided domains, accept ONLY if they are industries
    if isinstance(domains, list):
        for d in domains:
            d_low = d.lower()
            for industry in INDUSTRY_KEYWORDS.values():
                if industry in d_low:
                    result.add(industry)

    # 2️⃣ Fallback: search within CV text / companies
    for key, industry in INDUSTRY_KEYWORDS.items():
        if key in text:
            result.add(industry)

    return [d.title() for d in sorted(result)]

def normalize_project_domains(project: dict) -> list[str]:
    if not isinstance(project, dict):
        return []
    return normalize_domains(project.get("domains", []), project)

# ===============================================
# Main entry point
# ===============================================

def postprocess_filled_cv(data: dict, original_text: str = "") -> dict:
    # If projects arrived as a string, parse them back into a list
    if isinstance(data.get("projects_experience"), str):
        import json, ast

        try:
            data["projects_experience"] = json.loads(data["projects_experience"].replace("'", '"'))
        except Exception:
            try:
                data["projects_experience"] = ast.literal_eval(data["projects_experience"])
            except Exception:
                data["projects_experience"] = []

    # Apply duration normalization/fixes
    data["projects_experience"] = unify_durations(data.get("projects_experience", []))
    data["projects_experience"] = fix_open_date_ranges(data["projects_experience"])

    # Skills
    data["hard_skills"] = clean_duplicates_in_skills(data.get("hard_skills", {}))

    # Skills overview
    flat_skills = split_skills_overview_rows(data.get("skills_overview", []))
    reconstructed = generate_skills_overview(flat_skills)
    data["skills_overview"] = filter_skills_overview(reconstructed)

    # Project domains (hybrid: GPT output + fallback via keywords per project)
    for project in data.get("projects_experience", []):
        if not isinstance(project, dict):
            continue
        project["domains"] = normalize_project_domains(project)

    # Global domains: derived ONLY from project domains (no global extraction)
    project_domains = []
    for p in data.get("projects_experience", []):
        if isinstance(p, dict) and isinstance(p.get("domains"), list):
            project_domains.extend([str(x) for x in p.get("domains", []) if str(x).strip()])
    combined = sorted({d.strip().title() for d in project_domains if str(d).strip()})
    data["domains"] = combined

    # Format responsibilities for each project
    for project in data.get("projects_experience", []):
        if isinstance(project, dict) and "responsibilities" in project:
            project["responsibilities"] = format_responsibilities(project.get("responsibilities", []))

    # Clean text fields
    data = clean_text_fields(data)

    # Safety net: if it's a string again after processing, parse again
    if isinstance(data.get("projects_experience"), str):
        import ast
        try:
            data["projects_experience"] = ast.literal_eval(data["projects_experience"])
        except Exception:
            data["projects_experience"] = []

    # Auto-fill role and duration if GPT missed them
    for project in data.get("projects_experience", []):
        title = project.get("project_title", "") or ""
        overview = project.get("overview", "") or ""
        tech = " ".join(project.get("tech_stack", [])) if project.get("tech_stack") else ""

        combined_text = " ".join([title, overview, tech])

        # --- ROLE (only from the current project) ---
        if not project.get("role"):
            role_match = re.search(
                r"\b(CEO|Lead|Senior|Junior|Data|BI|Cloud|AI|ML|DevOps)?\s*"
                r"(Developer|Engineer|Architect|Consultant|Manager|Analyst|Director|Specialist)\b",
                combined_text,
                re.I,
            )
            if role_match:
                parts = [p for p in role_match.groups() if p]
                project["role"] = " ".join(parts).strip().title()
            else:
                project["role"] = ""

        # --- DURATION (only from the current project's text) ---
        if not project.get("duration"):
            duration_match = re.search(
                r"(\d{1,2}\.\d{2}|\b(19|20)\d{2}\b)\s*[–-]\s*(Jetzt|Heute|Present|\d{1,2}\.\d{2}|\b(19|20)\d{2}\b)",
                combined_text,
            )
            if duration_match:
                start = duration_match.group(1)
                end = duration_match.group(3)
                project["duration"] = f"{start} – {end}"
            else:
                project["duration"] = ""
    return data


# ===============================================
# Text cleanup and structure validation
# ===============================================

def clean_text_fields(data):
    """Recursively cleans strings from noise and special symbols."""
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
    """Checks that all key sections are present."""
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


# ===============================================
# 📝 Responsibilities formatting
# ===============================================

def format_responsibilities(responsibilities):
    """
    Format responsibilities into detailed, structured bullet points.

    Goals:
    - Break long paragraphs into informative bullet points (70–100 words each)
    - Preserve maximum information and context
    - Maintain readability through structure
    - Final target: up to 5 bullets, ~350–500 words per project (only if source text supports it)
    """
    if not responsibilities:
        return []
    
    if isinstance(responsibilities, str):
        responsibilities = [responsibilities]
    
    if not isinstance(responsibilities, list):
        return []
    
    formatted = []
    
    for item in responsibilities:
        if not isinstance(item, str):
            continue
            
        item = item.strip()
        if not item:
            continue
        
        word_count = len(item.split())

        # If the item is already in the target range (65-110 words), keep it as-is
        if 65 <= word_count <= 110:
            formatted.append(item)
            continue

        # If it's shorter than 65 words, keep it (we cannot safely expand it)
        if word_count < 65:
            formatted.append(item)
            continue
        
        # Split long text into sentences
        sentences = re.split(r'(?<=[.!?])\s+', item)
        
        current_bullet = []
        current_word_count = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            sentence_words = len(sentence.split())
            
            # If adding the sentence won't exceed 110 words
            if current_word_count + sentence_words <= 110:
                current_bullet.append(sentence)
                current_word_count += sentence_words
            else:
                # Save accumulated content and start a new bullet
                if current_bullet:
                    formatted.append(' '.join(current_bullet))
                current_bullet = [sentence]
                current_word_count = sentence_words
        
        # Add the final accumulated bullet
        if current_bullet:
            formatted.append(' '.join(current_bullet))
    
    # Limit to 5 bullets
    if len(formatted) > 5:
        formatted = formatted[:5]
    
    return formatted