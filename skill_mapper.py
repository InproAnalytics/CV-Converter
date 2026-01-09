import re
from tech_mapping import TECH_MAPPING


def remap_hard_skills(hard_skills_from_gpt):
    """
    Улучшенная нормализация hard_skills:
    - Распределяет всё по TECH_MAPPING
    - Убирает пустые и дубли
    - Схлопывает облака (Azure, AWS, GCP)
    - Распознаёт “мусор” из other_tools и возвращает его в правильные категории
    """

    all_categories = sorted(set(TECH_MAPPING.values()))
    mapped_skills = {cat: [] for cat in all_categories}
    mapped_skills["other_tools"] = []

    if not isinstance(hard_skills_from_gpt, dict):
        return {}

    # --- Основное распределение по шаблонам
    for category, tools in hard_skills_from_gpt.items():
        if not isinstance(tools, list):
            continue

        for item in tools:
            name = item["name"].strip() if isinstance(item, dict) else str(item).strip()
            if not name:
                continue

            matched_category = None
            for pattern, mapped_category in TECH_MAPPING.items():
                if re.search(pattern, name):
                    matched_category = mapped_category
                    break

            target_cat = matched_category or "other_tools"
            mapped_skills[target_cat].append({"name": name})

    # --- 🧠 Умная перераспределение "мусора" из other_tools
    if mapped_skills.get("other_tools"):
        reassign = {
            "data_engineering": [
                "data lake", "data warehouse", "lakehouse", "delta lake",
                "unity catalog", "etl", "elt", "pipeline", "databricks",
                "dataflow", "integration", "data quality"
            ],
            "analytics": [
                "analytics", "analysis", "kpi", "dashboard", "report", "time series"
            ],
            "ai_ml_tools": [
                "mlflow", "deep learning", "neural network", "ml model"
            ],
            "devops_iac": [
                "infrastructure as code", "iac"
            ],
            "bi_tools": [
                "power platform", "metabase"
            ]
        }

        new_assignments = {k: [] for k in reassign.keys()}

        remaining_other = []
        for tool in mapped_skills["other_tools"]:
            n = tool["name"].lower()
            found = False
            for target, keywords in reassign.items():
                if any(kw in n for kw in keywords):
                    new_assignments[target].append(tool)
                    found = True
                    break
            if not found:
                remaining_other.append(tool)

        for cat, vals in new_assignments.items():
            if vals:
                mapped_skills[cat].extend(vals)
        mapped_skills["other_tools"] = remaining_other

    # --- ☁️ Схлопывание облаков
    def collapse_clouds(category, keywords, clean_name):
        items = mapped_skills.get(category, [])
        if any(any(k in t["name"].lower() for k in keywords) for t in items):
            mapped_skills[category] = [{"name": clean_name}]

    collapse_clouds("cloud_platforms", ["azure"], "Microsoft Azure")
    collapse_clouds("cloud_platforms", ["aws", "amazon web services"], "AWS")
    collapse_clouds("cloud_platforms", ["google cloud", "gcp"], "Google Cloud")

    # --- 🧹 Чистка и сортировка
    for cat, tools in mapped_skills.items():
        seen = set()
        unique = []
        for t in tools:
            key = t["name"].strip().lower()
            if key not in seen:
                seen.add(key)
                unique.append(t)
        mapped_skills[cat] = sorted(unique, key=lambda x: x["name"].lower())

    # --- Удаляем пустые
    cleaned = {k: v for k, v in mapped_skills.items() if v}

    return cleaned
