import os
import yaml
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

from .models import Config, OrganizationMode, CategoriesMode

# Load .env
load_dotenv()

class Settings:
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    CONCURRENCY: int = int(os.getenv("COWORKER_CONCURRENCY", "5"))
    MODEL_NAME: str = os.getenv("COWORKER_MODEL", "gemini-2.0-flash")
    
    # User Config (defaults)
    config: Config = Config()

    def load_user_config(self, config_path: Path):
        """Load configuration from .coworker/config.yml"""
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    data = yaml.safe_load(f)
                    if data:
                        # Map string enums back if needed, pydantic handles it usually
                        self.config = Config(**data)
            except Exception as e:
                print(f"Warning: Failed to load config: {e}")

settings = Settings()
