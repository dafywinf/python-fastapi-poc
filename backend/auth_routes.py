"""Authentication routes — issues JWT tokens via the OAuth2 password flow."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from backend.config import settings
from backend.exceptions import handle_exception
from backend.schemas import TokenResponse
from backend.security import create_access_token, verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
@handle_exception(logger)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenResponse:
    """Issue a JWT access token for valid admin credentials.

    Accepts an OAuth2 password-grant form body and returns a bearer token
    when the supplied username and password match the configured admin account.

    Args:
        form_data: OAuth2 password form containing ``username`` and ``password``.

    Returns:
        A TokenResponse with the signed access token and token type.

    Raises:
        HTTPException: 401 if the credentials are incorrect.
    """
    # Always run bcrypt regardless of username match to prevent timing-based
    # username enumeration (wrong-username path must be indistinguishable in
    # duration from wrong-password path).
    username_ok = form_data.username == settings.admin_username
    password_ok = verify_password(form_data.password, settings.admin_password_hash)
    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(subject=form_data.username)
    return TokenResponse(access_token=token)
