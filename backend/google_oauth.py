"""Google OAuth2 protocol helpers.

Single-responsibility module for all Google OAuth2 logic. All outbound HTTP
calls use ``httpx`` in sync mode to match the project's sync handler
architecture.

State management uses Redis (via :mod:`backend.redis_client`) with SETEX for
atomic write-with-TTL and GETDEL for atomic read-and-delete. This prevents
replay attacks and is safe under multi-worker deployments.
"""

import logging
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
import redis as redis_lib
from fastapi import HTTPException

from backend.config import settings
from backend.redis_client import get_redis

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

STATE_TTL_SECONDS: int = 600  # 10 minutes — must not exceed this value


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
    """Generate a cryptographically random CSRF state token and store it in Redis.

    The token is stored with a TTL of :data:`STATE_TTL_SECONDS`. Tokens are
    consumed atomically by :func:`validate_and_consume_state` — replay is
    impossible even under concurrent load.

    Returns:
        A URL-safe random string used as the OAuth2 ``state`` parameter.

    Raises:
        HTTPException: 503 if Redis is unavailable.
    """
    state = secrets.token_urlsafe(32)
    key = f"oauth:state:{state}"
    try:
        get_redis().setex(key, STATE_TTL_SECONDS, "1")
    except redis_lib.RedisError as err:
        logger.error(
            "Redis unavailable — cannot store OAuth state. key=%s url=%s err=%s",
            key,
            settings.redis_url,
            err,
        )
        raise HTTPException(
            status_code=503,
            detail="Authentication service temporarily unavailable. Please try again.",
        ) from err
    return state


def validate_and_consume_state(state: str) -> None:
    """Validate and atomically consume a CSRF state token from Redis.

    Uses GETDEL — a single atomic Redis command that reads the key and
    deletes it in one operation. This prevents replay: if two concurrent
    requests arrive with the same token, only one will get a non-None result.

    Args:
        state: The ``state`` query parameter received in the OAuth2 callback.

    Raises:
        HTTPException: 400 if the state is unknown, expired, or already consumed.
        HTTPException: 503 if Redis is unavailable.
    """
    key = f"oauth:state:{state}"
    try:
        value = get_redis().getdel(key)
    except redis_lib.RedisError as err:
        logger.error(
            "Redis unavailable — cannot consume OAuth state. key=%s url=%s err=%s",
            key,
            settings.redis_url,
            err,
        )
        raise HTTPException(
            status_code=503,
            detail="Authentication service temporarily unavailable. Please try again.",
        ) from err
    if value is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")


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
    except httpx.HTTPStatusError as err:
        logger.error(
            "Google token endpoint returned %s: %s",
            err.response.status_code,
            err.response.text,
        )
        raise HTTPException(
            status_code=502, detail="Failed to exchange code with Google"
        ) from err
    except httpx.RequestError as err:
        logger.error("Network error contacting Google token endpoint: %s", err)
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
    except httpx.HTTPStatusError as err:
        logger.error(
            "Google userinfo endpoint returned %s: %s",
            err.response.status_code,
            err.response.text,
        )
        raise HTTPException(
            status_code=502, detail="Failed to fetch user info from Google"
        ) from err
    except httpx.RequestError as err:
        logger.error("Network error contacting Google userinfo endpoint: %s", err)
        raise HTTPException(
            status_code=502, detail="Failed to fetch user info from Google"
        ) from err
    data: dict[str, object] = response.json()
    missing = [f for f in ("sub", "email", "name") if f not in data]
    if missing:
        logger.error(
            "Google userinfo response missing required fields: %s. data=%s",
            missing,
            {k: v for k, v in data.items() if k != "access_token"},
        )
        raise HTTPException(
            status_code=502, detail="Failed to fetch user info from Google"
        )
    return GoogleUserInfo(
        google_id=str(data["sub"]),
        email=str(data["email"]),
        name=str(data["name"]),
        picture=str(data["picture"]) if data.get("picture") else None,
    )
