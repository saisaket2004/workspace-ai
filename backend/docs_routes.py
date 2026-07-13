"""
docs_routes.py — REST endpoints for Google Docs.

WHERE: Mounted on /docs prefix in app.py.

HOW:  GET /docs/list            — list all Google Docs
      GET /docs/read/{doc_id}   — read document content
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.session import session_manager
from backend.google_service import get_docs
from backend import docs_service

router = APIRouter(prefix="/docs", tags=["Docs"])


def _require_auth():
    if not session_manager.is_authenticated():
        return None, JSONResponse(
            status_code=401,
            content={"error": "Please login first."},
        )
    return session_manager.get_credentials(), None


@router.get("/list")
def list_docs():
    """List Google Docs in the user's Drive."""
    creds, err = _require_auth()
    if err:
        return err

    docs = docs_service.list_docs(creds)
    return {"docs": docs}


@router.get("/read/{doc_id}")
def read_doc(doc_id: str):
    """Read the full text of a Google Doc."""
    creds, err = _require_auth()
    if err:
        return err

    service = get_docs(creds)
    doc = docs_service.read_doc(service, doc_id)
    return {"doc": doc}
