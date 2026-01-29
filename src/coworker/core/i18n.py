import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


_i18n_instance = None

class I18n:
    def __init__(self):
        self.lang = "ru" 
        self.translations: Dict[str, Any] = {}
        self.loaded_langs: set = set()
        
        
        
        
        
        
        self.root_dir = Path(__file__).parent.parent / "i18n"
        
    def set_language(self, lang: str):
        if lang not in ["ru", "en"]:
            lang = "ru"
        self.lang = lang
        self._load_lang(lang)
        
    def _load_lang(self, lang: str):
        if lang in self.loaded_langs:
            return
            
        file_path = self.root_dir / f"{lang}.yml"
        if not file_path.exists():
            
            if lang != "ru":
                self._load_lang("ru")
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data:
                    self.translations[lang] = data
                    self.loaded_langs.add(lang)
        except Exception as e:
            print(f"Error loading translation for {lang}: {e}")

    def t(self, key: str, **kwargs) -> str:
        """Get translated string. Supports dots for nested keys e.g. 'cli.welcome'."""
        
        
        val = self._get_value(self.lang, key)
        
        
        if val is None and self.lang != "ru":
            val = self._get_value("ru", key)
            
        if val is None:
            return key 
            
        if isinstance(val, str):
            try:
                return val.format(**kwargs)
            except:
                return val
        return str(val)

    def _get_value(self, lang: str, key: str) -> Optional[Any]:
        if lang not in self.translations:
            self._load_lang(lang)
            
        data = self.translations.get(lang, {})
        keys = key.split(".")
        
        curr = data
        for k in keys:
            if isinstance(curr, dict):
                curr = curr.get(k)
            else:
                return None
        return curr

def get_i18n() -> I18n:
    global _i18n_instance
    if _i18n_instance is None:
        _i18n_instance = I18n()
    return _i18n_instance
    
def t(key: str, **kwargs) -> str:
    return get_i18n().t(key, **kwargs)
