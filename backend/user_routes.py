"""User management and Google OAuth2 routes."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_session
from backend.exceptions import handle_exception
from backend.google_oauth import (
    build_google_redirect_url,
    exchange_code_for_tokens,
    fetch_google_user_info,
    generate_state,
    validate_and_consume_state,
)
from backend.models import User
from backend.schemas import UserResponse
from backend.security import WriteDep, create_access_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["users"])

SessionDep = Annotated[Session, Depends(get_session)]


def _get_current_user(email: WriteDep, session: SessionDep) -> User:
    """Resolve the authenticated user's email to a User ORM object.

    Args:
        email: The JWT subject claim (user email) — provided by WriteDep.
        session: The database session.

    Returns:
        The :class:`User` row matching the authenticated email.

    Raises:
        HTTPException: 404 if no user row exists for this email.
    """
    user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        logger.warning("JWT valid but no user row found. email=%s", email)
        raise HTTPException(status_code=404, detail="User not found")
    return user


CurrentUserDep = Annotated[User, Depends(_get_current_user)]


@router.get("/auth/google/login")
@handle_exception(logger)
def google_login() -> RedirectResponse:
    """Redirect the browser to Google's OAuth2 consent screen.

    Generates a CSRF state token, stores it, and builds the authorization URL.

    Returns:
        A 307 redirect to Google's consent screen.
    """
    state = generate_state()
    redirect_url = build_google_redirect_url(state)
    return RedirectResponse(url=redirect_url)


@router.get("/auth/google/callback")
@handle_exception(logger)
def google_callback(
    state: str, session: SessionDep, code: str | None = None, error: str | None = None
) -> RedirectResponse:
    """Handle Google's OAuth2 callback, upsert the user, and issue a JWT.

    Args:
        state: The CSRF state token to validate.
        session: The database session.
        code: The authorization code from Google (absent when the user denies consent).
        error: The error code from Google (e.g. ``access_denied``).

    Returns:
        A redirect to the frontend /auth/callback page with the JWT in the URL
        fragment ``#token=`` — fragments are not transmitted to servers and do not
        appear in access logs or Referer headers.

    Raises:
        HTTPException: 400 if the state is invalid, expired, or Google returned
            an error (e.g. the user denied consent on the consent screen).
        HTTPException: 502 if the Google token or userinfo endpoints fail.
    """
    if error or not code:
        raise HTTPException(
            status_code=400, detail=error or "Authorization code missing"
        )
    validate_and_consume_state(state)
    tokens = exchange_code_for_tokens(code)
    access_token = tokens.get("access_token")
    if not access_token:
        logger.error(
            "Google token response missing access_token. keys=%s", list(tokens.keys())
        )
        raise HTTPException(
            status_code=502, detail="Failed to exchange code with Google"
        )
    user_info = fetch_google_user_info(access_token)

    existing = session.execute(
        select(User).where(User.google_id == user_info.google_id)
    ).scalar_one_or_none()

    if existing is None:
        user = User(
            google_id=user_info.google_id,
            email=user_info.email,
            name=user_info.name,
            picture=user_info.picture,
        )
        session.add(user)
        logger.info(
            "Created new user. email=%s google_id=%s",
            user_info.email,
            user_info.google_id,
        )
    else:
        existing.name = user_info.name
        existing.picture = user_info.picture
        logger.info(
            "Updated profile. email=%s google_id=%s",
            user_info.email,
            user_info.google_id,
        )

    try:
        session.commit()
    except IntegrityError as err:
        session.rollback()
        logger.error(
            "IntegrityError upserting Google user. email=%s google_id=%s err=%s",
            user_info.email,
            user_info.google_id,
            err,
        )
        raise HTTPException(
            status_code=409,
            detail=(
                "An account with this email already exists. "
                "Please sign in with your original method."
            ),
        ) from err

    jwt_token = create_access_token(
        subject=user_info.email,
        extra_claims={"name": user_info.name},
    )
    frontend_callback = f"{settings.frontend_url}/auth/callback#token={jwt_token}"
    return RedirectResponse(url=frontend_callback)


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
