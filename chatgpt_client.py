import os
import json
import ast
import logging
from dotenv import load_dotenv
from openai import OpenAI
from postprocess import safe_parse_if_str

# ============================================================
# 🔧 Initialisierung
# ============================================================
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
logging.basicConfig(level=logging.INFO)

# ============================================================
# 🧠 Hauptfunktion zum Aufruf von GPT
# ============================================================
def ask_chatgpt(text, mode="details", base_structure=None, model="gpt-5-mini"):
    """
    Universal function to call GPT for CV parsing.

    Modes:
    - structure: returns only the JSON skeleton (keys with empty values)
    - details: extracts all fields from the text
    - fix: fills missing/empty fields while keeping the schema intact
    """
    if mode == "structure":
        task_description = "Extract only the structural JSON skeleton of the CV with all field names but empty values."
    elif mode == "fix":
        task_description = "Repair missing or empty fields logically, keeping the schema intact."
    else:
        task_description = "Extract structured CV data from text and return strictly formatted JSON only."

    import json
    schema = {
        "full_name": "",
        "title": "",
        "education": [
            {"degree": "", "institution": "", "year": ""}
        ],
        "languages": [{"language": "", "level": ""}],
        "profile_summary": "",
        "hard_skills": {
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
        },
        "projects_experience": [],
        "skills_overview": [],
        "website": ""
    }
    prompt = f"""
TASK: {task_description}

INSTRUCTIONS:

- Extract a complete, structured JSON strictly following the provided SCHEMA:
{json.dumps(schema, ensure_ascii=False, indent=2)}

...existing code...
  * Tools like "Git", "Excel", "Outlook", "Power Platform" — only use "other_tools" if nothing else fits.
  * Avoid mixing tools in one item (e.g., don't write "Python / SQL" — create separate entries).

- For "skills_overview":
  * Include all tools used in projects or summary.
  * Estimate approximate "years_of_experience" logically (e.g., from project durations or global statements like "5+ years with Azure").
  * Include ALL categories that can be supported by CV content (no minimum count).
  * Each row must follow this format: {{ "category": "", "tools": [], "years_of_experience": "" }}
  * Do not leave "tools" empty — extract at least one tool per category if mentioned anywhere in the CV.

=== PROFILE SUMMARY ===
- Write a technical, third-person summary (80–100 words) describing technical specialization (e.g., Cloud Engineer, Data Engineer, DevOps Specialist), key tools, and strengths.
- Do NOT mention business domains/industries (Banking, Healthcare, etc.) in this summary — those belong in the "domains" field.
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

=== DOMAINS ===
- Determine the candidate’s professional domains based strictly on the business industries of the companies they worked for.
- Use ONLY employer/client industries that are clearly stated or unambiguously inferable from company names or company sector descriptions (e.g., "bank", "insurance", "telecom provider", "university", "hospital").
- Do NOT treat areas of work (e.g., AI, Marketing, Sales) as industries unless explicitly stated as the employer’s business sector.
- Domains must describe WHAT the company does as a business (industry / market sector).
- EXCLUDE any term that describes:
  • a technology or methodology,
  • a business function or activity,
  • a role, job title, or responsibility.
- If the candidate worked in multiple industries, list all relevant domains as a JSON array of strings.

=== OUTPUT RULES ===
- Return a single valid JSON object strictly matching the SCHEMA.
- Do NOT return markdown, explanations, comments, or prose — only JSON.
- Do NOT hallucinate tools, projects, dates, or titles.
- Do NOT change field names or structure.
- Dates must be copied exactly as in the source (no reformatting, no translation). If unclear or not present, leave empty.
- Before returning the final JSON, internally verify:
  * Responsibilities per project contain 3–5 bullet points.
  * Each bullet is 26–30 words (target exactly 28; count ALL words).
  * Each bullet focuses on MECHANISM (how the work was done), not just results.
  * NO forbidden words: comprehensive, robust, effectively, successfully, seamlessly, efficiently, ensuring, enabling, leading to, resulting in.
  * Do not expand acronyms unnecessarily.
  * If any bullet is <26 words, add more detail about the mechanism or technical approach.
  * If any bullet is >30 words, remove redundant words.
  * No arrays or objects are serialized as strings.
  * All fields strictly match the provided SCHEMA.
- If any rule is violated, regenerate the output until all constraints are satisfied.


SCHEMA:
{{
  "full_name": "",
  "title": "",
  "education": [{
    {
      "degree": "",
      "institution": "",
      "year": ""
    }}]
  ],
  "languages": [{{"language": "", "level": ""}}],
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
      "company": "",
      "overview": "",
      "role": "",
      "duration": "",
      "responsibilities": [],
      "tech_stack": [],
      "domains": []
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
# IMPORTANT: The education field is a list of all education entries. For each entry, provide
# degree, institution, and year (graduation year or study period). If information is missing,
# leave the value empty, but keep the structure.

TEXT:
{text}
"""

  # --- Build messages
    messages = [
        {"role": "system", "content": "You are an expert CV parser. CRITICAL: When writing responsibilities, describe the MECHANISM (how/method), NOT the result. Never use words like 'enabling', 'ensuring', 'improving', 'reducing' - describe what you DID and HOW."},
        {"role": "user", "content": prompt},
    ]

    if mode == "details" and base_structure:
        messages.append({
            "role": "user",
            "content": f"Use this structure strictly as your schema:\n{json.dumps(base_structure, ensure_ascii=False, indent=2)}"
        })

  # --- API call
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
      temperature=0.1,
    )
        raw = response.choices[0].message.content
        return {"raw_response": raw, "mode": mode, "prompt": prompt}

    except Exception as e:
        logging.error(f"❌ GPT error: {e}")
        return {"raw_response": "", "error": str(e)}
