"""
session.py — In-memory session management.

WHY:  The old file was three bare globals (`credentials = None`, etc.).
      A class gives us type safety, methods, and a clear API surface.
      Still single-process / single-user for now — multi-user persistence
      (Redis / DB) can be plugged in later by swapping the storage backend.

WHERE: Imported by auth, routes, and agent modules that need to read or
       write session state.

HOW:  `from backend.session import session_manager`
      `session_manager.set_credentials(creds)`
      `session_manager.is_authenticated()`
"""

from __future__ import annotations

import logging
import os
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

SESSION_FILE = ".cache/session.json"

@dataclass
class UserInfo:
    """Minimal Google profile data."""
    name: str = ""
    email: str = ""
    picture: str = ""


@dataclass
class SessionManager:
    """
    Holds per-session state for the current user.

    Attributes:
        _credentials:         Google OAuth credentials object.
        user_info:            Logged-in user's profile.
        conversation_history: List of {role, content} dicts for the AI agent.
        current_context:      Arbitrary context the agent can read/write
                              (e.g. "user is looking at Resume.pdf").
        selected_file:        Currently selected file metadata.
    """

    _credentials: Any = None
    user_info: UserInfo = field(default_factory=UserInfo)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    current_context: Dict[str, Any] = field(default_factory=dict)
    
    # Context Tracking
    last_searched_items: List[Dict[str, Any]] = field(default_factory=list)
    last_opened_item: Optional[Dict[str, Any]] = None
    last_opened_email: Optional[Dict[str, Any]] = None
    last_calendar_event: Optional[Dict[str, Any]] = None
    last_doc: Optional[Dict[str, Any]] = None
    last_sheet: Optional[Dict[str, Any]] = None
    last_slide: Optional[Dict[str, Any]] = None
    oauth_state: str = ""
    oauth_code_verifier: str = ""

    def __post_init__(self):
        """Automatically called after dataclass initialization."""
        self._load_persisted_credentials()

    # ── Credentials ────────────────────────────────────────────────────

    def _load_persisted_credentials(self):
        """Restore credentials from disk if available."""
        if os.path.exists(SESSION_FILE):
            try:
                self._credentials = Credentials.from_authorized_user_file(SESSION_FILE)
                logger.info("[Session] Loaded persisted credentials")
            except Exception as e:
                logger.warning(f"[Session] Failed to load persisted credentials: {e}")
                self._credentials = None

    def set_credentials(self, creds: Any) -> None:
        """Store OAuth credentials in memory and write to disk."""
        self._credentials = creds
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
        
        # Write to disk
        try:
            with open(SESSION_FILE, "w") as f:
                f.write(creds.to_json())
            logger.info("[Session] Credentials persisted")
        except Exception as e:
            logger.error(f"[Session] Failed to persist credentials: {e}")

    def get_credentials(self) -> Any:
        """Return stored credentials or None."""
        return self._credentials

    def is_authenticated(self) -> bool:
        """True if we have valid credentials."""
        return self._credentials is not None

    # ── Conversation ───────────────────────────────────────────────────

    def add_message(self, role: str, content: str) -> None:
        """Append a message to conversation history."""
        self.conversation_history.append({"role": role, "content": content})

    def get_history(self, last_n: int = 10) -> List[Dict[str, str]]:
        """Return the most recent *last_n* messages."""
        return self.conversation_history[-last_n:]

    def clear_history(self) -> None:
        """Reset conversation history."""
        self.conversation_history.clear()

    # ── Context ────────────────────────────────────────────────────────

    def set_context(self, key: str, value: Any) -> None:
        self.current_context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        return self.current_context.get(key, default)

    # ── Full Reset ─────────────────────────────────────────────────────

    def clear(self) -> None:
        """Wipe all session state (logout)."""
        self._credentials = None
        self.user_info = UserInfo()
        self.conversation_history.clear()
        self.current_context.clear()
        
        # Also clear file persistence
        if os.path.exists(SESSION_FILE):
            try:
                os.remove(SESSION_FILE)
                logger.info("[Session] Session cleared (file removed)")
            except Exception as e:
                logger.warning(f"Could not remove session file: {e}")
        else:
            logger.info("[Session] Session cleared (in-memory)")


# ── Module-level singleton ─────────────────────────────────────────────
session_manager = SessionManager()

# ── Backward-compatible alias ──────────────────────────────────────────
credentials = None  # Updated by auth.py; prefer session_manager going forward.
document_text = ""
selected_file = ""