import json
from typing import Optional, List, Dict, Set
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum


class AvailableModule(str, Enum):
    home = "HOME"
    email = "EMAIL"
    blog = "BLOG"
    social = "SOCIAL"
    research = "RESEARCH"
    memory = "MEMORY"
    shop = "SHOP"


class MemoryCategory(str, Enum):
    interactions = "interactions"
    learnings = "learnings"
    strategies = "strategies"
    observations = "observations"
    goals = "goals"
    relationships = "relationships"
    experiments = "experiments"
    preferences = "preferences"
    failures = "failures"
    successes = "successes"
    ideas = "ideas"
    reflections = "reflections"
    research_notes = "research_notes"

    @property
    def description(self) -> str:
        return _MEMORY_CATEGORY_DESCRIPTIONS[self]


_MEMORY_CATEGORY_DESCRIPTIONS: dict[MemoryCategory, str] = {
    MemoryCategory.interactions: "Past interactions with other agents and their responses",
    MemoryCategory.learnings: "Key insights and lessons learned over time",
    MemoryCategory.strategies: "Strategic decisions and their effectiveness",
    MemoryCategory.observations: "Patterns and trends noticed in the community",
    MemoryCategory.goals: "Long-term objectives and progress tracking",
    MemoryCategory.relationships: "Information about specific agents and connections",
    MemoryCategory.experiments: "Tests tried and their results",
    MemoryCategory.preferences: "Discovered preferences and personal tendencies",
    MemoryCategory.failures: "What didn't work and why",
    MemoryCategory.successes: "What worked well and should be repeated",
    MemoryCategory.ideas: "Future ideas and concepts to explore",
    MemoryCategory.reflections: "Deep thoughts and self-analysis",
    MemoryCategory.research_notes: "Deep research findings and synthesized data (Internal)",
}


class Settings(BaseSettings):
    ENVIRONMENT: str
    MOLTBOOK_API_KEY: str
    LLAMA_CPP_MODEL: str
    LLAMA_CPP_MODEL_CTX_SIZE: int
    CONTEXT_SAFETY_MARGIN: int
    ENABLE_SMART_COMPRESSION: bool
    LLAMA_CPP_MODEL_THREADS: int = 8
    MAIN_AGENT_FILE_PATH: Optional[str] = None
    BASE_AGENT_FILE_PATH: str
    MAX_ACTIONS_PER_SESSION: int
    MOLTBOOK_BASE_URL: str
    MOCK_MOLTBOOK_BASE_URL: str
    IS_TEST_MOLTBOOK_MODE: bool

    DB_PATH: str
    MOLTBOOK_API_TIMEOUT: int = 240
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_TO: str = ""
    ENABLE_EMAIL_REPORTS: bool = False
    MEMORY_CATEGORIES: Dict[str, str] = {
        category.value: category.description for category in MemoryCategory
    }
    MAX_ENTRIES_PER_CATEGORY: int = 100
    BLOG_API_URL: Optional[str] = None
    BLOG_API_KEY: Optional[str] = None
    FAL_API_KEY: Optional[str] = None
    BLOG_BASE_URL: Optional[str] = None
    USE_SUPERVISOR: bool

    USE_OLLAMA: bool
    OLLAMA_MODEL: str
    USE_OLLAMA_PROXY: bool
    OLLAMA_PROXY_URL: Optional[str] = None
    OLLAMA_PROXY_API_KEY: Optional[str] = None
    NUM_CTX_OLLAMA: Optional[int] = None
    EMAIL_MOLTBOOK_AGENT_OWNER: Optional[str] = None

    AGENT_IMAP_SERVER: Optional[str] = None
    AGENT_MAIL_BOX_EMAIL: Optional[str] = None
    AGENT_MAIL_BOX_PASSWORD: Optional[str] = None
    AGENT_IMAP_SMTP_HOST: Optional[str] = None
    USE_AGENT_MAILBOX: bool

    AGENT_NAME: str
    AGENT_DESCRIPTION: str

    USE_STABLE_DIFFUSION_LOCAL: bool
    USE_SD_PROXY: bool

    AVAILABLE_MODULES: List[str] = [module.value for module in AvailableModule]

    MODULE_TO_DOMAIN: Dict[AvailableModule, str] = {
        AvailableModule.home: "home",
        AvailableModule.email: "email",
        AvailableModule.blog: "blog",
        AvailableModule.social: "social",
        AvailableModule.research: "research",
        AvailableModule.memory: "memory",
        AvailableModule.shop: "shop",
    }

    ACTION_TO_DOMAIN: Dict[str, str] = {
        "email_read": "mail",
        "email_send": "mail",
        "email_delete": "mail",
        "email_archive": "mail",
        "email_mark_read": "mail",
        "email_get_messages": "mail",
        "write_blog_article": "blog",
        "share_created_blog_post_url": "blog",
        "review_pending_comments": "blog",
        "approve_comment": "blog",
        "approve_comment_key": "blog",
        "reject_comment_key": "blog",
        "refresh_feed": "social",
        "create_post": "social",
        "select_post_to_comment": "social",
        "publish_public_comment": "social",
        "vote_post": "social",
        "follow_agent": "social",
        "comment_post": "social",
        "reply_to_comment": "social",
        "read_post": "social",
        "share_link": "social",
        "downvote_post": "social",
        "unfollow_agent": "social",
        "wiki_search": "research",
        "wiki_read": "research",
        "research_complete": "research",
        "memory_store": "memory",
        "memory_retrieve": "memory",
        "buy_tool": "shop",
        "buy_artifact": "shop",
        "visit_shop": "shop",
        "update_master_plan": "strategy",
        "plan_initialize": "home",
        "plan_update": "home",
        "refresh_home": "home",
    }

    STICKY_ACTIONS: Set[str] = {
        "pin_to_workspace",
        "unpin_from_workspace",
        "memory_store",
        "memory_retrieve",
        "refresh_home",
    }

    USE_TOOLS_MODE: bool

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
