"""
sheets_routes.py — REST endpoints for Google Sheets.

WHERE: Mounted on /sheets prefix in app.py.

HOW:  GET /sheets/list            — list all spreadsheets
      GET /sheets/read/{sheet_id} — read spreadsheet data
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from backend.session import session_manager
from backend.google_service import get_sheets
from backend import sheets_service

router = APIRouter(prefix="/sheets", tags=["Sheets"])


def _require_auth():
    if not session_manager.is_authenticated():
        return None, JSONResponse(
            status_code=401,
            content={"error": "Please login first."},
        )
    return session_manager.get_credentials(), None


@router.get("/list")
def list_sheets():
    """List Google Sheets in the user's Drive."""
    creds, err = _require_auth()
    if err:
        return err

    sheets = sheets_service.list_sheets(creds)
    return {"sheets": sheets}


@router.get("/read/{spreadsheet_id}")
def read_sheet(
    spreadsheet_id: str,
    range: str = Query(None, description="A1 notation range, e.g. 'Sheet1!A1:D10'"),
):
    """Read data from a Google Sheet."""
    creds, err = _require_auth()
    if err:
        return err

    service = get_sheets(creds)
    data = sheets_service.read_sheet(service, spreadsheet_id, range_name=range)
    return {"sheet": data}
