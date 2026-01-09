import os
import re
import json
import time
import logging

from pdf_processor import prepare_cv_text
from chatgpt_client import ask_chatgpt
from postprocess import (
    postprocess_filled_cv,
    clean_text_fields,
    validate_cv_schema,
)
from utils import save_json

# Пути к файлам
INPUT_PDF = "data_input/CV Manuel Wolfsgruber.pdf"
OUTPUT_JSON = "data_output/result_Manuel.json"


# ============================================================
# 🔹 Вспомогательные функции
# ============================================================
def filter_explicit_domains(text: str, domains: list[str]) -> list[str]:
    """Расширяет поиск доменов по ключевым словам и контексту."""
    domain_keywords = {
        "Machine Learning": ["machine learning", "ml", "deep learning", "neural network"],
        "AI": ["artificial intelligence", "ai model", "generative ai"],
        "Data Engineering": ["data pipeline", "data ingestion", "etl", "databricks", "snowflake"],
        "MLOps": ["mlops", "model deployment", "ci/cd for models", "vertex ai", "sagemaker"],
        "Cloud": ["aws", "azure", "gcp", "kubernetes", "terraform"],
        "Analytics": ["bi", "power bi", "analytics", "dashboards", "reporting"],
        "IoT": ["iot", "connected devices", "sensor data", "predictive maintenance"],
        "Finance": ["banking", "fintech", "risk model", "insurance"],
        "Healthcare": ["medical", "health", "pharma", "clinical"],
        "Manufacturing": ["factory", "industrial", "process optimization", "production"],
    }

    found = set()
    text_l = text.lower()
    for domain, keywords in domain_keywords.items():
        if any(k in text_l for k in keywords):
            found.add(domain)

    if domains:
        found.update(domains)

    return sorted(found)


def shorten_profile_summary(text: str, max_chars: int = 1200) -> str:
    """Обрезает слишком длинное описание профиля."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text.strip())
    if len(text) > max_chars:
        cut = text[:max_chars]
        if "." in cut:
            cut = cut[:cut.rfind(".") + 1]
        return cut.strip()
    return text.strip()


# ============================================================
# 🔹 Главный пайплайн
# ============================================================

def main():
    start_time = time.time()
    logging.basicConfig(level=logging.INFO)
    logging.info("🚀 Starting CV Extraction Pipeline...")

    # 1️⃣ Обработка PDF → подготовка текста
    prepared_text, raw_text = prepare_cv_text(INPUT_PDF)

    # 2️⃣ Вызов GPT
    logging.info("📨 Sending text to GPT (mode='details')...")
    result = ask_chatgpt(prepared_text, mode="details")

    # 3️⃣ Проверка и разбор ответа
    if "raw_response" in result:
        try:
            filled_json = json.loads(result["raw_response"])

            # 4️⃣ Основная постобработка
            logging.info("🧩 Running structured postprocessing...")
            filled_json = postprocess_filled_cv(filled_json, raw_text)

            # 5️⃣ Дополнительная очистка и проверка
            logging.info("🧼 Cleaning and validating result...")
            filled_json = clean_text_fields(filled_json)

            missing_fields = validate_cv_schema(filled_json)
            if missing_fields:
                logging.warning(f"⚠️ Missing fields: {missing_fields}")

            # 6️⃣ Доменная фильтрация и сокращение summary
            filled_json["domains"] = filter_explicit_domains(
                prepared_text, filled_json.get("domains", [])
            )
            filled_json["profile_summary"] = shorten_profile_summary(
                filled_json.get("profile_summary", "")
            )

            # 7️⃣ Добавление метаданных
            filled_json["_meta"] = {
                "source_pdf": INPUT_PDF,
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "processing_time_sec": round(time.time() - start_time, 2),
            }

            # 8️⃣ Сохранение результата
            save_json(OUTPUT_JSON, filled_json)
            logging.info(f"✅ Result saved to: {OUTPUT_JSON}")

        except json.JSONDecodeError as e:
            logging.error("❌ JSON parsing error:")
            logging.error(e)
            logging.warning("⚠️ GPT raw response:")
            print(result["raw_response"])

    else:
        logging.error("❌ GPT did not return a valid response.")

    elapsed = time.time() - start_time
    logging.info(f"✅ Pipeline completed in {elapsed:.2f} seconds")


# ============================================================
# 🔹 Точка входа
# ============================================================

if __name__ == "__main__":
    main()
