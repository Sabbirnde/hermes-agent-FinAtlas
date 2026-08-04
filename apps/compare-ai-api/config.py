"""COMPARE AI — Application Configuration"""

from __future__ import annotations

import os
from typing import Optional


class Settings:
    APP_NAME: str = "COMPARE AI"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Database
    DATABASE_URL: str = os.getenv(
        "COMPARE_AI_DB_URL",
        "sqlite+aiosqlite:///./compare_ai.db"
    )

    # Redis
    REDIS_URL: Optional[str] = os.getenv("COMPARE_AI_REDIS_URL")

    # LLM Provider (via Hermes or direct)
    LLM_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    LLM_BASE_URL: Optional[str] = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    LLM_MODEL: str = os.getenv("COMPARE_AI_MODEL", "anthropic/claude-sonnet-4-5")

    # Web Search
    SERPER_API_KEY: Optional[str] = os.getenv("SERPER_API_KEY")
    FIRECRAWL_API_KEY: Optional[str] = os.getenv("FIRECRAWL_API_KEY")

    # CORS
    ALLOWED_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://compare.ai",
        "https://bd.compare.ai",
        "https://in.compare.ai",
    ]

    # Live countries (MVP: BD only)
    LIVE_COUNTRIES: list = ["BD"]

    # Cache TTL (seconds)
    RESEARCH_CACHE_TTL: int = int(os.getenv("RESEARCH_CACHE_TTL", "21600"))  # 6 hours
    FRESHNESS_THRESHOLD_DAYS: int = int(os.getenv("FRESHNESS_THRESHOLD_DAYS", "30"))

    # Research limits
    MAX_SOURCES_PER_PRODUCT: int = 5
    MAX_PRODUCTS_PER_RESEARCH: int = 20
    TOP_N_RESULTS: int = 5

    # Hermes home
    HERMES_HOME: str = os.getenv(
        "HERMES_HOME",
        os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "hermes")
    )


settings = Settings()
