"""
slides_routes.py — REST endpoints for Google Slides.

WHERE: Mounted on /slides prefix in app.py.

HOW:  GET /slides/list  — list all presentations
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.session import session_manager
from backend import slides_service

router = APIRouter(prefix="/slides", tags=["Slides"])


def _require_auth():
    if not session_manager.is_authenticated():
        return None, JSONResponse(
            status_code=401,
            content={"error": "Please login first."},
        )
    return session_manager.get_credentials(), None


@router.get("/list")
def list_presentations():
    """List Google Slides presentations in the user's Drive."""
    creds, err = _require_auth()
    if err:
        return err

    presentations = slides_service.list_presentations(creds)
    return {"presentations": presentations}
