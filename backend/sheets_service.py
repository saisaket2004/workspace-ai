"""
sheets_service.py — Google Sheets operations.

WHY:  Provides list, read, and search capabilities for Google Sheets.
      Uses Drive API for listing (Sheets API has no list endpoint)
      and Sheets API for reading cell data.

WHERE: Called by sheets_routes.py and tools.py.

HOW:  `from backend.sheets_service import list_sheets, read_sheet`
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from backend.google_service import get_drive

logger = logging.getLogger(__name__)

GOOGLE_SHEET_MIME = "application/vnd.google-apps.spreadsheet"


# ── Public API ─────────────────────────────────────────────────────────

def list_sheets(credentials, max_results: int = 50) -> List[Dict[str, str]]:
    """
    List Google Sheets in the user's Drive.

    Uses Drive API with mimeType filter.
    """
    drive = get_drive(credentials)
    result = drive.files().list(
        pageSize=max_results,
        fields="files(id, name, modifiedTime)",
        q=f"mimeType='{GOOGLE_SHEET_MIME}' and trashed=false",
        orderBy="modifiedTime desc",
    ).execute()

    return result.get("files", [])


def read_sheet(
    sheets_service,
    spreadsheet_id: str,
    range_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Read data from a Google Sheet.

    Args:
        range_name: A1 notation, e.g. "Sheet1!A1:D10".
                    If None, reads metadata + first sheet's data.

    Returns:
        {"id": ..., "title": ..., "sheets": [...], "values": [[...]]}
    """
    # Get spreadsheet metadata
    meta = sheets_service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
    ).execute()

    title = meta.get("properties", {}).get("title", "")
    sheet_names = [
        s.get("properties", {}).get("title", "")
        for s in meta.get("sheets", [])
    ]

    # Read values
    if range_name is None and sheet_names:
        range_name = sheet_names[0]  # Read first sheet

    values = []
    if range_name:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name,
        ).execute()
        values = result.get("values", [])

    return {
        "id": spreadsheet_id,
        "title": title,
        "sheets": sheet_names,
        "range": range_name or "",
        "values": values,
    }


def get_all_rows(
    sheets_service,
    spreadsheet_id: str,
    sheet_name: Optional[str] = None,
) -> List[List[str]]:
    """
    Return all rows from a sheet (defaults to the first sheet).

    Convenience wrapper around read_sheet().
    """
    data = read_sheet(sheets_service, spreadsheet_id, sheet_name)
    return data.get("values", [])


def search_data(
    credentials,
    query: str,
    max_results: int = 20,
) -> List[Dict[str, str]]:
    """
    Search for spreadsheets containing the query text.

    Uses Drive's fullText search scoped to Sheets mimeType.
    """
    drive = get_drive(credentials)
    q = (
        f"mimeType='{GOOGLE_SHEET_MIME}' "
        f"and fullText contains '{query}' "
        f"and trashed=false"
    )

    result = drive.files().list(
        pageSize=max_results,
        fields="files(id, name, modifiedTime)",
        q=q,
        orderBy="modifiedTime desc",
    ).execute()

    return result.get("files", [])
