"""
chatbot.py — Low-level Gemini API wrapper.

WHY:  Single place that talks to the Gemini API.  Every other module
      (agent, tools, routes) goes through these helpers instead of
      importing the Gemini SDK directly.

WHERE: Called by agent.py (primarily) and by legacy routes.

HOW:  `from backend.chatbot import ask_gemini, ask_gemini_json`
"""

from __future__ import annotations

import logging
import os
import time
from functools import wraps

from dotenv import load_dotenv
from google import genai
from google.genai.errors import APIError

from backend.config import settings

load_dotenv()

logger = logging.getLogger(__name__)

# ── Client ─────────────────────────────────────────────────────────────
client = genai.Client(
    api_key=settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY"),
)

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

# ── Retry Logic ────────────────────────────────────────────────────────

def with_retry(func):
    """
    Exponential backoff decorator for Gemini API calls.
    Retries max 3 times with delays: 1s, 2s, 4s.
    Only retries for 429, 503, and 504.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        delays = [1, 2, 4]
        for attempt in range(len(delays) + 1):
            try:
                return func(*args, **kwargs)
            except APIError as e:
                # Check status code from APIError
                status = getattr(e, 'code', None)
                if status not in (429, 503, 504):
                    raise # Don't retry auth/invalid requests

                if attempt < len(delays):
                    delay = delays[attempt]
                    logger.warning(
                        "Gemini API error %s. Retrying in %ds (Attempt %d/%d)", 
                        status, delay, attempt + 1, len(delays)
                    )
                    time.sleep(delay)
                else:
                    logger.error("Gemini API failed after %d retries.", len(delays))
                    raise
            except Exception as e:
                # Some errors might not be APIError, e.g., network timeout
                err_str = str(e)
                if any(x in err_str for x in ["429", "503", "504"]):
                    if attempt < len(delays):
                        delay = delays[attempt]
                        logger.warning(
                            "Gemini network error. Retrying in %ds (Attempt %d/%d)", 
                            delay, attempt + 1, len(delays)
                        )
                        time.sleep(delay)
                    else:
                        raise
                else:
                    raise
    return wrapper

# ── Core functions ─────────────────────────────────────────────────────

@with_retry
def _generate_content_with_retry(*args, **kwargs):
    return client.models.generate_content(*args, **kwargs)

def ask_gemini(prompt: str) -> str:
    """Send a prompt to Gemini and return the text response."""
    try:
        response = _generate_content_with_retry(
            model=MODEL,
            contents=prompt,
        )
        return response.text
    except Exception as e:
        logger.exception("Gemini API error")
        return f"Sorry, I encountered an error: {str(e)}"


def ask_gemini_json(prompt: str) -> str:
    """
    Send a prompt that expects a JSON response.

    Uses the same endpoint but with a system instruction
    nudging Gemini to return only JSON.
    """
    try:
        response = _generate_content_with_retry(
            model=MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
            },
        )
        return response.text
    except Exception as e:
        logger.exception("Gemini JSON API error")
        return '{"tool": "none", "args": {}}'


# ── Backward-compatible helpers ────────────────────────────────────────

def summarize_document(text: str) -> str:
    """Summarize a document in bullet points (used by legacy auth flow)."""
    prompt = f"""Summarize the following document in bullet points.

{text}
"""
    return ask_gemini(prompt)


def chat_with_document(document_text: str, user_question: str) -> str:
    """
    Answer a question about a specific document.

    Kept for backward compatibility with the old /chat endpoint.
    """
    prompt = f"""You are a Google Workspace AI Assistant.

Answer the question using ONLY the information in the document below.
If the answer is not available, say: "I couldn't find that information in the document."

Document:
{document_text}

Question:
{user_question}

Answer professionally.
"""
    return ask_gemini(prompt)