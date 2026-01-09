import json
import os
import tempfile
from typing import Any, Dict


# ============================================================
# 1️⃣ Safe JSON save
# ============================================================
def save_json(filepath: str, data: Dict[str, Any]):
    """
    Safely saves JSON to the given path.
    Uses an atomic write: first write to a temp file, then replace the original.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="tmp_json_", suffix=".json")

    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as tmp_file:
            json.dump(data, tmp_file, ensure_ascii=False, indent=2)
        os.replace(tmp_path, filepath)
    except Exception as e:
        raise RuntimeError(f"❌ Error saving JSON to {filepath}: {e}")
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


# ============================================================
# 2️⃣ Safe JSON load
# ============================================================
def load_json(filepath: str) -> Dict[str, Any]:
    """Loads JSON if it exists; otherwise returns an empty dict."""
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        raise ValueError(f"❌ Invalid JSON file: {filepath}")
    except Exception as e:
        raise RuntimeError(f"❌ Error loading JSON: {e}")


# ============================================================
# 3️⃣ Empty field check
# ============================================================
def has_empty_fields(data: Any) -> bool:
    """
    Recursively checks whether there are empty strings, lists, or dicts.
    Returns True if at least one empty field is found.
    """
    if data is None:
        return True

    if isinstance(data, str):
        return not data.strip()

    if isinstance(data, (list, tuple)):
        return any(has_empty_fields(v) for v in data)

    if isinstance(data, dict):
        return any(has_empty_fields(v) for v in data.values())

    return False


# ============================================================
# 4️⃣ Empty field count
# ============================================================
def count_empty_fields(data: Any) -> int:
    """
    Recursively counts the number of empty fields (strings, lists, dicts).
    """
    count = 0

    if data is None:
        return 1

    if isinstance(data, str):
        return 1 if not data.strip() else 0

    if isinstance(data, (list, tuple)):
        for v in data:
            count += count_empty_fields(v)
        return count

    if isinstance(data, dict):
        for v in data.values():
            count += count_empty_fields(v)
        return count

    return 0


# ============================================================
# 5️⃣ Debug utilities (optional)
# ============================================================
if __name__ == "__main__":
    test_data = {
        "name": "Manuel Wolfsgruber",
        "email": "",
        "languages": ["English", ""],
        "projects": [
            {"name": "Data Pipeline", "duration": "", "tools": ["Python", "Airflow"]},
            {},
        ],
    }

    print("Has empty fields:", has_empty_fields(test_data))
    print("Empty field count:", count_empty_fields(test_data))

    save_json("data_output/test.json", test_data)
    loaded = load_json("data_output/test.json")
    print("Loaded JSON keys:", list(loaded.keys()))

