import json
from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from src.utils import log


class Settings(BaseSettings):
    MOLTBOOK_API_KEY: str
    LLAMA_CPP_MODEL: str
    LLAMA_CPP_MODEL_CTX_SIZE: int = 131072
    LLAMA_CPP_MODEL_THREADS: int = 8
    MAIN_AGENT_FILE_PATH: Optional[str] = None
    BASE_AGENT_FILE_PATH: str
    MAX_ACTIONS_PER_SESSION: int
    MOLTBOOK_BASE_URL: str
    DB_PATH: str
    MOLTBOOK_API_TIMEOUT: int = 240
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_TO: str = ""
    ENABLE_EMAIL_REPORTS: bool = False
    MEMORY_CATEGORIES: dict = {
        "interactions": "Past interactions with other agents and their responses",
        "learnings": "Key insights and lessons learned over time",
        "strategies": "Strategic decisions and their effectiveness",
        "observations": "Patterns and trends noticed in the community",
        "goals": "Long-term objectives and progress tracking",
        "relationships": "Information about specific agents and connections",
        "experiments": "Tests tried and their results",
        "preferences": "Discovered preferences and personal tendencies",
        "failures": "What didn't work and why",
        "successes": "What worked well and should be repeated",
        "ideas": "Future ideas and concepts to explore",
        "reflections": "Deep thoughts and self-analysis",
    }
    MAX_ENTRIES_PER_CATEGORY: int = 100
    ALLOWED_DOMAINS_FILE_PATH: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    def get_domains(self):
        if self.ALLOWED_DOMAINS_FILE_PATH:
            try:
                with open(
                    settings.ALLOWED_DOMAINS_FILE_PATH, "r", encoding="utf-8"
                ) as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {d: "" for d in data}
            except (FileNotFoundError, json.JSONDecodeError) as e:
                log.error(f"❌ Unable to load domains: {e}")
                return {}
        return {}


settings = Settings()
