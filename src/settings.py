from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MOLTBOOK_API_KEY: str
    LLAMA_CPP_MODEL: str
    MAIN_AGENT_FILE_PATH: Optional[str] = None
    BASE_AGENT_FILE_PATH: str = "agents/BASE.md"
    MAX_ACTIONS_PER_SESSION: int
    MOLTBOOK_BASE_URL: str = "https://www.moltbook.com/api/v1"
    DB_PATH: str = "memory.db"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
