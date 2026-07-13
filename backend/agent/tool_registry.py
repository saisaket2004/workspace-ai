"""
tool_registry.py — Central registry for all AI agent tools.

WHY:  The intent_classifier selects tools based on their metadata (name,
      description, parameters). The assistant_agent executes them. This file
      connects the agent to the underlying Google API services.

WHERE: Used by intent_classifier.py and assistant_agent.py.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from backend.google_service import (
    get_drive, get_gmail, get_calendar, get_docs, get_sheets, get_slides,
    get_user_info,
)
from backend import drive_service
from backend import gmail_service
from backend import calendar_service
from backend import docs_service
from backend import sheets_service
from backend import slides_service

logger = logging.getLogger(__name__)


@dataclass
class Tool:
    """Describes a single callable tool available to the AI agent."""
    name: str
    description: str
    category: str
    parameters: Dict[str, str]  # dict of param_name -> param_description
    execute: Callable  # (credentials, **kwargs) → Any

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "parameters": self.parameters,
        }


# ═══════════════════════════════════════════════════════════════════════
# TOOL IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════════════

# ── Drive ──────────────────────────────────────────────────────────────

def _drive_search(credentials, **kwargs):
    svc = get_drive(credentials)
    return drive_service.search_files(svc, query=kwargs.get("query", ""))

def _drive_read_file(credentials, **kwargs):
    svc = get_drive(credentials)
    return drive_service.read_file_content(
        svc,
        file_id=kwargs["file_id"],
        file_name=kwargs.get("file_name", "file"),
        mime_type=kwargs.get("mime_type", "text/plain"),
    )

def _drive_list_files(credentials, **kwargs):
    svc = get_drive(credentials)
    return drive_service.list_files(svc, max_results=kwargs.get("max_results", 30))


# ── Gmail ──────────────────────────────────────────────────────────────

def _gmail_search(credentials, **kwargs):
    svc = get_gmail(credentials)
    return gmail_service.search_mail(svc, query=kwargs.get("query", ""))

def _gmail_read(credentials, **kwargs):
    svc = get_gmail(credentials)
    return gmail_service.read_message(svc, message_id=kwargs["message_id"])

def _gmail_unread(credentials, **kwargs):
    svc = get_gmail(credentials)
    return gmail_service.get_unread_messages(svc, max_results=kwargs.get("max_results", 10))

def _gmail_list(credentials, **kwargs):
    svc = get_gmail(credentials)
    return gmail_service.list_messages(svc, max_results=kwargs.get("max_results", 10))


# ── Calendar ───────────────────────────────────────────────────────────

def _calendar_upcoming(credentials, **kwargs):
    svc = get_calendar(credentials)
    return calendar_service.get_upcoming_events(svc, days=kwargs.get("days", 7))

def _calendar_today(credentials, **kwargs):
    svc = get_calendar(credentials)
    return calendar_service.get_today_schedule(svc)

def _calendar_week(credentials, **kwargs):
    svc = get_calendar(credentials)
    return calendar_service.get_weekly_schedule(svc)


# ── Docs ───────────────────────────────────────────────────────────────

def _docs_list(credentials, **kwargs):
    return docs_service.list_docs(credentials, max_results=kwargs.get("max_results", 30))

def _docs_read(credentials, **kwargs):
    svc = get_docs(credentials)
    return docs_service.read_doc(svc, doc_id=kwargs["doc_id"])


# ── Sheets ─────────────────────────────────────────────────────────────

def _sheets_list(credentials, **kwargs):
    return sheets_service.list_sheets(credentials, max_results=kwargs.get("max_results", 30))

def _sheets_read(credentials, **kwargs):
    svc = get_sheets(credentials)
    return sheets_service.read_sheet(
        svc,
        spreadsheet_id=kwargs["spreadsheet_id"],
        range_name=kwargs.get("range"),
    )


# ── Slides ─────────────────────────────────────────────────────────────

def _slides_list(credentials, **kwargs):
    return slides_service.list_presentations(credentials, max_results=kwargs.get("max_results", 30))

def _slides_read(credentials, **kwargs):
    svc = get_slides(credentials)
    return slides_service.read_presentation(svc, presentation_id=kwargs["presentation_id"])


# ── Profile ────────────────────────────────────────────────────────────

def _profile_info(credentials, **kwargs):
    return get_user_info(credentials)


# ═══════════════════════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════════════════════

TOOL_REGISTRY: Dict[str, Tool] = {
    # ── Drive ──────────────────────────────────────────────────────────
    "drive_search": Tool(
        name="drive_search",
        description="Search for files in Google Drive by name or content. Use when user asks to find or locate a file.",
        category="drive",
        parameters={"query": "str, required — the search term"},
        execute=_drive_search,
    ),
    "drive_read": Tool(
        name="drive_read",
        description="Read the text content of a file in Google Drive (PDF, Google Doc, text, Word doc).",
        category="drive",
        parameters={
            "file_id": "str, required",
            "file_name": "str, optional",
            "mime_type": "str, required (e.g. application/pdf)",
        },
        execute=_drive_read_file,
    ),
    "drive_list": Tool(
        name="drive_list",
        description="List recent files in the user's Google Drive.",
        category="drive",
        parameters={"max_results": "int, optional, default 30"},
        execute=_drive_list_files,
    ),

    # ── Gmail ──────────────────────────────────────────────────────────
    "gmail_search": Tool(
        name="gmail_search",
        description="Search emails using Gmail search syntax.",
        category="gmail",
        parameters={"query": "str, required — Gmail search query"},
        execute=_gmail_search,
    ),
    "gmail_read": Tool(
        name="gmail_read",
        description="Read the full body of a specific email by its message ID.",
        category="gmail",
        parameters={"message_id": "str, required"},
        execute=_gmail_read,
    ),
    "gmail_unread": Tool(
        name="gmail_unread",
        description="Get unread inbox emails.",
        category="gmail",
        parameters={"max_results": "int, optional, default 10"},
        execute=_gmail_unread,
    ),
    "gmail_list": Tool(
        name="gmail_list",
        description="List recent emails showing subject, sender, and snippet.",
        category="gmail",
        parameters={"max_results": "int, optional, default 10"},
        execute=_gmail_list,
    ),

    # ── Calendar ───────────────────────────────────────────────────────
    "calendar_upcoming": Tool(
        name="calendar_upcoming",
        description="Get upcoming calendar events for the next N days.",
        category="calendar",
        parameters={"days": "int, optional, default 7"},
        execute=_calendar_upcoming,
    ),
    "calendar_today": Tool(
        name="calendar_today",
        description="Get today's calendar events and schedule.",
        category="calendar",
        parameters={},
        execute=_calendar_today,
    ),
    "calendar_week": Tool(
        name="calendar_week",
        description="Get this week's calendar events (next 7 days).",
        category="calendar",
        parameters={},
        execute=_calendar_week,
    ),

    # ── Docs ───────────────────────────────────────────────────────────
    "docs_list": Tool(
        name="docs_list",
        description="List Google Docs in the user's Drive.",
        category="docs",
        parameters={"max_results": "int, optional, default 30"},
        execute=_docs_list,
    ),
    "docs_read": Tool(
        name="docs_read",
        description="Read the full text of a Google Doc by its document ID.",
        category="docs",
        parameters={"doc_id": "str, required"},
        execute=_docs_read,
    ),

    # ── Sheets ─────────────────────────────────────────────────────────
    "sheets_list": Tool(
        name="sheets_list",
        description="List Google Sheets in the user's Drive.",
        category="sheets",
        parameters={"max_results": "int, optional, default 30"},
        execute=_sheets_list,
    ),
    "sheets_read": Tool(
        name="sheets_read",
        description="Read data from a Google Sheet by its spreadsheet ID. Optionally specify a range.",
        category="sheets",
        parameters={
            "spreadsheet_id": "str, required",
            "range": "str, optional — e.g. 'Sheet1!A1:D10'",
        },
        execute=_sheets_read,
    ),

    # ── Slides ─────────────────────────────────────────────────────────
    "slides_list": Tool(
        name="slides_list",
        description="List Google Slides presentations in the user's Drive.",
        category="slides",
        parameters={"max_results": "int, optional, default 30"},
        execute=_slides_list,
    ),
    "slides_read": Tool(
        name="slides_read",
        description="Read the content (slide titles and text) of a Google Slides presentation.",
        category="slides",
        parameters={"presentation_id": "str, required"},
        execute=_slides_read,
    ),

    # ── Profile ────────────────────────────────────────────────────────
    "profile_info": Tool(
        name="profile_info",
        description="Get the user's Google profile (name, email, profile picture).",
        category="profile",
        parameters={},
        execute=_profile_info,
    ),
}


def get_all_tool_metadata() -> List[Dict[str, Any]]:
    """Returns metadata for all registered tools to send to the LLM."""
    return [tool.get_metadata() for tool in TOOL_REGISTRY.values()]


def execute_tool(tool_name: str, credentials, **kwargs) -> Dict[str, Any]:
    """
    Look up a tool by name and execute it.
    Always returns a standardized object format.
    """
    tool = TOOL_REGISTRY.get(tool_name)
    
    if not tool:
        return {
            "success": False,
            "tool": tool_name,
            "data": None,
            "error": f"Unknown tool: {tool_name}"
        }

    try:
        logger.info("Executing tool: %s with args: %s", tool_name, kwargs)
        result = tool.execute(credentials, **kwargs)
        return {
            "success": True,
            "tool": tool_name,
            "data": result,
            "error": None
        }
    except Exception as e:
        logger.exception("Tool %s failed", tool_name)
        return {
            "success": False,
            "tool": tool_name,
            "data": None,
            "error": f"Tool '{tool_name}' failed: {str(e)}"
        }
