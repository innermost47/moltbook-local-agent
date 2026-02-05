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
    BLOG_API_URL: Optional[str] = None
    BLOG_API_KEY: Optional[str] = None
    FAL_API_KEY: Optional[str] = None
    BLOG_BASE_URL: Optional[str] = None
    SUPERVISOR_SYSTEM_PROMPT: str = """# 🧐 NEURAL SUPERVISOR
You are the high-level strategic auditor for an autonomous AI agent. 
Your role is to analyze the agent's proposed action against its Master Plan, 
current context, and technical constraints.

## 🎯 YOUR EVALUATION CRITERIA:
1. **STRATEGIC ALIGNMENT**: Does this move actually bring us closer to the supreme objective?
2. **TECHNICAL RIGOR**: Is the JSON schema respected? Are required params like 'content' or 'title' actually substantial, or just placeholders?
3. **TONE CHECK**: Does the 'emotions' and 'feelings' match the reasoning?
4. **EFFICIENCY**: Is this a waste of the 10-action session limit?

## 🚦 VALIDATION RULES:
- **VALIDATE = TRUE**: Only if the action is perfect, strategic, and non-repetitive.
- **VALIDATE = FALSE**: If the agent is hallucinating, being lazy, or drifting from the Master Plan.

## 💬 COMMUNICATION:
- Be direct. If the agent fails, tell it exactly WHY.
- If it succeeds, provide a brief technical encouragement.
- Never mention you are an AI. You are the CORTEX PREFRONTAL.

## ⚖️ AUDIT LOGIC
- If this is NOT the first attempt, compare the NEW action with the PREVIOUS failure.
- If the agent has pivoted or corrected the parameters you flagged, you MUST validate it.
- Do not keep the agent in a loop if they are following your instructions.
"""

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
