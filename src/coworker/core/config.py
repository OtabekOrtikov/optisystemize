import os
import yaml
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

from .models import Config, OrganizationMode, CategoriesMode
from pydantic import BaseModel 

load_dotenv()

class Config(BaseModel):
    lang: Optional[str] = None # ru or en
    organization_mode: OrganizationMode = OrganizationMode.BOTH
    categories_mode: CategoriesMode = CategoriesMode.AUTO
    max_categories: int = 12
    custom_categories: List[str] = []

class Settings:
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    CONCURRENCY: int = int(os.getenv("COWORKER_CONCURRENCY", "3"))
    MODEL_NAME: str = os.getenv("COWORKER_MODEL", "gemini-2.0-flash")
    
    config: Config = Config()
    
    _cli_lang_set: bool = False 

    def __init__(self):
        self._init_i18n()

    def _init_i18n(self):
        env_lang = os.getenv("COWORKER_LANG")
        
        if not env_lang:
            import locale
            try:
                loc = locale.getdefaultlocale()[0]
                if loc and loc.lower().startswith('ru'):
                    env_lang = 'ru'
            except: pass
            
        from .i18n import get_i18n
        self.i18n = get_i18n()
        if env_lang:
            self.i18n.set_language(env_lang)
        else:
            self.i18n.set_language("ru") 

    def set_cli_language(self, lang: str):
        """Called by CLI callback to enforce language."""
        if lang:
            self.i18n.set_language(lang)
            self._cli_lang_set = True

    def load_user_config(self, config_path: Path):
        """Load configuration from .coworker/config.yml"""
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    data = yaml.safe_load(f)
                    if data:
                        self.config = Config(**data)
                        if self.config.lang and not self._cli_lang_set:
                             self.i18n.set_language(self.config.lang)
                             
            except Exception as e:
                print(f"Warning: Failed to load config: {e}")

settings = Settings()
