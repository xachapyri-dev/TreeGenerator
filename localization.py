import os
import json
from app_paths import get_path

class LocalizationManager:
    def __init__(self):
        self.translations = {}
        self.current_lang = "ru"
        self.load_all()

    def load_all(self):
        trans_dir = get_path("translation")
        if not os.path.exists(trans_dir):
            os.makedirs(trans_dir, exist_ok=True)
            return

        for fname in os.listdir(trans_dir):
            if fname.endswith(".json"):
                lang_code = os.path.splitext(fname)[0]
                full_path = os.path.join(trans_dir, fname)
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        self.translations[lang_code] = json.load(f)
                except Exception as e:
                    print(f"Ошибка чтения {fname}: {e}")

    def get_available_languages(self):
        res = {}
        for code, data in self.translations.items():
            res[code] = data.get("name", code)
        return res

    def set_language(self, code: str):
        if code in self.translations:
            self.current_lang = code

    def tr(self, key: str, default: str = "") -> str:
        lang_data = self.translations.get(self.current_lang, {})
        return lang_data.get(key, default or key)