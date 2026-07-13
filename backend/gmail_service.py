"""
gmail_service.py — Gmail operations.

WHY:  Provides clean, structured access to Gmail data.  Raw Gmail API
      responses are deeply nested; this module flattens them into simple dicts.

WHERE: Called by gmail_routes.py and tools.py.

HOW:  `from backend.gmail_service import list_messages, read_message`
"""

from __future__ import annotations

import base64
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────

def _decode_body(payload: Dict) -> str:
    """Recursively extract the plain-text body from a Gmail message payload."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    # Multipart: recurse into parts
    for part in payload.get("parts", []):
        text = _decode_body(part)
        if text:
            return text

    return ""


def _extract_header(headers: List[Dict], name: str) -> str:
    """Pull a single header value by name."""
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def _summarize_message(msg: Dict) -> Dict[str, str]:
    """Convert a raw Gmail message to a minimal summary dict."""
    headers = msg.get("payload", {}).get("headers", [])
    return {
        "id": msg["id"],
        "threadId": msg.get("threadId", ""),
        "subject": _extract_header(headers, "Subject"),
        "from": _extract_header(headers, "From"),
        "date": _extract_header(headers, "Date"),
        "snippet": msg.get("snippet", ""),
    }


# ── Public API ─────────────────────────────────────────────────────────

def list_messages(service, max_results: int = 15) -> List[Dict[str, str]]:
    """List recent messages with subject, sender, and snippet."""
    result = service.users().messages().list(
        userId="me",
        maxResults=max_results,
    ).execute()

    messages = []
    for item in result.get("messages", []):
        msg = service.users().messages().get(
            userId="me",
            id=item["id"],
            format="metadata",
            metadataHeaders=["Subject", "From", "Date"],
        ).execute()
        messages.append(_summarize_message(msg))

    return messages


def search_mail(service, query: str, max_results: int = 15) -> List[Dict[str, str]]:
    """
    Search Gmail using Gmail search syntax.

    Examples: "from:amazon", "subject:invoice", "is:unread after:2025/01/01"
    """
    result = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=max_results,
    ).execute()

    messages = []
    for item in result.get("messages", []):
        msg = service.users().messages().get(
            userId="me",
            id=item["id"],
            format="metadata",
            metadataHeaders=["Subject", "From", "Date"],
        ).execute()
        messages.append(_summarize_message(msg))

    return messages


def read_message(service, message_id: str) -> Dict[str, Any]:
    """Read a full email message including decoded body."""
    msg = service.users().messages().get(
        userId="me",
        id=message_id,
        format="full",
    ).execute()

    headers = msg.get("payload", {}).get("headers", [])
    body = _decode_body(msg.get("payload", {}))

    return {
        "id": msg["id"],
        "threadId": msg.get("threadId", ""),
        "subject": _extract_header(headers, "Subject"),
        "from": _extract_header(headers, "From"),
        "to": _extract_header(headers, "To"),
        "date": _extract_header(headers, "Date"),
        "body": body,
        "snippet": msg.get("snippet", ""),
        "labelIds": msg.get("labelIds", []),
    }


def get_attachments(service, message_id: str) -> List[Dict[str, str]]:
    """List attachments on a message (metadata only — no download)."""
    msg = service.users().messages().get(
        userId="me",
        id=message_id,
        format="full",
    ).execute()

    attachments = []
    for part in msg.get("payload", {}).get("parts", []):
        filename = part.get("filename")
        if filename:
            attachments.append({
                "filename": filename,
                "mimeType": part.get("mimeType", ""),
                "size": part.get("body", {}).get("size", 0),
                "attachmentId": part.get("body", {}).get("attachmentId", ""),
            })

    return attachments


def get_unread_messages(service, max_results: int = 15) -> List[Dict[str, str]]:
    """Return unread inbox messages."""
    return search_mail(service, "is:unread in:inbox", max_results)