# ============================================================
#  
# ============================================================

def safe_json_parse(raw):
    """
    Safely converts a string or object into a Python dict/list.

    If a string contains JSON embedded inside a string (e.g. "[{...}]"),
    it attempts to unwrap it.
    """
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list):
        return raw
    if not isinstance(raw, str):
        return {}

    try:
        # 🧠 Try standard JSON
        return json.loads(raw)
    except json.JSONDecodeError:
        # 🧩 Sometimes GPT uses single quotes
        try:
            return json.loads(raw.replace("'", '"'))
        except Exception:
            pass
        # 🧩 Sometimes the string is a Python literal representation
        try:
            return ast.literal_eval(raw)
        except Exception as e:
            logging.warning(f"⚠️ safe_json_parse failed: {e}")
            return {}

# ============================================================

def _call_gpt_and_parse(prompt: str, model: str = "gpt-4o-mini") -> dict:
    """Single GPT call + safe JSON parsing (shared helper for JSON responses)."""
    try:
        messages = [
            {"role": "system", "content": "You are an expert CV parser."},
            {"role": "user", "content": prompt},
        ]
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,
        )
        raw = response.choices[0].message.content or ""
        parsed = safe_parse_if_str(raw)
        return {"success": True, "json": parsed, "raw_response": raw}
    except Exception as e:
        logging.error(f"❌ GPT step failed: {e}")
        return {"success": False, "json": {}, "raw_response": ""}


def gpt_extract_cv_without_projects(text: str, model: str = "gpt-4o-mini") -> dict:
    """Extracts all CV fields except projects_experience (keeps it as [])."""
    prompt = f"""
TASK: Extract a structured CV JSON from the text, but DO NOT extract any projects.

INSTRUCTIONS:

- Extract a complete, structured JSON strictly following the provided SCHEMA.

- Avoid assumptions — rely only on what's clearly stated or strongly implied in the resume.
- If a field is unknown or not present in the CV, use empty values: "" for strings, [] for lists, {{}} for objects. Do NOT guess.
- The ONLY exception: for "skills_overview.years_of_experience" you MUST infer an approximate integer value based on project durations and global statements (e.g., "5+ years").
- Do NOT wrap arrays or objects into strings. Always output proper JSON values.
- Always extract and include exact start and end dates for every project, job, or education entry.

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
  * Include ALL categories that can be supported by CV content (no minimum count).
  * Each row must follow this format: {{ "category": "", "tools": [], "years_of_experience": "" }}
  * "years_of_experience" MUST never be empty. If not explicitly stated, infer a conservative integer (e.g., 1, 2, 3, 5) from project durations or CV summary.
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

=== DOMAINS ===
- Determine the candidate's professional domains based STRICTLY on the business industries/sectors of the companies or clients they worked for.
- Domains MUST represent what the company/client DOES as a business (industry/market sector).
- Examples of CORRECT domains: Banking, Insurance, Healthcare, Manufacturing, Retail, E-Commerce, Telecommunications, Automotive, Energy, Government, Education, Consulting, Real Estate, Logistics, Media, Hospitality.
- FORBIDDEN as domains (these are technical specializations, NOT industries): Cloud, DevOps, Data Engineering, Machine Learning, AI, Business Intelligence, MLOps, Big Data, IoT, Cybersecurity.
- Look for company names, client names, or explicit industry mentions (e.g., "for a major bank", "automotive manufacturer", "telecom provider").
- If industry is unclear or not mentioned, leave domains as empty array [].
- If the candidate worked in multiple industries, list all relevant domains as a JSON array of strings.

=== OUTPUT RULES ===
- Return a single valid JSON object strictly matching the SCHEMA.
- Do NOT return markdown, explanations, comments, or prose — only JSON.
- Do NOT hallucinate tools, projects, dates, or titles.
- Do NOT change field names or structure.
- Dates must be copied exactly as in the source (no reformatting, no translation). If unclear or not present, leave empty.

SCHEMA:
{{
  "full_name": "",
  "title": "",
  "education": "",
  "languages": [{{"language": "", "level": ""}}],
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
  "projects_experience": [],
  "skills_overview": [{{
    "category": "",
    "tools": [],
    "years_of_experience": ""
  }}],
  "website": ""
}}

TEXT:
{text}
"""
    return _call_gpt_and_parse(prompt, model=model)


