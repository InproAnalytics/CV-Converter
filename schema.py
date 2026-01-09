from copy import deepcopy

# ============================================================
# 1️⃣ Базовый шаблон схемы CV
# ============================================================
CV_SCHEMA_TEMPLATE = {
    "full_name": "",
    "title": "",
    "education": "",
    "languages": [],
    "domains": [],
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
        "other_tools": [],
    },
    "projects_experience": [],
    "skills_overview": [],
    "website": "",
}


# ============================================================
# 2️⃣ Основная функция валидации схемы
# ============================================================
def validate_schema(data: dict) -> dict:
    """
    Проверяет соответствие JSON базовой схеме.
    Автоматически добавляет недостающие поля.
    Не изменяет существующие данные.
    """
    if not isinstance(data, dict):
        return deepcopy(CV_SCHEMA_TEMPLATE)

    validated = deepcopy(CV_SCHEMA_TEMPLATE)

    for key, default_value in CV_SCHEMA_TEMPLATE.items():
        if key not in data:
            validated[key] = default_value
        else:
            value = data[key]
            if isinstance(default_value, dict) and isinstance(value, dict):
                # Глубокая проверка вложенных dict
                nested = deepcopy(default_value)
                nested.update(value)
                validated[key] = nested
            else:
                validated[key] = value

    # Добавляем любые дополнительные ключи, которых нет в шаблоне
    for extra_key, extra_val in data.items():
        if extra_key not in validated:
            validated[extra_key] = extra_val

    return validated


# ============================================================
# 🔍 Локальный тест
# ============================================================
if __name__ == "__main__":
    import json

    example = {
        "full_name": "Manuel Wolfsgruber",
        "hard_skills": {"cloud_platforms": [{"name": "AWS"}]},
        "languages": [{"language": "English", "level": "Fluent"}],
    }

    result = validate_schema(example)
    print(json.dumps(result, indent=2, ensure_ascii=False))
