"""
chat_routes.py — Legacy chat endpoint (backward compatibility).

WHY:  The old /chat endpoint still works but now routes through the
      AI agent instead of the hardcoded resume chatbot.

WHERE: Mounted on the FastAPI app at root level.

HOW:  POST /chat  — accepts {question: str}, returns {answer: str}
      Internally delegates to the same agent pipeline as POST /assistant.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.session import session_manager
from backend.agent.assistant_agent import agent

router = APIRouter(tags=["Chat"])


class ChatRequest(BaseModel):
    question: str


@router.post("/chat")
def chat(request: ChatRequest):
    """
    Legacy chat endpoint.

    Now routes through the AI agent instead of the old document-only chatbot.
    Kept for backward compatibility with existing frontend code.
    """
    if not session_manager.is_authenticated():
        return JSONResponse(
            status_code=401,
            content={"answer": "Please login first."},
        )

    answer = agent.process(
        request.question,
        session_manager.get_credentials(),
    )

    return {"answer": answer}