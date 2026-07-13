"""
drive_routes.py — REST endpoints for Google Drive.

WHY:  Exposes Drive operations as HTTP endpoints.  The AI agent calls
      the service layer directly, but these routes let the frontend
      (or external clients) access Drive data too.

WHERE: Mounted on /drive prefix in app.py.

HOW:  GET /drive/files         — list files
      GET /drive/search?q=...  — search files
      GET /drive/read/{file_id}— read file content
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from backend.session import session_manager
from backend.google_service import get_drive
from backend import drive_service

router = APIRouter(prefix="/drive", tags=["Drive"])


# ── Auth guard ─────────────────────────────────────────────────────────

def _require_auth():
    """Return credentials or an error response."""
    if not session_manager.is_authenticated():
        return None, JSONResponse(
            status_code=401,
            content={"error": "Please login first."},
        )
    return session_manager.get_credentials(), None


# ── Endpoints ──────────────────────────────────────────────────────────

@router.get("/files")
def list_files():
    """List files in the user's Google Drive."""
    creds, err = _require_auth()
    if err:
        return err

    service = get_drive(creds)
    files = drive_service.list_files(service)
    return {"files": files}


@router.get("/search")
def search_files(q: str = Query(..., description="Search query")):
    """Search Drive files by name or content."""
    creds, err = _require_auth()
    if err:
        return err

    service = get_drive(creds)
    results = drive_service.search_files(service, query=q)
    return {"results": results, "query": q}


@router.get("/read/{file_id}")
def read_file(file_id: str):
    """Read the text content of a file by its ID."""
    creds, err = _require_auth()
    if err:
        return err

    service = get_drive(creds)

    # Get file metadata to determine mime type
    meta = service.files().get(
        fileId=file_id,
        fields="id, name, mimeType",
    ).execute()

    content = drive_service.read_file_content(
        service,
        file_id=file_id,
        file_name=meta.get("name", "file"),
        mime_type=meta.get("mimeType", ""),
    )

    return {
        "file": meta,
        "content": content,
    }