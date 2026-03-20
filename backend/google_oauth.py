"""Google OAuth2 protocol helpers.

Single-responsibility module for all Google OAuth2 logic. All outbound HTTP
calls use ``httpx`` in sync mode to match the project's sync handler
architecture.

State management uses an in-memory dict keyed by the random state token and
valued by the ``time.monotonic()`` timestamp at generation. This is safe for
a single-worker deployment only — see the design doc for the POC constraint.
"""

import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

from backend.config import settings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

STATE_TTL_SECONDS: float = 600.0  # 10 minutes

# In-memory CSRF state store: {state_token: created_at_monotonic}
# Single-worker POC only — not safe under multi-worker deployments.
state_store: dict[str, float] = {}


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class GoogleUserInfo:
    """Profile data returned by the Google userinfo endpoint."""

    google_id: str
    email: str
    name: str
    picture: str | None


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------


def generate_state() -> str:
    """Generate a cryptographically random CSRF state token and store it.

    Returns:
        A URL-safe random string used as the OAuth2 ``state`` parameter.
    """
    state = secrets.token_urlsafe(32)
    state_store[state] = time.monotonic()
    return state


def validate_and_consume_state(state: str) -> None:
    """Validate a received state token and remove it from the store.

    Args:
        state: The ``state`` query parameter received in the OAuth2 callback.

    Raises:
        HTTPException: 400 if the state is unknown or has expired.
    """
    created_at = state_store.get(state)
    if created_at is None:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    # Remove regardless — expired states must not be reused
    del state_store[state]
    if time.monotonic() - created_at > STATE_TTL_SECONDS:
        raise HTTPException(status_code=400, detail="OAuth state has expired")


# ---------------------------------------------------------------------------
# Google API helpers
# ---------------------------------------------------------------------------


def build_google_redirect_url(state: str) -> str:
    """Construct the Google authorization URL for the OAuth2 consent screen.

    Args:
        state: A CSRF state token (from :func:`generate_state`).

    Returns:
        A fully-qualified Google authorization URL including all required
        query parameters.
    """
    redirect_uri = f"{settings.backend_url}/auth/google/callback"
    params = urlencode(
        {
            "client_id": settings.google_client_id,
            "response_type": "code",
            "scope": "openid email profile",
            "redirect_uri": redirect_uri,
            "state": state,
        }
    )
    return f"{_GOOGLE_AUTH_URL}?{params}"


def exchange_code_for_tokens(code: str) -> dict[str, str]:
    """Exchange an authorization code for Google access and ID tokens.

    Args:
        code: The authorization code received in the OAuth2 callback.

    Returns:
        The JSON response body from the Google token endpoint as a dict.

    Raises:
        HTTPException: 502 if the Google token endpoint returns an error.
    """
    redirect_uri = f"{settings.backend_url}/auth/google/callback"
    try:
        response = httpx.post(
            _GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
    except (httpx.HTTPStatusError, httpx.RequestError) as err:
        raise HTTPException(
            status_code=502, detail="Failed to exchange code with Google"
        ) from err
    return dict(response.json())


def fetch_google_user_info(access_token: str) -> GoogleUserInfo:
    """Fetch the authenticated user's profile from the Google userinfo endpoint.

    Args:
        access_token: A valid Google OAuth2 access token.

    Returns:
        A :class:`GoogleUserInfo` populated from the userinfo response.

    Raises:
        HTTPException: 502 if the Google userinfo endpoint returns an error.
    """
    try:
        response = httpx.get(
            _GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
    except (httpx.HTTPStatusError, httpx.RequestError) as err:
        raise HTTPException(
            status_code=502, detail="Failed to fetch user info from Google"
        ) from err
    data: dict[str, object] = response.json()
    return GoogleUserInfo(
        google_id=str(data["sub"]),
        email=str(data["email"]),
        name=str(data["name"]),
        picture=str(data["picture"]) if data.get("picture") else None,
    )
