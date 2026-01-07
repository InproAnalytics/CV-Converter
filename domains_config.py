import json
import os


def _load_domains_config() -> list[str]:
    config_file = "domains.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return sorted(set(d.strip().title() for d in data.get("domains", []) if str(d).strip()))
        except Exception as e:
            print(f"Error loading domains: {e}")
    return []


def _save_domains_config(domains: list) -> bool:
    config_file = "domains.json"
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump({"domains": sorted(set(domains))}, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving domains: {e}")
        return False
