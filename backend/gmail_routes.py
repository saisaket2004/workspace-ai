"""
gmail_routes.py — REST endpoints for Gmail.

WHERE: Mounted on /gmail prefix in app.py.

HOW:  GET /gmail/messages       — list recent messages
      GET /gmail/message/{id}   — read full message
      GET /gmail/search?q=...   — search mail
      GET /gmail/unread         — unread inbox messages
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from backend.session import session_manager
from backend.google_service import get_gmail
from backend import gmail_service

router = APIRouter(prefix="/gmail", tags=["Gmail"])


def _require_auth():
    if not session_manager.is_authenticated():
        return None, JSONResponse(
            status_code=401,
            content={"error": "Please login first."},
        )
    return session_manager.get_credentials(), None


@router.get("/messages")
def list_messages(max_results: int = Query(15, ge=1, le=50)):
    """List recent email messages."""
    creds, err = _require_auth()
    if err:
        return err

    service = get_gmail(creds)
    messages = gmail_service.list_messages(service, max_results=max_results)
    return {"messages": messages}


@router.get("/message/{message_id}")
def read_message(message_id: str):
    """Read a full email message by ID."""
    creds, err = _require_auth()
    if err:
        return err

    service = get_gmail(creds)
    message = gmail_service.read_message(service, message_id)
    return {"message": message}


@router.get("/search")
def search_mail(q: str = Query(..., description="Gmail search query")):
    """Search emails using Gmail search syntax."""
    creds, err = _require_auth()
    if err:
        return err

    service = get_gmail(creds)
    results = gmail_service.search_mail(service, query=q)
    return {"results": results, "query": q}


@router.get("/unread")
def unread_messages(max_results: int = Query(15, ge=1, le=50)):
    """Get unread inbox messages."""
    creds, err = _require_auth()
    if err:
        return err

    service = get_gmail(creds)
    messages = gmail_service.get_unread_messages(service, max_results=max_results)
    return {"messages": messages}
