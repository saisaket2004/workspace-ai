"""
drive_service.py — Google Drive operations.

WHY:  Encapsulates every Drive interaction so routes and the AI agent
      never call the raw Google API directly.

WHERE: Called by drive_routes.py and tools.py.

HOW:  Each function takes a Drive API service object (from google_service.py)
      plus any arguments, and returns structured dicts — never raw API JSON.
"""

from __future__ import annotations

import io
import logging
import os
from typing import Any, Dict, List, Optional

from googleapiclient.http import MediaIoBaseDownload

from backend.config import settings
from backend.document_processor import extract_pdf_text

logger = logging.getLogger(__name__)

DOWNLOAD_FOLDER = settings.DOWNLOAD_FOLDER


# ── List / Search ──────────────────────────────────────────────────────

def list_files(
    service,
    max_results: int = 100,
    mime_type: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    List files in the user's Drive.

    Args:
        mime_type: Optional filter, e.g. "application/pdf".
    """
    query = ""
    if mime_type:
        query = f"mimeType='{mime_type}'"

    results = service.files().list(
        pageSize=max_results,
        fields="files(id, name, mimeType, modifiedTime, size)",
        q=query or None,
        orderBy="modifiedTime desc",
    ).execute()

    return results.get("files", [])


def search_files(service, query: str, max_results: int = 20) -> List[Dict[str, str]]:
    """
    Full-text search across file names and contents.

    Uses Drive's `fullText contains '...'` operator.
    """
    # Escape single quotes to prevent Drive API 400 syntax errors
    safe_query = query.replace("'", "\\'")
    q = f"fullText contains '{safe_query}' and trashed = false"

    results = service.files().list(
        pageSize=max_results,
        fields="files(id, name, mimeType, modifiedTime)",
        q=q,
        orderBy="modifiedTime desc",
    ).execute()

    return results.get("files", [])


# ── Download ───────────────────────────────────────────────────────────

def download_file(service, file_id: str, file_name: str) -> str:
    """Download a binary file (PDF, image, etc.) to the local downloads folder."""
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

    request = service.files().get_media(fileId=file_id)
    filepath = os.path.join(DOWNLOAD_FOLDER, file_name)

    with open(filepath, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

    logger.info("Downloaded %s → %s", file_name, filepath)
    return filepath


# ── Read Content ───────────────────────────────────────────────────────

def read_pdf(service, file_id: str, file_name: str) -> str:
    """Download a PDF and extract its text."""
    path = download_file(service, file_id, file_name)
    text = extract_pdf_text(path)
    return text[:settings.MAX_DOCUMENT_CHARS]


def read_text_file(service, file_id: str) -> str:
    """Read a plain-text file from Drive."""
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue().decode("utf-8", errors="replace")[:settings.MAX_DOCUMENT_CHARS]


def read_google_doc_via_export(service, file_id: str) -> str:
    """
    Export a Google Doc as plain text.

    Google Docs can't be downloaded with get_media — they must be exported.
    """
    request = service.files().export_media(
        fileId=file_id,
        mimeType="text/plain",
    )
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue().decode("utf-8", errors="replace")[:settings.MAX_DOCUMENT_CHARS]


def read_word_doc(service, file_id: str, file_name: str) -> str:
    """
    Download a .docx file and extract text.
    """
    path = download_file(service, file_id, file_name)
    try:
        from backend.document_processor import extract_docx_text
        return extract_docx_text(path)[:settings.MAX_DOCUMENT_CHARS]
    except ImportError:
        logger.warning("python-docx not installed; returning raw download path.")
        return f"[Word document downloaded to {path}]"

def read_powerpoint(service, file_id: str, file_name: str) -> str:
    """
    Download a .pptx file and extract text.
    """
    path = download_file(service, file_id, file_name)
    try:
        from backend.document_processor import extract_pptx_text
        return extract_pptx_text(path)[:settings.MAX_DOCUMENT_CHARS]
    except ImportError:
        logger.warning("python-pptx not installed; returning raw download path.")
        return f"[PowerPoint presentation downloaded to {path}]"

def read_file_content(service, file_id: str, file_name: str, mime_type: str) -> str:
    """
    Unified reader — automatically picks the right extraction method.

    This is the function the AI agent calls.
    """
    if mime_type == "application/pdf":
        return read_pdf(service, file_id, file_name)
    elif mime_type == "application/vnd.google-apps.document":
        return read_google_doc_via_export(service, file_id)
    elif mime_type == "application/vnd.google-apps.spreadsheet":
        from backend import sheets_service
        try:
            return str(sheets_service.read_sheet(get_sheets(service._http.credentials), file_id))[:settings.MAX_DOCUMENT_CHARS]
        except Exception:
            from backend.google_service import get_sheets
            # Try again by grabbing valid creds
            return "[Error reading Google Sheet]"
    elif mime_type == "application/vnd.google-apps.presentation":
        from backend import slides_service
        from backend.google_service import get_slides
        try:
            return str(slides_service.read_presentation(get_slides(service._http.credentials), file_id))[:settings.MAX_DOCUMENT_CHARS]
        except Exception:
            return "[Error reading Google Slide]"
    elif mime_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ):
        return read_word_doc(service, file_id, file_name)
    elif mime_type in (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.ms-powerpoint",
    ):
        return read_powerpoint(service, file_id, file_name)
    elif mime_type.startswith("text/"):
        return read_text_file(service, file_id)
    else:
        return f"[Cannot read file type: {mime_type}. Please just let the user know you found it.]"