"""JWT authentication helpers and FastAPI OAuth2 dependency providers."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt  # pyright: ignore[reportMissingModuleSource]
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt  # pyright: ignore[reportMissingModuleSource]

from backend.config import settings

logger = logging.getLogger(__name__)

# auto_error=False so that GET endpoints can remain public (no token → None).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


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


def create_access_token(subject: str) -> str:
    """Create a signed JWT access token for the given subject (username).

    Args:
        subject: The identifier to embed in the token (typically a username).

    Returns:
        A signed JWT string.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload: dict[str, object] = {"sub": subject, "exp": expire}
    return str(
        jwt.encode(  # pyright: ignore[reportUnknownMemberType]
            payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )
    )


def _decode_token_subject(token: str) -> str:
    """Decode a JWT and return its subject claim.

    Args:
        token: A raw JWT string from the Authorization header.

    Returns:
        The username embedded in the token's ``sub`` claim.

    Raises:
        HTTPException: 401 if the token is missing, expired, or otherwise invalid.
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
        return subject
    except JWTError as err:
        raise credentials_error from err


def get_optional_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> str | None:
    """Return the authenticated username, or None when no token is provided.

    A token that IS provided but fails validation raises 401 immediately, so
    callers can distinguish "no auth" from "bad auth".

    Args:
        token: Raw Bearer token from the Authorization header, or None.

    Returns:
        The username embedded in the token, or None if no token was sent.

    Raises:
        HTTPException: 401 if a token was sent but is invalid or expired.
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
        user: Result of get_optional_user — username or None.

    Returns:
        The authenticated username.

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
