import os
import yaml
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

from .models import Config, OrganizationMode, CategoriesMode
from pydantic import BaseModel # Added this import for BaseModel

# Load .env
load_dotenv()

# The Config class definition is moved here from .models to allow direct modification as per instruction.
# This assumes the user intended to move/redefine Config here.
class Config(BaseModel):
    lang: Optional[str] = None # ru or en
    organization_mode: OrganizationMode = OrganizationMode.BOTH
    categories_mode: CategoriesMode = CategoriesMode.AUTO
    max_categories: int = 12
    custom_categories: List[str] = []

class Settings:
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    CONCURRENCY: int = int(os.getenv("COWORKER_CONCURRENCY", "5"))
    MODEL_NAME: str = os.getenv("COWORKER_MODEL", "gemini-2.0-flash")
    
    # User Config (defaults)
    config: Config = Config()
    
    _cli_lang_set: bool = False # Track if CLI Overrode lang

    def __init__(self):
        # Initialize with ENV or default RU
        self._init_i18n()

    def _init_i18n(self):
        # Priority: ENV -> Default RU (Config loaded later)
        env_lang = os.getenv("COWORKER_LANG")
        
        # System locale check as fallback before hard default?
        # User requested: ENV > System > RU
        if not env_lang:
            # Simple check
            import locale
            try:
                # getdefaultlocale returns (lang, encoding) e.g. ('en_US', 'UTF-8')
                loc = locale.getdefaultlocale()[0]
                if loc and loc.lower().startswith('ru'):
                    env_lang = 'ru'
                # Default is already strict RU if nothing mapped
            except: pass
            
        from .i18n import get_i18n
        self.i18n = get_i18n()
        # Set initial from ENV or default
        if env_lang:
            self.i18n.set_language(env_lang)
        else:
            self.i18n.set_language("ru") # Hard Default

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
                        # Map string enums back if needed, pydantic handles it usually
                        self.config = Config(**data)
                        
                        # Apply Config Lang if set (overrides default/system, but CLI overrides this later)
                        # Actually logic: CLI > Config > ENV.
                        # We set ENV in __init__. Now Config might overwrite it? 
                        # Wait, logic requested: CLI > Config > ENV.
                        # So if ENV is set, does Config override it?
                        # Usually CLI > Config > Env means Command Line is strongest.
                        # Config is user's persistent preference. Env is session/machine.
                        # Config > Env makes sense for persistent settings.
                        # BUT CLI > Config.
                        if self.config.lang and not self._cli_lang_set:
                             self.i18n.set_language(self.config.lang)
                             
            except Exception as e:
                print(f"Warning: Failed to load config: {e}")

settings = Settings()
