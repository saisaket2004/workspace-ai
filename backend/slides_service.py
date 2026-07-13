"""
slides_service.py — Google Slides operations.

WHY:  Provides list and read capabilities for Google Slides presentations.
      Uses Drive API for listing (Slides API has no list endpoint)
      and Slides API for reading slide content.

WHERE: Called by slides_routes.py and tools.py.

HOW:  `from backend.slides_service import list_presentations, read_presentation`
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from backend.google_service import get_drive

logger = logging.getLogger(__name__)

GOOGLE_SLIDES_MIME = "application/vnd.google-apps.presentation"


# ── Helpers ────────────────────────────────────────────────────────────

def _extract_text_from_element(element: Dict) -> str:
    """Extract text from a page element (shape, text box, etc.)."""
    shape = element.get("shape", {})
    text = shape.get("text", {})
    parts: List[str] = []

    for text_element in text.get("textElements", []):
        text_run = text_element.get("textRun")
        if text_run:
            parts.append(text_run.get("content", ""))

    return "".join(parts).strip()


# ── Public API ─────────────────────────────────────────────────────────

def list_presentations(credentials, max_results: int = 50) -> List[Dict[str, str]]:
    """
    List Google Slides presentations in the user's Drive.

    Uses Drive API with mimeType filter.
    """
    drive = get_drive(credentials)
    result = drive.files().list(
        pageSize=max_results,
        fields="files(id, name, modifiedTime)",
        q=f"mimeType='{GOOGLE_SLIDES_MIME}' and trashed=false",
        orderBy="modifiedTime desc",
    ).execute()

    return result.get("files", [])


def read_presentation(
    slides_service,
    presentation_id: str,
) -> Dict[str, Any]:
    """
    Read a Google Slides presentation.

    Returns:
        {
            "id": ...,
            "title": ...,
            "slides": [
                {"slideNumber": 1, "title": "...", "content": "..."},
                ...
            ]
        }
    """
    pres = slides_service.presentations().get(
        presentationId=presentation_id,
    ).execute()

    title = pres.get("title", "")
    slides_data: List[Dict[str, Any]] = []

    for idx, slide in enumerate(pres.get("slides", []), start=1):
        slide_texts: List[str] = []
        slide_title = ""

        for element in slide.get("pageElements", []):
            text = _extract_text_from_element(element)
            if text:
                # First non-empty text in a slide is usually the title
                if not slide_title:
                    slide_title = text
                slide_texts.append(text)

        slides_data.append({
            "slideNumber": idx,
            "title": slide_title,
            "content": "\n".join(slide_texts),
        })

    return {
        "id": pres.get("presentationId", ""),
        "title": title,
        "slideCount": len(slides_data),
        "slides": slides_data,
    }
