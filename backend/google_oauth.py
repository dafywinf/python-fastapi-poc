"""Google OAuth2 protocol helpers.

Single-responsibility module for all Google OAuth2 logic. All outbound HTTP
calls use ``httpx`` in sync mode to match the project's sync handler
architecture.

State management uses Redis (via :mod:`backend.redis_client`) with SETEX for
atomic write-with-TTL and GETDEL for atomic read-and-delete. This prevents
replay attacks and is safe under multi-worker deployments.

PKCE (RFC 7636) is implemented using the S256 challenge method. The code
verifier is stored in Redis alongside the state token and consumed atomically
during the callback. This prevents authorization code interception attacks.
"""

import base64
import hashlib
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
_PKCE_VERIFIER_PREFIX = "oauth:pkce:"


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


def generate_state() -> tuple[str, str]:
    """Generate a CSRF state token and PKCE code verifier, storing both in Redis.

    The state token is stored under ``oauth:state:{state}`` and the PKCE code
    verifier is stored under ``oauth:pkce:{state}``, both written atomically via
    a single ``MULTI/EXEC`` pipeline with a TTL of :data:`STATE_TTL_SECONDS`.
    The pipeline guarantees all-or-nothing: a mid-write crash cannot leave an
    orphaned state key without a corresponding verifier. Tokens are consumed
    atomically by :func:`validate_and_consume_state` and
    :func:`consume_pkce_verifier` — replay is impossible even under concurrent
    load.

    The code verifier is generated per RFC 7636: 32 random bytes encoded as
    base64url without padding, yielding a 43-character string.

    Returns:
        A ``(state, code_verifier)`` tuple where ``state`` is the OAuth2 CSRF
        token and ``code_verifier`` is the PKCE verifier for the S256 challenge.

    Raises:
        HTTPException: 503 if Redis is unavailable.
    """
    state = secrets.token_urlsafe(32)
    raw = base64.urlsafe_b64encode(secrets.token_bytes(32))
    code_verifier = raw.rstrip(b"=").decode("ascii")
    state_key = f"oauth:state:{state}"
    pkce_key = f"{_PKCE_VERIFIER_PREFIX}{state}"
    try:
        pipe = get_redis().pipeline(transaction=True)  # pyright: ignore[reportUnknownMemberType]
        pipe.setex(state_key, STATE_TTL_SECONDS, "1")
        pipe.setex(pkce_key, STATE_TTL_SECONDS, code_verifier)
        pipe.execute()
    except redis_lib.RedisError as err:
        logger.error(
            "Redis unavailable — cannot store OAuth state",
            extra={
                "event": "oauth.redis.error",
                "operation": "generate_state",
                "redis_url": settings.redis_url,
                "error": str(err),
            },
        )
        raise HTTPException(
            status_code=503,
            detail="Authentication service temporarily unavailable. Please try again.",
        ) from err
    return state, code_verifier


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
            "Redis unavailable — cannot consume OAuth state",
            extra={
                "event": "oauth.redis.error",
                "operation": "validate_and_consume_state",
                "redis_url": settings.redis_url,
                "error": str(err),
            },
        )
        raise HTTPException(
            status_code=503,
            detail="Authentication service temporarily unavailable. Please try again.",
        ) from err
    if value is None:
        logger.warning(
            "OAuth state validation failed — unknown or expired state",
            extra={"event": "oauth.state.invalid", "state_prefix": state[:8]},
        )
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")


def consume_pkce_verifier(state: str) -> str | None:
    """Atomically retrieve and delete the PKCE code verifier for a given state.

    Uses GETDEL — a single atomic Redis command that reads the key and deletes
    it in one operation. This prevents the verifier from being reused across
    multiple token exchange attempts.

    Args:
        state: The OAuth2 ``state`` parameter received in the callback.

    Returns:
        The code verifier string if found, or ``None`` if the state is unknown,
        expired, or the verifier has already been consumed.

    Raises:
        HTTPException: 503 if Redis is unavailable.
    """
    key = f"{_PKCE_VERIFIER_PREFIX}{state}"
    try:
        value: str | None = get_redis().getdel(key)  # type: ignore[assignment]
    except redis_lib.RedisError as err:
        logger.error(
            "Redis unavailable — cannot consume PKCE verifier",
            extra={
                "event": "oauth.redis.error",
                "operation": "consume_pkce_verifier",
                "redis_url": settings.redis_url,
                "error": str(err),
            },
        )
        raise HTTPException(
            status_code=503,
            detail="Authentication service temporarily unavailable. Please try again.",
        ) from err
    return value


# ---------------------------------------------------------------------------
# Google API helpers
# ---------------------------------------------------------------------------


def build_google_redirect_url(state: str, code_verifier: str) -> str:
    """Construct the Google authorization URL for the OAuth2 consent screen.

    Derives the S256 PKCE code challenge from ``code_verifier`` and appends
    ``code_challenge`` and ``code_challenge_method=S256`` to the redirect URL.
    The challenge is computed as the base64url-encoded SHA-256 hash of the
    verifier, with padding stripped per RFC 7636 §4.2.

    Args:
        state: A CSRF state token (from :func:`generate_state`).
        code_verifier: The PKCE code verifier (from :func:`generate_state`).

    Returns:
        A fully-qualified Google authorization URL including all required
        query parameters and PKCE challenge.
    """
    redirect_uri = f"{settings.backend_url}/auth/google/callback"
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    params = urlencode(
        {
            "client_id": settings.google_client_id,
            "response_type": "code",
            "scope": "openid email profile",
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{_GOOGLE_AUTH_URL}?{params}"


def exchange_code_for_tokens(code: str, code_verifier: str) -> dict[str, str]:
    """Exchange an authorization code for Google access and ID tokens.

    Includes the PKCE ``code_verifier`` in the token request body so Google
    can verify the challenge presented during the authorization request. This
    prevents authorization code interception attacks per RFC 7636 §4.5.

    Args:
        code: The authorization code received in the OAuth2 callback.
        code_verifier: The PKCE code verifier generated during the login step.

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
                "code_verifier": code_verifier,
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
