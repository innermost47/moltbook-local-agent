from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MOLTBOOK_API_KEY: str
    LLAMA_CPP_MODEL: str
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

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