def gpt_extract_projects_text(text: str, model: str = "gpt-4o-mini") -> dict:
    """Returns one large projects-only text, separated by === PROJECT N === markers."""
    prompt = f"""
TASK: Extract ONLY project sections from the following CV text.

INSTRUCTIONS:
- A project is a block describing work for a client, product or role, with responsibilities and usually a duration.
- Read the entire CV and isolate each distinct project.
- For each project, output in the following format:

=== PROJECTS ===

In the "projects_experience" field:

• Extract any block that contains at least a `project_title:` — even if duration is missing.
  → These blocks are always valid. Extract them even if role, overview, or tech_stack are missing. Fill missing fields with empty values.
• For each project, try to identify:
  - Company/client name ONLY, without city/country (e.g., "Accenture", "Deutsche Bank", "BMW")
  - Business industry of the company (e.g., Manufacturing, Banking, Automotive)
  - Keep this information in the raw text for later structuring
• Preserve the full "duration" exactly as written (e.g., "Jul 2021 – Present"). Do not modify, translate, or guess.
• Extract only real, distinct projects. Use visual or semantic separation as an indicator (headings, date blocks, project keywords, client names, etc.).
• For "responsibilities": create clear, concise professional bullet points (3–5 bullets per project). Each bullet MUST be 26–30 words (target exactly 28); count every word; FOCUS ON MECHANISM (how/method), not result; express action + detailed mechanism/technical approach; NEVER use: comprehensive, robust, effectively, successfully, seamlessly, efficiently, ensuring, enabling, leading to, resulting in; do not expand acronyms; use precise verbs; describe specific methods and configurations. Example: "Configured Kubernetes clusters with Helm Charts using automated deployment pipelines, resource quotas, and pod disruption budgets to manage workload distribution across environments." (26 words — ADD 2 words for target 28)
• Do not split a single job into multiple projects unless:
  - It has distinct durations, OR
  - There is clear formatting separation.

• If multiple roles or tasks are grouped under the same company and duration, treat them as one project.
• Do not skip projects just because some fields are missing. If it's a valid block (with `Project:` + `title:` + `duration:`), extract it fully with empty fields where needed.
• All extracted projects must follow the schema strictly.

- NEVER wrap JSON arrays or objects in strings.
  * For example, do NOT return: "projects_experience": "[{...}]"
  * Instead, return a proper JSON list: "projects_experience": [{...}]
- Do NOT return lists as strings. Fields like "projects_experience", "skills_overview", and "languages" must be actual JSON arrays — not strings that look like lists.
- Always use double quotes for all keys and string values.
• Each distinct project must become a separate JSON object in the "projects_experience" list.
• Never merge or combine projects — even if company or technologies overlap.
• Use clear separators such as '=== PROJECT START ===' or 'Project:' to distinguish them.

CV_TEXT:
{text}
"""
    try:
        messages = [
            {"role": "system", "content": "You are an expert CV parser."},
            {"role": "user", "content": prompt},
        ]
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1
        )
        raw = response.choices[0].message.content or ""
        return {"success": True, "text": raw, "raw_response": raw}
    except Exception as e:
        logging.error(f"❌ GPT projects-text step failed: {e}")
        return {"success": False, "text": "", "raw_response": ""}


