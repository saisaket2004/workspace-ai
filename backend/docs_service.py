"""
docs_service.py — Google Docs operations.

WHY:  Provides list, read, and search capabilities for Google Docs.
      Uses Drive API for listing/searching (Docs API doesn't have list)
      and Docs API for reading document content.

WHERE: Called by docs_routes.py and tools.py.

HOW:  `from backend.docs_service import list_docs, read_doc`
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from backend.google_service import get_drive

logger = logging.getLogger(__name__)

GOOGLE_DOC_MIME = "application/vnd.google-apps.document"


# ── Helpers ────────────────────────────────────────────────────────────

def _extract_text_from_doc(doc: Dict) -> str:
    """
    Walk the Docs API document body and extract all text.

    The Docs API returns a deeply nested structure of structural elements,
    paragraphs, and text runs. This flattens it to a single string.
    """
    text_parts: List[str] = []
    body = doc.get("body", {})

    for element in body.get("content", []):
        paragraph = element.get("paragraph")
        if not paragraph:
            continue
        for text_element in paragraph.get("elements", []):
            text_run = text_element.get("textRun")
            if text_run:
                text_parts.append(text_run.get("content", ""))

    return "".join(text_parts)


# ── Public API ─────────────────────────────────────────────────────────

def list_docs(credentials, max_results: int = 50) -> List[Dict[str, str]]:
    """
    List Google Docs in the user's Drive.

    Uses Drive API with mimeType filter because the Docs API
    does not have a list endpoint.
    """
    drive = get_drive(credentials)
    result = drive.files().list(
        pageSize=max_results,
        fields="files(id, name, modifiedTime)",
        q=f"mimeType='{GOOGLE_DOC_MIME}' and trashed=false",
        orderBy="modifiedTime desc",
    ).execute()

    return result.get("files", [])


def read_doc(docs_service, doc_id: str) -> Dict[str, Any]:
    """
    Read the full text of a Google Doc.

    Returns:
        {"id": ..., "title": ..., "content": "full text..."}
    """
    doc = docs_service.documents().get(documentId=doc_id).execute()
    content = _extract_text_from_doc(doc)

    return {
        "id": doc.get("documentId", ""),
        "title": doc.get("title", ""),
        "content": content,
    }


def search_docs(
    credentials,
    query: str,
    max_results: int = 20,
) -> List[Dict[str, str]]:
    """
    Search Google Docs by content.

    Uses Drive's fullText search scoped to Google Docs mimeType.
    """
    drive = get_drive(credentials)
    q = (
        f"mimeType='{GOOGLE_DOC_MIME}' "
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
