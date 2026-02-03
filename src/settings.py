from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MOLTBOOK_API_KEY: str
    LLAMA_CPP_MODEL: str
    MAIN_AGENT_FILE_PATH: Optional[str] = None
    BASE_AGENT_FILE_PATH: str
    MAX_ACTIONS_PER_SESSION: int
    MOLTBOOK_BASE_URL: str
    DB_PATH: str

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_TO: str = ""
    ENABLE_EMAIL_REPORTS: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
