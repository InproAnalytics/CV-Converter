import os
import re
import json
import logging
from dotenv import load_dotenv
from openai import OpenAI

# ============================================================
# 🔧 Инициализация
# ============================================================
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
logging.basicConfig(level=logging.INFO)

# ============================================================
# 🧠 Основная функция вызова GPT
# ============================================================
def ask_chatgpt(text, mode="details", base_structure=None):
    """
    Универсальная функция вызова GPT для CV-парсинга.
    Поддерживает режимы:
    - structure: выводит структуру JSON
    - details: извлекает все поля из текста
    - fix: заполняет пустые поля
    """
    if mode == "structure":
        task_description = "Extract only the structural JSON skeleton of the CV with all field names but empty values."
    elif mode == "fix":
        task_description = "Repair missing or empty fields logically, keeping the schema intact."
    else:
        task_description = "Extract structured CV data from text and return strictly formatted JSON only."

    allowed_categories = [
        "cloud_platforms", "devops_iac", "monitoring_security", "programming_languages",
        "containers_orchestration", "ci_cd_tools", "ai_ml_tools", "databases",
        "backend", "frontend", "security", "data_engineering", "etl_tools",
        "bi_tools", "analytics", "infrastructure_os", "other_tools"
    ]

    prompt = f"""
TASK: {task_description}

INSTRUCTIONS:

- Extract a complete, structured JSON strictly following the provided SCHEMA.
- Detect the candidate’s actual domain (e.g., Cloud, DevOps, BI, Data Engineering) based on tools, project content, and terminology.
- Avoid assumptions — rely only on what's clearly stated or strongly implied in the resume.

=== PROJECTS ===
- In "projects_experience":
  * Always include the full "duration" as written (e.g., "Jul 2021 – Present").
  * Use concise, technical bullet points (≤12 words) in "responsibilities", starting with action verbs.
  * Extract all real, clearly separate projects or job positions.
  * Do not artificially split one job or role into multiple entries.
  * If multiple responsibilities belong to the same employer and time period, keep them as one project.

  === SKILLS ===
- For "hard_skills" and "skills_overview":
  * Use ONLY these fixed categories:
    cloud_platforms, devops_iac, monitoring_security, programming_languages,
    containers_orchestration, ci_cd_tools, ai_ml_tools, databases,
    backend, frontend, security, data_engineering, etl_tools, bi_tools,
    analytics, infrastructure_os, other_tools

  * Do NOT merge or invent new categories like "BI / Analytics" — always split correctly.
  * Each tool must be placed in only ONE most relevant category.
  * Tools like "Git", "Excel", "Outlook", "Power Platform" — only use "other_tools" if nothing else fits.
  * Avoid mixing tools in one item (e.g., don't write "Python / SQL" — create separate entries).

- For "skills_overview":
  * Include all tools used in projects or summary.
  * Estimate approximate "years_of_experience" logically (e.g., from project durations or global statements like "5+ years with Azure").
  * Output must include ≥10 distinct categories.
  * Each row must follow this format: {{ "category": "", "tools": [], "years_of_experience": "" }}
  * Always extract actual tools listed under each category in the CV, even if they appear in the same line as the category or year.
  * Do not leave "tools" empty — extract at least one tool per category if mentioned anywhere in the CV.

=== PROFILE SUMMARY ===
- Write a technical, third-person summary (80–100 words) describing actual domains, tools, and strengths.
- Align this summary strictly with real CV content — don't invent.

=== LANGUAGES ===
- Extract only explicitly mentioned languages and their levels (e.g., "German: native", "English: C1").
- Recognize section titles such as "Languages", "Language Skills", "Sprachen", or "Sprachkenntnisse".
- Do NOT infer any languages that are not explicitly written in the CV.
- Detect levels written as “native”, “fluent”, “C2”, “B1”, etc.
- If no languages are mentioned, return an empty list: []
- Output format:
  "languages": [
      {{"language": "German", "level": "C2"}},
      {{"language": "English", "level": "C1"}}
  ]

=== DATE FORMATTING ===
- Convert formats like:
  * "07.21 –" → "Jul 2021 – Present"
  * "07.21 – 12.23" → "Jul 2021 – Dec 2023"
  * "2020" → "Jan 2020 – Dec 2020"
  * German words like "Jetzt", "Heute", "Derzeit" → "Present"

=== OUTPUT RULES ===
- Return a single valid JSON object strictly matching the SCHEMA.
- Do NOT return markdown, explanations, comments, or prose — only JSON.
- Do NOT hallucinate tools, projects, dates, or titles.

SCHEMA:
{{
  "full_name": "",
  "title": "",
  "education": "",
  "languages": [{{"language": "", "level": ""}}],
  "domains": [],
  "profile_summary": "",
  "hard_skills": {{
    "programming_languages": [],
    "backend": [],
    "frontend": [],
    "databases": [],
    "data_engineering": [],
    "etl_tools": [],
    "bi_tools": [],
    "analytics": [],
    "cloud_platforms": [],
    "devops_iac": [],
    "ci_cd_tools": [],
    "containers_orchestration": [],
    "monitoring_security": [],
    "security": [],
    "ai_ml_tools": [],
    "infrastructure_os": [],
    "other_tools": []
  }},
  "projects_experience": [
    {{
      "project_title": "",
      "overview": "",
      "role": "",
      "duration": "",
      "responsibilities": [],
      "tech_stack": []
    }}
  ],
  "skills_overview": [
    {{
      "category": "",
      "tools": [],
      "years_of_experience": ""
    }}
  ],
  "website": ""
}}

TEXT:
{text}
"""

    if mode == "details" and base_structure:
        prompt += f"\n\nBASE STRUCTURE:\n{json.dumps(base_structure, ensure_ascii=False, indent=2)}"

    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",  
            messages=[
                {"role": "system", "content": "You are an expert CV parser."},
                {"role": "user", "content": prompt},
            ],
        )
        raw = response.choices[0].message.content
        return {
            "raw_response": raw,
            "mode": mode,
            "prompt": prompt
        }

    except Exception as e:
        print(f"❌ GPT error: {e}")
        return {"raw_response": "", "error": str(e)}

