import os
import json
from app_paths import get_path

SETTINGS_FILE = get_path("settings.json")

DEFAULT_SETTINGS = {
    "first_run": True,
    "language": "ru"
}

def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_SETTINGS, **data}
        except Exception as e:
            print(f"Ошибка загрузки settings.json: {e}")
    return DEFAULT_SETTINGS.copy()

def save_settings(settings: dict):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Ошибка сохранения settings.json: {e}")