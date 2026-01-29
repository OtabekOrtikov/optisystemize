import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load .env from current directory or parent directories
load_dotenv()

class Settings:
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    CONCURRENCY: int = int(os.getenv("COWORKER_CONCURRENCY", "5"))
    MODEL_NAME: str = os.getenv("COWORKER_MODEL", "gemini-2.0-flash-exp")

settings = Settings()