# ============================================================
# 📆 Исправление открытых диапазонов дат
# ============================================================
def fix_open_date_ranges(text_or_json):
    if isinstance(text_or_json, dict):
        for key, value in text_or_json.items():
            if isinstance(value, dict):
                fix_open_date_ranges(value)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        fix_open_date_ranges(item)
                    elif isinstance(item, str):
                        text_or_json[key][i] = fix_open_date_ranges(item)
            elif key.lower() == "duration" and isinstance(value, str):
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
    return text

# ============================================================
# 🔄 Обёртки для вызовов
# ============================================================
def extract_structure_with_gpt(text: str) -> dict:
    return ask_chatgpt(text, mode="structure")

def extract_details_with_gpt(text: str, structure: dict) -> dict:
    return ask_chatgpt(text, mode="details", base_structure=structure)

def auto_fix_missing_fields(data: dict) -> dict:
    return ask_chatgpt(data, mode="fix")

# ============================================================
# 🧪 Локальный запуск
# ============================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    input_path = "debug/full_prepared_text.txt"
    output_path = "debug/filled_cv_from_gpt.json"

    if not os.path.exists(input_path):
        logging.warning(f"⚠️ File not found: {input_path}")
        exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        input_text = f.read()

    logging.info("📨 Sending text to GPT (mode='details')...")
    result = ask_chatgpt(input_text, mode="details")

    if "raw_response" in result:
        try:
            filled_json = json.loads(result["raw_response"])

            # ⬇️ Постпроцессинг
            from postprocess import postprocess_filled_cv
            with open("debug/full_prepared_text.txt", "r", encoding="utf-8") as f:
                raw_text = f.read()
            filled_json = postprocess_filled_cv(filled_json, raw_text)

            # ⬇️ Сохранение
            with open(output_path, "w", encoding="utf-8") as out_f:
                json.dump(filled_json, out_f, indent=2, ensure_ascii=False)

            logging.info(f"✅ Результат сохранён: {output_path}")


        except json.JSONDecodeError as e:
            logging.error("❌ JSON parsing error:")
            logging.error(e)
            logging.warning("⚠️ GPT response:")
            print(result["raw_response"])
    else:
        logging.error("❌ GPT did not return a valid response.")
