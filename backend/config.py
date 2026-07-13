"""
config.py — Central configuration for the Workspace AI Assistant.

WHY:  A single source of truth for all settings. Uses Pydantic Settings
      so values can be overridden via environment variables or .env file
      without touching code.

WHERE: Imported by every other backend module that needs a config value.

HOW:  `from backend.config import settings`  then use `settings.SCOPES`, etc.
      Backward-compatible aliases `CREDENTIALS_FILE` and `SCOPES` are
      exported at module level so existing imports keep working.
"""

import os
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application-wide settings loaded from environment / .env."""

    # ── Paths ──────────────────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    CREDENTIALS_FILE: Path = Path(__file__).resolve().parent.parent / "credentials" / "credentials.json"
    DOWNLOAD_FOLDER: str = "downloads"

    # ── Google OAuth ───────────────────────────────────────────────────
    REDIRECT_URI: str = "http://localhost:8000/auth/callback"
    FRONTEND_URL: str = "http://localhost:5173"

    SCOPES: List[str] = [
        # Drive
        "https://www.googleapis.com/auth/drive.readonly",
        # Gmail
        "https://www.googleapis.com/auth/gmail.readonly",
        # Calendar
        "https://www.googleapis.com/auth/calendar.readonly",
        # Docs
        "https://www.googleapis.com/auth/documents.readonly",
        # Sheets
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        # Slides
        "https://www.googleapis.com/auth/presentations.readonly",
        # User profile
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ]

    # ── Gemini ─────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

    # ── Limits ─────────────────────────────────────────────────────────
    MAX_DOCUMENT_CHARS: int = 50_000
    MAX_SEARCH_RESULTS: int = 20

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }



# ── Singleton ──────────────────────────────────────────────────────────
settings = Settings()

# ── Backward-compatible aliases ────────────────────────────────────────
CREDENTIALS_FILE = settings.CREDENTIALS_FILE
SCOPES = settings.SCOPES