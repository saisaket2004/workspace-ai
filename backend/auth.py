"""
auth.py — Authentication routes.

WHY:  Handles Google OAuth 2.0 login flow and user profile.
      Cleaned up from the old version — no longer downloads PDFs or
      summarises documents inside the callback.

WHERE: Mounted on the FastAPI app at root level.

HOW:  /login          → redirects to Google consent screen
      /auth/callback  → exchanges code, stores creds, redirects to frontend
      /auth/status    → returns authentication status
      /userinfo       → returns user profile (name, email, picture)
      /logout         → clears session
"""

from __future__ import annotations

import os
import logging

# Allow OAuth over HTTP during local development
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse

from google_auth_oauthlib.flow import Flow

from backend.config import settings, CREDENTIALS_FILE, SCOPES
from backend.session import session_manager
from backend.google_service import get_user_info
import backend.session as session  # backward-compat alias

logger = logging.getLogger(__name__)

router = APIRouter()

REDIRECT_URI = settings.REDIRECT_URI

import json

def _get_oauth_flow(state=None):
    """
    Helper to initialize the Google OAuth Flow.
    Supports both environment variable injection (for Production)
    and local file fallback (for Development).
    """
    credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    
    if credentials_json:
        # Production: Create Flow from memory
        client_config = json.loads(credentials_json)
        return Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            state=state,
            redirect_uri=REDIRECT_URI,
            autogenerate_code_verifier=False,
        )
    else:
        # Development: Create Flow from local credentials file
        if not CREDENTIALS_FILE.exists():
            raise FileNotFoundError(f"Missing local file: {CREDENTIALS_FILE}")
            
        return Flow.from_client_secrets_file(
            str(CREDENTIALS_FILE),
            scopes=SCOPES,
            state=state,
            redirect_uri=REDIRECT_URI,
            autogenerate_code_verifier=False,
        )


# ── Login ──────────────────────────────────────────────────────────────

@router.get("/login")
def login():
    """Redirect the user to Google's OAuth consent screen."""
    try:
        flow = _get_oauth_flow()
    except FileNotFoundError:
        logger.error(f"Credentials file missing: {CREDENTIALS_FILE}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Server Configuration Error: Google OAuth credentials file missing."},
        )

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    session_manager.oauth_state = state
    session_manager.oauth_code_verifier = ""

    logger.info("Authorization URL: %s", authorization_url)
    return RedirectResponse(authorization_url)


# ── Callback ───────────────────────────────────────────────────────────

@router.get("/auth/callback")
def auth_callback(request: Request):
    """
    Handle the OAuth callback from Google.

    Exchanges the authorization code for credentials, stores them
    in the session, fetches user profile, and redirects to the frontend.
    """
    # Read the state parameter directly from the request URL
    # This makes the callback completely resilient to server restarts during development
    state_from_url = request.query_params.get("state")
    
    try:
        flow = _get_oauth_flow(state=state_from_url)
    except FileNotFoundError:
        logger.error(f"Credentials file missing: {CREDENTIALS_FILE}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Server Configuration Error: Google OAuth credentials file missing."},
        )

    # Restore PKCE code verifier (if any)
    if session_manager.oauth_code_verifier:
        flow.code_verifier = session_manager.oauth_code_verifier

    # Exchange authorization code for access token
    flow.fetch_token(authorization_response=str(request.url))

    credentials = flow.credentials

    # Store in new session manager
    session_manager.set_credentials(credentials)

    # Also set backward-compatible module-level variable
    session.credentials = credentials

    # Fetch user profile
    try:
        user_info = get_user_info(credentials)
        session_manager.user_info.name = user_info.get("name", "")
        session_manager.user_info.email = user_info.get("email", "")
        session_manager.user_info.picture = user_info.get("picture", "")
        logger.info("User logged in: %s", session_manager.user_info.email)
    except Exception as e:
        logger.warning("Could not fetch user info: %s", e)

    # Redirect to frontend
    return RedirectResponse(f"{settings.FRONTEND_URL}?auth=success")


# ── Status ─────────────────────────────────────────────────────────────

@router.get("/auth/status")
def auth_status():
    """Check if the user is currently authenticated."""
    return {
        "authenticated": session_manager.is_authenticated(),
        "user": {
            "name": session_manager.user_info.name,
            "email": session_manager.user_info.email,
        } if session_manager.is_authenticated() else None,
    }


# ── User Info ──────────────────────────────────────────────────────────

@router.get("/userinfo")
def userinfo():
    """Return the authenticated user's Google profile."""
    if not session_manager.is_authenticated():
        return JSONResponse(
            status_code=401,
            content={"error": "Not authenticated. Please login first."},
        )

    return {
        "name": session_manager.user_info.name,
        "email": session_manager.user_info.email,
        "picture": session_manager.user_info.picture,
    }


# ── Logout ─────────────────────────────────────────────────────────────

@router.get("/logout")
def logout():
    """Clear the session and log the user out."""
    session_manager.clear()
    session.credentials = None
    session.document_text = ""
    session.selected_file = ""
    return {"message": "Logged out successfully."}