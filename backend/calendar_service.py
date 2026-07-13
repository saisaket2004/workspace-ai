"""
calendar_service.py — Google Calendar operations.

WHY:  Provides clean access to calendar events with proper timezone
      handling and human-readable time formatting.

WHERE: Called by calendar_routes.py and tools.py.

HOW:  `from backend.calendar_service import get_today_schedule`
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────

def _format_event(event: Dict) -> Dict[str, Any]:
    """Flatten a Calendar API event into a simple dict."""
    start = event.get("start", {})
    end = event.get("end", {})

    return {
        "id": event.get("id", ""),
        "summary": event.get("summary", "(No title)"),
        "description": event.get("description", ""),
        "location": event.get("location", ""),
        "start": start.get("dateTime") or start.get("date", ""),
        "end": end.get("dateTime") or end.get("date", ""),
        "status": event.get("status", ""),
        "htmlLink": event.get("htmlLink", ""),
        "organizer": event.get("organizer", {}).get("email", ""),
        "attendees": [
            a.get("email", "") for a in event.get("attendees", [])
        ],
    }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ── Public API ─────────────────────────────────────────────────────────

def get_upcoming_events(
    service,
    days: int = 7,
    max_results: int = 25,
) -> List[Dict[str, Any]]:
    """Return events in the next *days* days."""
    now = _utc_now()
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days)).isoformat()

    result = service.events().list(
        calendarId="primary",
        timeMin=time_min,
        timeMax=time_max,
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    return [_format_event(e) for e in result.get("items", [])]


def get_today_schedule(service) -> List[Dict[str, Any]]:
    """Return today's events only."""
    now = _utc_now()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    result = service.events().list(
        calendarId="primary",
        timeMin=start_of_day.isoformat(),
        timeMax=end_of_day.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    return [_format_event(e) for e in result.get("items", [])]


def get_weekly_schedule(service) -> List[Dict[str, Any]]:
    """Return this week's events (next 7 days)."""
    return get_upcoming_events(service, days=7)


def get_event_details(service, event_id: str) -> Dict[str, Any]:
    """Fetch a single event by ID."""
    event = service.events().get(
        calendarId="primary",
        eventId=event_id,
    ).execute()
    return _format_event(event)