def gpt_structurize_projects_from_text(projects_text: str, model: str = "gpt-4o-mini") -> dict:
    """Converts === PROJECT N === text blocks into the target schema's projects_experience."""
    prompt = f"""
TASK: Convert the following PROJECTS text into structured JSON objects.

INPUT FORMAT:
- The text contains multiple project blocks, each starting with a delimiter line:

=== PROJECT 1 ===
<raw project text>

=== PROJECT 2 ===
<raw project text>
...

PROJECT_SCHEMA:
{{ 
  "project_title": "",
  "company": "",
  "overview": "",
  "role": "",
  "duration": "",
  "responsibilities": [],
  "tech_stack": [],
  "domains": []
}}

INSTRUCTIONS:
- For each input project, produce one object following PROJECT_SCHEMA.
- Extract company name ONLY, without city or country (e.g., "Accenture", "Access Bank PLC", "Siemens AG"). Remove location information. If not mentioned, leave empty "".
- Determine project domains (industries/business sectors) based STRICTLY on the client's/company's industry mentioned in the project.
- Domains MUST represent what the client/company DOES as a business (e.g., Banking, Manufacturing, Healthcare, E-Commerce, Telecommunications, Automotive, Government, Insurance, Retail).
- FORBIDDEN as domains: Cloud, DevOps, Data Engineering, Big Data, AI, Machine Learning, IoT, Business Intelligence (these are technical areas, NOT industries).
- Look for explicit mentions like "for a bank", "automotive client", "manufacturing industry", "telecom provider", "healthcare company".
- If the industry is not clearly stated in the project description, return an empty list [].
- If the original project text is not in English (e.g. German), TRANSLATE all textual fields
  (project_title, company, overview, role, responsibilities, tech_stack items) to natural English.
- Preserve the meaning and level of technical detail when translating.
- Normalize duration to English format "MMM YYYY – MMM YYYY" or "MMM YYYY – Present".
- Clean any OCR noise or stray characters (e.g., "Jan 2023 nJetzt -" → "Jan 2023 – Present").
- Extract:
  - project_title in English (short, descriptive)
  - company in English (company name ONLY without city/country, e.g., "Accenture" not "Accenture, Dublin Ireland")
  - overview in English (60-80 words: comprehensive context about the project, its business goal, and scope)
  - role in English (e.g., "Lead BI Developer", "Data Engineer")
  - duration exactly as written in the text
  - domains as array of business industries (e.g., ["Banking"], ["Healthcare", "Insurance"])
  - responsibilities: 3–5 bullets, 26–30 words each (target 28). Focus on HOW (method/tools), not results. Action verb + specific method + technical context. FORBIDDEN: comprehensive, robust, effectively, successfully, seamlessly, efficiently, ensuring, enabling, leading to, resulting in. Don't expand acronyms.
  - tech_stack as flat list of tools.
- If any field is missing in the text, leave it as an empty string or empty list.
- Return ONLY JSON of the form {{ "projects_experience": [PROJECT_SCHEMA, ...]}}.

PROJECTS_TEXT:
{projects_text}
"""
    return _call_gpt_and_parse(prompt, model=model)

def run_stage_based_parsing(text: str, model: str = "gpt-4o-mini") -> dict:
    """
    Stage-based pipeline:
    1. Extract general CV info without projects
    2. Extract raw text for relevant projects
    3. Structurize the extracted project text into JSON
    4. Merge into one final result JSON
    """

    try:
      # Step 1: extract general CV info (no projects)
        step1 = gpt_extract_cv_without_projects(text, model=model)
        if not step1.get("success"):
            return {"success": False, "error": "Step 1 failed: general CV info"}

      # Step 2: extract raw projects text
        step2 = gpt_extract_projects_text(text, model=model)
        if not step2.get("success"):
            return {"success": False, "error": "Step 2 failed: projects text"}

      # Step 3: convert projects text into structured JSON
        step3 = gpt_structurize_projects_from_text(step2["text"], model=model)
        if not step3.get("success"):
            return {"success": False, "error": "Step 3 failed: project structuring"}

      # Merge results
        result_json = step1["json"]
        result_json["projects_experience"] = step3["json"].get("projects_experience", [])

        return {
            "success": True,
            "json": result_json,
            "raw_projects_text": step2["text"]
        }

    except Exception as e:
        logging.error(f"❌ Stage-based parsing pipeline failed: {e}")
        return {"success": False, "error": str(e)}

