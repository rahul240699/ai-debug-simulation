"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


# ── LLM ──────────────────────────────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))

# ── Grid ─────────────────────────────────────────────────────────────────────
GRID_WIDTH: int = int(os.getenv("GRID_WIDTH", "8"))
GRID_HEIGHT: int = int(os.getenv("GRID_HEIGHT", "8"))
MAX_TURNS: int = int(os.getenv("MAX_TURNS", "100"))
WALL_DENSITY: float = float(os.getenv("WALL_DENSITY", "0.15"))
DM_STALE_TURNS: int = int(os.getenv("DM_STALE_TURNS", "2"))

# ── Langfuse ──────────────────────────────────────────────────────────────────
LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
LANGFUSE_ENABLED: bool = bool(LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY)

# ── App ──────────────────────────────────────────────────────────────────────
APP_ENV: str = os.getenv("APP_ENV", "development")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
