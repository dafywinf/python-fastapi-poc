"""User management and Google OAuth2 routes."""

import logging
import secrets as _secrets
from datetime import datetime, timezone
from typing import Annotated

import redis as redis_lib
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from jose import JWTError
from jose import jwt as _jwt  # pyright: ignore[reportMissingModuleSource]
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_session
from backend.exceptions import handle_exception
from backend.google_oauth import (
    build_google_redirect_url,
    consume_pkce_verifier,
    exchange_code_for_tokens,
    fetch_google_user_info,
    generate_state,
    validate_and_consume_state,
)
from backend.models import User
from backend.rate_limiter import limiter
from backend.redis_client import get_redis
from backend.schemas import UserResponse
from backend.security import ExtraClaims, OptionalUserDep, WriteDep, create_access_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["users"])

SessionDep = Annotated[Session, Depends(get_session)]


def _get_current_user(email: WriteDep, session: SessionDep) -> User:
    """Resolve the authenticated user's email to a User ORM object.

    Args:
        email: The JWT subject claim (user email) — provided by WriteDep.
        session: The database session.

    Returns:
        The :class:`User` row matching the authenticated email.  When
        ``settings.enable_password_auth`` is ``True`` and the JWT subject
        matches ``settings.admin_username``, returns a synthetic in-memory
        ``User`` object rather than querying the database.

    Raises:
        HTTPException: 404 if no user row exists for this email and the
            admin shortcut does not apply.
    """
    user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        if settings.enable_password_auth and email == settings.admin_username:
            return User(
                id=0,
                google_id="local-admin",
                email=email,
                name="Admin",
                picture=None,
                created_at=datetime.now(timezone.utc),
            )
        logger.warning("JWT valid but no user row found. email=%s", email)
        raise HTTPException(status_code=404, detail="User not found")
    return user


CurrentUserDep = Annotated[User, Depends(_get_current_user)]


@router.get("/auth/google/login")
@limiter.limit("20/minute")  # pyright: ignore[reportUnknownMemberType]
@handle_exception(logger)
def google_login(request: Request) -> RedirectResponse:
    """Redirect the browser to Google's OAuth2 consent screen.

    Generates a CSRF state token and PKCE code verifier, stores them, and
    builds the authorization URL with S256 challenge.

    Args:
        request: The Starlette request (required by slowapi for rate limiting).

    Returns:
        A 307 redirect to Google's consent screen.
    """
    state, code_verifier = generate_state()
    redirect_url = build_google_redirect_url(state, code_verifier)
    return RedirectResponse(url=redirect_url)


