"""
intent_classifier.py — Fast hybrid intent router with Memory Resolution.

WHY:  Detects intents and resolves pronouns ("it", "latest", "first one")
      using the user's current session memory.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

from backend.chatbot import ask_gemini_json
from backend.agent.tool_registry import get_all_tool_metadata
from backend.session import session_manager

logger = logging.getLogger(__name__)

# Basic keywords that don't need context
ROUTER_RULES = [
    (r"\b(calendar|meeting|schedule|events)\b.*\btoday\b", [{"tool": "calendar_today"}]),
    (r"\b(calendar|meeting|schedule|events)\b.*\b(next|upcoming|week)\b", [{"tool": "calendar_week"}]),
    (r"\b(unread|new)\b.*\b(email|mail|message)\b", [{"tool": "gmail_unread"}]),
]

PLANNER_PROMPT = """You are a tiny JSON-only router for a Workspace Assistant.

AVAILABLE TOOLS:
{tools}

SESSION CONTEXT:
{context}

USER QUESTION:
{question}

You must return a JSON array of tool executions.
If the user references previous items ("it", "the first one", "latest"), use the IDs from the SESSION CONTEXT.
If they want to read/summarize a file, you MUST use the read tools (e.g. drive_read, docs_read) and supply the correct ID.
If they want to search, use search tools.

CRITICAL: When using drive_search, extract ONLY the filename or search term. Strip out action verbs (e.g., "Summarize", "Open", "Read", "Compare").
For example: "Summarize AAC RESEARCH 1.pdf" -> query: "AAC RESEARCH 1.pdf".

Example 1: "Summarize the first and second" (where search returned docs)
{{
    "executions": [
        {{"tool": "docs_read", "args": {{"doc_id": "id1"}}}},
        {{"tool": "docs_read", "args": {{"doc_id": "id2"}}}}
    ]
}}

Example 2: "Search for resume"
{{
    "executions": [
        {{"tool": "drive_search", "args": {{"query": "resume"}}}}
    ]
}}

Example 3: "Summarize AAC RESEARCH 1.pdf"
{{
    "executions": [
        {{"tool": "drive_search", "args": {{"query": "AAC RESEARCH 1.pdf"}}}}
    ]
}}

Example 4: "Read it" (where last_opened_item was a Drive file)
{{
    "executions": [
        {{"tool": "drive_read", "args": {{"file_id": "id_from_context", "mime_type": "type_from_context"}}}}
    ]
}}

Return ONLY JSON describing the tools to run. Never output text.
"""

def _build_context_summary() -> str:
    ctx = []
    if session_manager.last_searched_items:
        items = session_manager.last_searched_items[:5]
        summary = [{"id": i.get("id"), "name": i.get("name") or i.get("title") or i.get("subject"), "type": i.get("mimeType", "unknown")} for i in items]
        ctx.append(f"Last searched items (1 to {len(items)}): {json.dumps(summary)}")
        
    if session_manager.last_opened_item:
        i = session_manager.last_opened_item
        ctx.append(f"Last opened item ('it', 'this'): id={i.get('id')}, name={i.get('name')}, type={i.get('mimeType')}")
        
    if not ctx:
        return "No recent context."
    return "\n".join(ctx)


def detect_intents(question: str) -> List[Dict[str, Any]]:
    """
    Returns a list of dicts: [{"tool": "tool_name", "args": {"query": "..."}}]
    """
    question_lower = question.lower()
    
    # 1. Fast Python Routing (only for stateless queries)
    # If the question contains contextual pronouns, skip to Gemini
    context_keywords = ["it", "this", "that", "latest", "previous", "first", "second", "last", "next", "one"]
    needs_context = any(kw in question_lower.split() for kw in context_keywords)
    
    if not needs_context:
        selected_tools = []
        for pattern, tools in ROUTER_RULES:
            if re.search(pattern, question_lower):
                selected_tools.extend(tools)
                
        if selected_tools:
            logger.info("Python router matched stateless intent.")
            return selected_tools
            
    # 2. Gemini Contextual Router
    logger.info("Using Gemini Router for complex intent resolution.")
    
    tools_json = json.dumps(get_all_tool_metadata(), indent=2)
    context_str = _build_context_summary()
    
    prompt = PLANNER_PROMPT.format(tools=tools_json, context=context_str, question=question)
    
    try:
        response_text = ask_gemini_json(prompt)
        
        # Strip potential markdown code blocks
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        response_text = response_text.strip()
            
        decision = json.loads(response_text)
        
        executions = decision.get("executions", [])
        
        # Fallback if it returned old format
        if not executions and "tools" in decision:
            executions = [{"tool": t, "args": {}} for t in decision["tools"]]
            
        logger.info(f"Gemini Intent Router chose: {executions}")
        return executions
    except Exception as e:
        logger.exception("Failed to parse Gemini router response")
        return []
