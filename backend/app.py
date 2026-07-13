"""
app.py — FastAPI application entry point.

WHY:  Central place that creates the app, registers all routers,
      configures CORS, and adds exception handling.

WHERE: Run with `uvicorn backend.app:app --reload`

HOW:  All route modules are imported and mounted here.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ── Routers ────────────────────────────────────────────────────────────
from backend.auth import router as auth_router
from backend.chat_routes import router as chat_router
from backend.drive_routes import router as drive_router
from backend.gmail_routes import router as gmail_router
from backend.calendar_routes import router as calendar_router
from backend.docs_routes import router as docs_router
from backend.sheets_routes import router as sheets_router
from backend.slides_routes import router as slides_router
from backend.workspace_routes import router as workspace_router

# ── Logging ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Workspace AI Assistant",
    description="ChatGPT for Google Workspace — ask anything about your Drive, Gmail, Calendar, Docs, Sheets, and Slides.",
    version="2.0.0",
)

# ── CORS ───────────────────────────────────────────────────────────────
from backend.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        settings.FRONTEND_URL,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register all routers ───────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(drive_router)
app.include_router(gmail_router)
app.include_router(calendar_router)
app.include_router(docs_router)
app.include_router(sheets_router)
app.include_router(slides_router)
app.include_router(workspace_router)


# ── Global exception handler ──────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error. Please try again."},
    )


# ── Health check ───────────────────────────────────────────────────────
@app.get("/")
def home():
    return {
        "status": "success",
        "message": "Workspace AI Backend is Running 🚀",
        "version": "2.0.0",
        "endpoints": {
            "auth": ["/login", "/auth/callback", "/auth/status", "/userinfo", "/logout"],
            "assistant": ["POST /assistant", "POST /chat"],
            "drive": ["/drive/files", "/drive/search", "/drive/read/{id}"],
            "gmail": ["/gmail/messages", "/gmail/message/{id}", "/gmail/search", "/gmail/unread"],
            "calendar": ["/calendar/events", "/calendar/today", "/calendar/week"],
            "docs": ["/docs/list", "/docs/read/{id}"],
            "sheets": ["/sheets/list", "/sheets/read/{id}"],
            "slides": ["/slides/list"],
            "workspace": ["/workspace/search"],
        },
    }


# ── Startup ────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    logger.info("=" * 60)
    logger.info("  Workspace AI Assistant v2.0.0")
    logger.info("  Endpoints registered: %d", len(app.routes))
    logger.info("=" * 60)

    # Deployment Validation
    if not settings.GEMINI_API_KEY:
        logger.warning("[WARNING] GEMINI_API_KEY is missing! AI agent will fail.")
        
    if not settings.CREDENTIALS_FILE.exists():
        logger.warning(f"[WARNING] Google OAuth credentials file missing: {settings.CREDENTIALS_FILE}")
        logger.warning("[WARNING] OAuth Login will fail.")

    logger.info(f"  Frontend URL: {settings.FRONTEND_URL}")
    logger.info(f"  Redirect URI: {settings.REDIRECT_URI}")
    logger.info("=" * 60)