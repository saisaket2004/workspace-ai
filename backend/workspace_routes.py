"""
workspace_routes.py — Unified Workspace endpoints.

WHY:  This is the most important route file.  POST /assistant is the
      SINGLE chat endpoint that routes user questions through the AI Agent.
      GET /workspace/search provides cross-service search.

WHERE: Mounted on /workspace prefix in app.py.
       POST /assistant is mounted at root level.

HOW:  POST /assistant           — unified AI chat (the main endpoint)
      GET /workspace/search?q=  — search across all Google services
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.session import session_manager
from backend.agent.assistant_agent import agent
from backend.google_service import get_drive
from backend import drive_service
from backend import docs_service
from backend import sheets_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Workspace"])


def _require_auth():
    creds = session_manager.get_credentials()
    if not creds:
        return None, JSONResponse(
            status_code=401,
            content={"error": "Please login first."},
        )
        
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                logger.info("[Session] Credentials refreshed")
                session_manager.set_credentials(creds)
            except Exception as e:
                logger.warning(f"[Session] Session expired, refresh failed: {e}")
                session_manager.clear()
                return None, JSONResponse(
                    status_code=401,
                    content={"error": "Your session has expired. Please sign in again."},
                )
        else:
            logger.warning("[Session] Session expired and cannot be refreshed.")
            session_manager.clear()
            return None, JSONResponse(
                status_code=401,
                content={"error": "Your session has expired. Please sign in again."},
            )
            
    return creds, None


# ── Unified AI Assistant ───────────────────────────────────────────────

class AssistantRequest(BaseModel):
    question: str


@router.post("/assistant")
async def assistant_endpoint(request: AssistantRequest):
    """
    Main entrypoint for the intelligent AI agent.
    """
    creds, err = _require_auth()
    if err:
        return err

    try:
        result = await agent.process(request.question, creds)
        return result
    except Exception as e:
        logger.exception("Agent error")
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal agent error: {str(e)}"}
        )


# ── Workspace Search ───────────────────────────────────────────────────

@router.get("/workspace/search")
def workspace_search(q: str = Query(..., description="Search query")):
    """Search across all Google Workspace services."""
    creds, err = _require_auth()
    if err:
        return err

    results = []

    # Drive (all file types)
    try:
        drive_svc = get_drive(creds)
        drive_results = drive_service.search_files(drive_svc, q)
        for f in drive_results:
            f["source"] = "drive"
        results.extend(drive_results)
    except Exception as e:
        logger.warning("Drive search failed: %s", e)

    # Docs
    try:
        doc_results = docs_service.search_docs(creds, q)
        for d in doc_results:
            d["source"] = "docs"
        results.extend(doc_results)
    except Exception as e:
        logger.warning("Docs search failed: %s", e)

    # Sheets
    try:
        sheet_results = sheets_service.search_data(creds, q)
        for s in sheet_results:
            s["source"] = "sheets"
        results.extend(sheet_results)
    except Exception as e:
        logger.warning("Sheets search failed: %s", e)

    # Deduplicate by file ID
    seen = set()
    unique = []
    for item in results:
        fid = item.get("id", "")
        if fid not in seen:
            seen.add(fid)
            unique.append(item)

    return {"results": unique, "query": q, "total": len(unique)}
