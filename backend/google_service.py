"""
google_service.py — Google API client factory.

WHY:  Centralises the creation of every Google API client so no other module
      needs to know API versions or import `build` directly.

WHERE: Called by service modules (drive_service, gmail_service, …) and by
       auth.py when fetching user profile info.

HOW:  `from backend.google_service import get_drive, get_user_info`
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# ── Service name → (API name, version) mapping ────────────────────────
_SERVICES = {
    "drive":    ("drive",         "v3"),
    "gmail":    ("gmail",         "v1"),
    "calendar": ("calendar",      "v3"),
    "docs":     ("docs",          "v1"),
    "sheets":   ("sheets",        "v4"),
    "slides":   ("slides",        "v1"),
    "people":   ("people",        "v1"),
    "oauth2":   ("oauth2",        "v2"),
}


def get_service(service_name: str, credentials: Any):
    """
    Generic factory — build any Google API client by logical name.

    >>> svc = get_service("drive", creds)
    """
    if service_name not in _SERVICES:
        raise ValueError(f"Unknown service: {service_name!r}. "
                         f"Choose from {list(_SERVICES)}")
    api, version = _SERVICES[service_name]
    return build(api, version, credentials=credentials)


# ── Convenience helpers (backward-compatible) ─────────────────────────

def get_drive(credentials):
    return get_service("drive", credentials)


def get_gmail(credentials):
    return get_service("gmail", credentials)


def get_calendar(credentials):
    return get_service("calendar", credentials)


def get_docs(credentials):
    return get_service("docs", credentials)


def get_sheets(credentials):
    return get_service("sheets", credentials)


def get_slides(credentials):
    return get_service("slides", credentials)


# ── User Profile ──────────────────────────────────────────────────────

def get_user_info(credentials) -> Dict[str, str]:
    """
    Fetch the authenticated user's Google profile.

    Returns:
        {"name": "...", "email": "...", "picture": "..."}
    """
    service = get_service("oauth2", credentials)
    info = service.userinfo().get().execute()
    return {
        "name": info.get("name", ""),
        "email": info.get("email", ""),
        "picture": info.get("picture", ""),
    }