@router.get("/auth/google/callback")
@limiter.limit("20/minute")  # pyright: ignore[reportUnknownMemberType]
@handle_exception(logger)
def google_callback(
    request: Request,
    state: str,
    session: SessionDep,
    code: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Handle Google's OAuth2 callback, upsert the user, and issue a JWT cookie.

    Args:
        request: The Starlette request (required by slowapi for rate limiting).
        state: The CSRF state token to validate.
        session: The database session.
        code: The authorization code from Google (absent when the user denies consent).
        error: The error code from Google (e.g. ``access_denied``).

    Returns:
        A redirect to ``settings.frontend_url`` with two HttpOnly cookies set:
        ``access_token`` (SameSite=Lax, path=/) and ``refresh_token``
        (SameSite=Strict, path=/auth).

    Raises:
        HTTPException: 400 if the state is invalid, expired, or Google returned
            an error.
        HTTPException: 502 if the Google token or userinfo endpoints fail.
    """
    if error or not code:
        logger.warning(
            "OAuth callback received error from Google",
            extra={
                "event": "oauth.callback.error",
                "error_code": error or "missing_code",
            },
        )
        raise HTTPException(
            status_code=400, detail=error or "Authorization code missing"
        )
    validate_and_consume_state(state)
    code_verifier = consume_pkce_verifier(state)
    if code_verifier is None:
        logger.warning(
            "PKCE verifier missing after valid state consumption"
            " — possible partial write or replay",
            extra={"event": "oauth.pkce.verifier_missing", "state_prefix": state[:8]},
        )
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    tokens = exchange_code_for_tokens(code, code_verifier)
    access_token = tokens.get("access_token")
    if not access_token:
        logger.error(
            "Google token response missing access_token",
            extra={
                "event": "oauth.callback.error",
                "error_code": "missing_access_token",
            },
        )
        raise HTTPException(
            status_code=502, detail="Failed to exchange code with Google"
        )
    user_info = fetch_google_user_info(access_token)

    existing = session.execute(
        select(User).where(User.google_id == user_info.google_id)
    ).scalar_one_or_none()

    is_new_user = existing is None
    if is_new_user:
        user = User(
            google_id=user_info.google_id,
            email=user_info.email,
            name=user_info.name,
            picture=user_info.picture,
        )
        session.add(user)
    else:
        existing.name = user_info.name
        existing.picture = user_info.picture

    try:
        session.commit()
    except IntegrityError as err:
        session.rollback()
        logger.error(
            "IntegrityError upserting Google user",
            extra={
                "event": "oauth.callback.error",
                "error_code": "integrity_error",
                "email": user_info.email,
                "google_id": user_info.google_id,
            },
        )
        raise HTTPException(
            status_code=409,
            detail=(
                "An account with this email already exists. "
                "Please sign in with your original method."
            ),
        ) from err

    extra_claims: ExtraClaims = {"name": user_info.name}
    if user_info.picture is not None:
        extra_claims["picture"] = user_info.picture
    jwt_token = create_access_token(
        subject=user_info.email,
        extra_claims=extra_claims,
    )

    logger.info(
        "User login successful",
        extra={
            "event": "auth.login.success",
            "sub": user_info.email,
            "is_new_user": is_new_user,
        },
    )

    max_age = settings.access_token_expire_minutes * 60
    refresh_token = _secrets.token_urlsafe(32)
    refresh_ttl = settings.refresh_token_expire_days * 86400

    try:
        get_redis().setex(
            f"oauth:refresh:{refresh_token}", refresh_ttl, user_info.email
        )
    except redis_lib.RedisError as err:
        logger.error(
            "Redis error storing refresh token",
            extra={
                "event": "oauth.redis.error",
                "operation": "store_refresh_token",
                "redis_url": settings.redis_url,
                "error": str(err),
            },
        )
        raise HTTPException(
            status_code=503,
            detail="Authentication service temporarily unavailable.",
        ) from err

    # Derive secure flag from frontend scheme — Secure cookies are silently
    # dropped by browsers over plain HTTP, breaking the auth flow in dev.
    _secure = settings.frontend_url.startswith("https://")

    response = RedirectResponse(url=settings.frontend_url)
    response.set_cookie(
        key="access_token",
        value=jwt_token,
        httponly=True,
        secure=_secure,
        samesite="lax",
        path="/",
        max_age=max_age,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=_secure,
        samesite="strict",
        path="/auth",
        max_age=refresh_ttl,
    )
    return response


@router.post("/auth/refresh")
@limiter.limit("60/minute")  # pyright: ignore[reportUnknownMemberType]
@handle_exception(logger)
def refresh_token(
    request: Request,
    session: SessionDep,
    # Named refresh_token_cookie to avoid shadowing the function name under
    # basedpyright strict mode (which flags parameter/function name collisions).
    refresh_token_cookie: Annotated[str | None, Cookie(alias="refresh_token")] = None,
) -> Response:
    """Issue a new access JWT in exchange for a valid refresh token.

    Rotation: the old refresh token is consumed (GETDEL) and a new one is issued.
    A missing or expired refresh token returns 401.  If Redis fails after the
    old token is consumed but before the new token is stored, the old token is
    permanently gone — the caller must re-authenticate via Google OAuth.

    Args:
        request: The Starlette request (required by slowapi for rate limiting).
        session: The database session (used to fetch user profile for extra claims).
        refresh_token_cookie: Value of the refresh_token cookie.

    Returns:
        200 response with new access_token and refresh_token cookies set.

    Raises:
        HTTPException: 401 if the refresh token is missing or invalid.
        HTTPException: 503 if Redis is unavailable.
    """
    if refresh_token_cookie is None:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    key = f"oauth:refresh:{refresh_token_cookie}"
    try:
        email = get_redis().getdel(key)
    except redis_lib.RedisError as err:
        logger.error(
            "Redis error during token refresh",
            extra={
                "event": "oauth.redis.error",
                "operation": "refresh_token",
                "redis_url": settings.redis_url,
                "error": str(err),
            },
        )
        raise HTTPException(
            status_code=503,
            detail="Authentication service temporarily unavailable.",
        ) from err

    if email is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    email_str = str(email)
    user = session.execute(
        select(User).where(User.email == email_str)
    ).scalar_one_or_none()

    extra_claims: ExtraClaims | None = None
    if user is not None:
        extra_claims = {"name": user.name}
        if user.picture is not None:
            extra_claims["picture"] = user.picture

    new_access_token = create_access_token(
        subject=email_str,
        extra_claims=extra_claims,
    )
    new_refresh_token = _secrets.token_urlsafe(32)
    refresh_ttl = settings.refresh_token_expire_days * 86400

    try:
        get_redis().setex(f"oauth:refresh:{new_refresh_token}", refresh_ttl, email_str)
    except redis_lib.RedisError as err:
        logger.error(
            "Redis error storing new refresh token",
            extra={
                "event": "oauth.redis.error",
                "operation": "store_refresh_token",
                "redis_url": settings.redis_url,
                "error": str(err),
            },
        )
        raise HTTPException(
            status_code=503,
            detail="Authentication service temporarily unavailable.",
        ) from err

    logger.info(
        "Token refreshed",
        extra={"event": "auth.refresh", "sub": email_str},
    )

    _secure = settings.frontend_url.startswith("https://")

    response = Response(status_code=200)
    max_age = settings.access_token_expire_minutes * 60
    response.set_cookie(
        "access_token",
        new_access_token,
        httponly=True,
        secure=_secure,
        samesite="lax",
        path="/",
        max_age=max_age,
    )
    response.set_cookie(
        "refresh_token",
        new_refresh_token,
        httponly=True,
        secure=_secure,
        samesite="strict",
        path="/auth",
        max_age=refresh_ttl,
    )
    return response


@router.post("/auth/logout", status_code=204)
@limiter.limit("20/minute")  # pyright: ignore[reportUnknownMemberType]
@handle_exception(logger)
def logout(
    request: Request,
    user: OptionalUserDep,
    access_token: Annotated[str | None, Cookie()] = None,
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> Response:
    """Revoke the current session tokens and clear auth cookies.

    Adds the access JWT's jti to the Redis revocation blocklist with TTL equal
    to the remaining token lifetime. Deletes the refresh token from Redis.

    Args:
        request: The Starlette request (required by slowapi for rate limiting).
        user: The currently authenticated user email (or None).
        access_token: The access_token cookie value.
        refresh_token: The refresh_token cookie value.

    Returns:
        204 No Content with both cookies cleared.
    """
    # Revoke access token by jti
    if access_token:
        try:
            payload = _jwt.decode(
                access_token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            jti: object = payload.get("jti")
            exp: object = payload.get("exp")
            if isinstance(jti, str) and isinstance(exp, (int, float)):
                remaining = max(0, int(exp - datetime.now(timezone.utc).timestamp()))
                if remaining > 0:
                    get_redis().setex(f"oauth:revoked:{jti}", remaining, "1")
        except (JWTError, redis_lib.RedisError) as err:
            # Best-effort revocation at logout: if Redis is down, the cookie is
            # still cleared. Logout always succeeds from the user's perspective;
            # the access token will expire naturally within access_token_expire_minutes.
            logger.warning(
                "Best-effort logout revocation failed"
                " — access token will expire naturally",
                extra={
                    "event": "auth.logout.revocation_failed",
                    "error": str(err),
                    "error_type": type(err).__name__,
                },
            )

    # Delete refresh token
    if refresh_token:
        try:
            get_redis().delete(f"oauth:refresh:{refresh_token}")
        except redis_lib.RedisError as err:
            logger.warning(
                "Best-effort logout refresh token deletion failed",
                extra={
                    "event": "auth.logout.refresh_delete_failed",
                    "error": str(err),
                    "error_type": type(err).__name__,
                },
            )

    if user:
        logger.info(
            "User logged out",
            extra={"event": "auth.logout", "sub": user},
        )

    _secure = settings.frontend_url.startswith("https://")

    response = Response(status_code=204)
    response.delete_cookie("access_token", path="/", secure=_secure, samesite="lax")
    response.delete_cookie(
        "refresh_token", path="/auth", secure=_secure, samesite="strict"
    )
    return response


@router.get("/users/", response_model=list[UserResponse])
@handle_exception(logger)
def list_users(_: WriteDep, session: SessionDep) -> list[User]:
    """Return all users who have logged in, most recent first.

    Args:
        _: Requires a valid JWT — enforces authentication without using the value.
        session: The database session.

    Returns:
        A list of :class:`UserResponse` objects.

    Raises:
        HTTPException: 401 if the caller is not authenticated.
    """
    return list(
        session.execute(select(User).order_by(User.created_at.desc())).scalars()
    )


@router.get("/users/me", response_model=UserResponse)
@handle_exception(logger)
def get_current_user_profile(current_user: CurrentUserDep) -> User:
    """Return the authenticated user's own profile.

    Args:
        current_user: Resolved via :func:`_get_current_user` from the JWT subject.

    Returns:
        The :class:`UserResponse` for the authenticated user.
    """
    return current_user
