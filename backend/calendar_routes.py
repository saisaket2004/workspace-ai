"""
calendar_routes.py — REST endpoints for Google Calendar.

WHERE: Mounted on /calendar prefix in app.py.

HOW:  GET /calendar/events      — upcoming events (default 7 days)
      GET /calendar/today       — today's schedule
      GET /calendar/week        — this week's schedule
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from backend.session import session_manager
from backend.google_service import get_calendar
from backend import calendar_service

router = APIRouter(prefix="/calendar", tags=["Calendar"])


def _require_auth():
    if not session_manager.is_authenticated():
        return None, JSONResponse(
            status_code=401,
            content={"error": "Please login first."},
        )
    return session_manager.get_credentials(), None


@router.get("/events")
def upcoming_events(days: int = Query(7, ge=1, le=30)):
    """Get upcoming calendar events for the next N days."""
    creds, err = _require_auth()
    if err:
        return err

    service = get_calendar(creds)
    events = calendar_service.get_upcoming_events(service, days=days)
    return {"events": events, "days": days}


@router.get("/today")
def today_schedule():
    """Get today's calendar events."""
    creds, err = _require_auth()
    if err:
        return err

    service = get_calendar(creds)
    events = calendar_service.get_today_schedule(service)
    return {"events": events}


@router.get("/week")
def weekly_schedule():
    """Get this week's calendar events."""
    creds, err = _require_auth()
    if err:
        return err

    service = get_calendar(creds)
    events = calendar_service.get_weekly_schedule(service)
    return {"events": events}