from typing import Dict, Any
def gpt_generate_text_cv_summary(cv_data: Dict[str, Any], model: str = "gpt-4o-mini") -> dict:
    """
    Generates a concise CV summary including:
    - Relevant Experience (2–5 key projects, 170–180 words total, including project titles in headers)
    - Expertise bullets (3–5 items, 32 words total for all bullets combined)
    - Why Me section (~40 words)
    Output is plain text. No JSON. No explanations.
    """
  # 1) Serialize the dict for the prompt
    structured_data_str = json.dumps(cv_data, ensure_ascii=False, indent=2)
    prompt = f"""
TASK: Generate a plain-text CV summary from the structured resume data below.

OUTPUT STRUCTURE:

--- RELEVANT EXPERIENCE ---
• Include exactly 2–5 projects from 'projects_experience'. No more, no less.
• For each project, include the project title in the header (e.g., "Project: Project Name").
• Only use content from the structured 'projects_experience' field. Do not invent or summarize from other sections.
• Limit total section length to 170–180 words and 1200–1300 characters (including spaces).
• Each bullet must describe one project only: include title, duration, 1–2 key results (max 18 words each), and 2–3 main technologies.
• Do not merge multiple projects into one bullet.
• If several projects share the same date range (e.g., May 2020 – Aug 2025), group them under that date in parentheses. Then list each project as a separate bullet below. This avoids repeating the same date in each line.
• Prioritize the most relevant and unique projects. Avoid duplicates or similar entries. Focus on business value and diversity of experience (e.g., platforms, automation, observability, security).
• Ignore unimportant, redundant, or overlapping projects.

--- EXPERTISE ---
• Write 3–5 bullet points.
• The entire expertise section must be exactly 32 words in total.
• Keep each bullet point concise and focused on unique technical strengths (e.g., "6+ years with Terraform", "Strong CI/CD background in FinTech").
• Each point must start with a measurable or domain-relevant phrase, such as:
   - “6+ years with Python and SQL”
   - “Strong CI/CD delivery in FinTech”
   - “Hands-on MLOps with Azure DevOps and MLflow”
• Use this format consistently across all points.
• Avoid vague summaries — favor specific skills, years, or business domains.
• Each bullet must reflect a unique skillset or perspective, avoiding repetition across bullets.
- Do NOT insert empty lines or blank lines between bullets.

--- WHY ME ---
• Write one paragraph of 35–40 words (270–290 characters including spaces).
• Clearly highlight the candidate’s unique value for the target role.
• Avoid soft skills or general motivation. Focus on differentiators: technical strengths, domains, scale of delivery, impact.

RULES:
- Use only structured resume data (especially 'projects_experience').
- Do NOT invent content or hallucinate skills, tools, or project names.
- Do NOT copy from unstructured text sections.
- Output must be plain English with no markdown, no comments, no labels.
- Style: concise, professional, high-density, no fluff.
- Output format: only plain text. No comments, no code blocks.
- Language: English.

FORMATTING:
- Separate each bullet or paragraph with a single blank line.
- Return the section headers exactly as written: --- RELEVANT EXPERIENCE ---, --- EXPERTISE ---, --- WHY ME ---.
- Each project, expertise point, and the WHY ME paragraph must be clearly separated by a blank line for readability.
- Within the --- EXPERTISE --- section, list all bullet points as consecutive lines with NO blank lines between them.

STRUCTURED CV DATA:
{structured_data_str}
"""

    try:
        messages = [
            {
                "role": "system",
                "content": """
                You are a senior CV writer specialized in technical summaries. 
                Your ONLY task is to generate the summary following ALL formatting and content rules below.
                CRITICAL RULES: Use only structured data. Do not invent content. Do not use markdown.
                """
            },
            # Keep only the structure and variables in the prompt
            {"role": "user", "content": prompt}, 
        ]

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1
        )

        raw = response.choices[0].message.content.strip()

        return {
            "success": True,
            "output_text": raw
        }

    except Exception as e:
        logging.error(f"❌ GPT summary generation failed: {e}")
        return {
            "success": False,
            "output_text": "",
            "error": str(e)
        }
