"""JWT authentication helpers and FastAPI cookie-based dependency providers."""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

import bcrypt  # pyright: ignore[reportMissingModuleSource]
import redis as redis_lib
from fastapi import Cookie, Depends, Header, HTTPException, status
from jose import JWTError, jwt  # pyright: ignore[reportMissingModuleSource]
from jose.exceptions import (
    ExpiredSignatureError,  # pyright: ignore[reportMissingModuleSource]
)

from backend.config import settings
from backend.redis_client import get_redis

logger = logging.getLogger(__name__)

# Allowlist of permitted extra JWT claim keys.
# NOTE: _ALLOWED_EXTRA_CLAIMS and ExtraClaims must be kept in sync manually.
# basedpyright enforces ExtraClaims at call sites; the frozenset is a runtime backstop.
_ALLOWED_EXTRA_CLAIMS: frozenset[str] = frozenset({"name", "picture"})

ExtraClaims = dict[Literal["name", "picture"], str]


def _get_token_from_request(
    access_token: Annotated[str | None, Cookie()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> str | None:
    """Extract the JWT access token from the cookie or Bearer header.

    Returns None when the cookie is absent so that optional-auth endpoints
    can remain publicly accessible.  Callers that require authentication
    should use :func:`get_optional_user` and then raise 401 if the result is
    None, or use :data:`WriteDep` which does so automatically.

    Args:
        access_token: The ``access_token`` cookie value, injected by FastAPI.
        authorization: Optional ``Authorization`` header.

    Returns:
        The raw JWT string, or None if neither auth mechanism is present.

    Raises:
        HTTPException: 401 if an ``Authorization`` header is present but malformed.
    """
    if access_token is not None:
        return access_token
    if authorization is None:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash.

    Args:
        plain_password: The raw password supplied by the caller.
        hashed_password: The stored bcrypt hash to compare against.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    return bool(
        bcrypt.checkpw(  # pyright: ignore[reportUnknownMemberType]
            plain_password.encode(), hashed_password.encode()
        )
    )


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt.

    Not used in the current MVP flow (the admin hash is supplied via
    ``ADMIN_PASSWORD_HASH`` in the environment).  Retained as a utility for
    future admin-management features (e.g. password rotation, seeding scripts).

    Args:
        plain_password: The raw password to hash.

    Returns:
        A bcrypt hash string suitable for storage.
    """
    return bcrypt.hashpw(  # pyright: ignore[reportUnknownMemberType]
        plain_password.encode(),
        bcrypt.gensalt(),  # pyright: ignore[reportUnknownMemberType]
    ).decode()


def create_access_token(subject: str, extra_claims: ExtraClaims | None = None) -> str:
    """Create a signed JWT access token.

    Args:
        subject: The JWT ``sub`` claim — the authenticated user's email.
        extra_claims: Optional additional claims to include in the payload
            (e.g. ``name``, ``picture``). Only allowlisted claims are included.
            Unknown keys are silently filtered out by the runtime backstop.

    Returns:
        A signed JWT string.
    """
    jti = secrets.token_urlsafe(16)
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload: dict[str, object] = {"sub": subject, "exp": expire, "jti": jti}
    if extra_claims:
        safe_claims = {
            k: v for k, v in extra_claims.items() if k in _ALLOWED_EXTRA_CLAIMS
        }
        payload.update(safe_claims)
    return str(
        jwt.encode(  # pyright: ignore[reportUnknownMemberType]
            payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )
    )


def _decode_token_subject(token: str) -> str:
    """Decode a JWT and return its subject claim.

    Performs a Redis-backed revocation check on the token's ``jti`` claim.
    Fails closed: if Redis is unavailable, raises 503 rather than allowing
    a potentially revoked token through.

    Args:
        token: A raw JWT string from the access_token cookie.

    Returns:
        The email embedded in the token's ``sub`` claim.

    Raises:
        HTTPException: 401 if the token is expired, its signature is invalid, or the
            sub claim is absent.
        HTTPException: 401 if the token has been revoked.
        HTTPException: 503 if Redis is unavailable during the revocation check.
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        subject: object = payload.get("sub")  # pyright: ignore[reportUnknownMemberType]
        if not isinstance(subject, str):
            raise credentials_error

        # Revocation check — fail-closed: Redis unavailable = 503
        jti: object = payload.get("jti")  # pyright: ignore[reportUnknownMemberType]
        if isinstance(jti, str):
            try:
                if get_redis().exists(f"oauth:revoked:{jti}"):
                    logger.warning(
                        "Rejected revoked token",
                        extra={
                            "event": "oauth.token.revoked",
                            "jti": jti,
                            "sub": subject,
                        },
                    )
                    raise credentials_error
            except HTTPException:
                raise
            except redis_lib.RedisError as err:
                logger.error(
                    "Redis unavailable during revocation check",
                    extra={
                        "event": "oauth.redis.error",
                        "operation": "revocation_check",
                        "redis_url": settings.redis_url,
                        "error": str(err),
                    },
                )
                raise HTTPException(
                    status_code=503,
                    detail="Authentication service temporarily unavailable.",
                ) from err

        return subject
    except ExpiredSignatureError as err:
        logger.debug("JWT validation failed (expired): %s", err)
        raise credentials_error from err
    except JWTError as err:
        logger.warning(
            "JWT validation failed — anomalous token "
            "(bad signature, algorithm confusion, or malformed)",
            extra={
                "event": "auth.jwt.invalid",
                "error": str(err),
                "error_type": type(err).__name__,
            },
        )
        raise credentials_error from err


def get_optional_user(
    token: Annotated[str | None, Depends(_get_token_from_request)],
) -> str | None:
    """Return the authenticated user's email, or None when no cookie is present.

    A cookie that IS present but contains an invalid or expired JWT raises 401
    immediately, so callers can distinguish "no auth" from "bad auth".

    Args:
        token: Raw JWT extracted from the ``access_token`` cookie, or None.

    Returns:
        The email embedded in the token's ``sub`` claim, or None if no cookie
        was sent.

    Raises:
        HTTPException: 401 if a cookie was sent but its JWT is invalid or expired.
        HTTPException: 401 if the token has been revoked.
        HTTPException: 503 if Redis is unavailable during the revocation check.
    """
    if token is None:
        return None
    return _decode_token_subject(token)


OptionalUserDep = Annotated[str | None, Depends(get_optional_user)]


def require_authenticated_user(
    user: OptionalUserDep,
) -> str:
    """Require a valid JWT; raise 401 if no token is present or it is invalid.

    Args:
        user: Result of get_optional_user — email or None.

    Returns:
        The authenticated user's email.

    Raises:
        HTTPException: 401 if the caller is not authenticated.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


WriteDep = Annotated[str, Depends(require_authenticated_user)]
