# Google OAuth2 Social Login Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded admin user with Google OAuth2 social login, persist user profiles in a `users` table, and add a frontend Users page and auth-aware UI.

**Architecture:** Backend-driven Authorization Code Flow — the Vue SPA triggers a top-level navigation to `/auth/google/login`, Google redirects back to the FastAPI callback which exchanges the code server-side, upserts the user in PostgreSQL, issues a project JWT (with `name` claim added), and redirects the browser to `/auth/callback?token=<jwt>`. The frontend stores the token in localStorage under `'access_token'` and uses a `useAuth` composable backed by a Vue `ref` as the single source of truth for auth state.

**Tech Stack:** FastAPI (sync `def` handlers), SQLAlchemy 2.0, Alembic, httpx (sync mode), python-jose, pytest + testcontainers + pytest-env, Vue 3 Composition API, Vue Router 4, Vitest, `@playwright/test`

---

## Chunk 1: Backend Foundation

### Task 1: Add pytest-env and update pyproject.toml + config.py

**Files:**
- Modify: `pyproject.toml`
- Modify: `backend/config.py`

- [ ] **Step 1: Add pytest-env dev dependency**

```bash
poetry add --group dev pytest-env
```

Expected: `pytest-env` added to `[tool.poetry.group.dev.dependencies]` in `pyproject.toml`.

- [ ] **Step 2: Add env setting to pytest config in pyproject.toml**

Open `pyproject.toml`, find `[tool.pytest.ini_options]`, and **append only the `env` key** to the existing block — do not replace `testpaths`, `addopts`, or `markers`:

```toml
env = ["ENABLE_PASSWORD_AUTH=true"]
```

The section should end up looking like:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --ignore=tests/perf --ignore=tests/e2e"
markers = [
    "perf: performance/timing tests (run with: just backend-perf)",
    "e2e: end-to-end tests against a live running stack (run with: just backend-e2e)",
]
env = ["ENABLE_PASSWORD_AUTH=true"]
```

- [ ] **Step 3: Update backend/config.py**

Open `backend/config.py`. The current `Settings` class has `admin_password_hash: str` (required, no default). Update it and add the new fields:

```python
"""Application configuration loaded from environment variables and .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    loki_url: str | None = None
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    admin_username: str = "admin"
    admin_password_hash: str = ""          # optional — only needed when enable_password_auth=True
    google_client_id: str = ""             # optional — only needed at runtime for Google endpoints
    google_client_secret: str = ""         # optional — only needed at runtime for Google endpoints
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    enable_password_auth: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()  # pyright: ignore[reportCallIssue]
```

- [ ] **Step 4: Verify the existing test suite still passes**

```bash
just backend-test
```

Expected: All existing tests pass. The `ENABLE_PASSWORD_AUTH=true` env var (set by `pytest-env`) ensures `/auth/token` is registered so the `auth_token` fixture in `conftest.py` continues to work.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml backend/config.py
git commit -m "chore(config): add pytest-env, make admin hash optional, add Google OAuth settings"
```

---

### Task 2: Add User ORM model to backend/models.py

**Files:**
- Modify: `backend/models.py`
- Test: `tests/test_users.py` (new file)

- [ ] **Step 1: Write a failing test that imports and queries User**

Create `tests/test_users.py`:

```python
"""Tests for user persistence and the /users endpoints."""

import allure
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models import User


@allure.feature("Users")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Model")  # pyright: ignore[reportUnknownMemberType]
class TestUserModel:
    def test_user_can_be_inserted_and_retrieved(self, db_session: Session) -> None:
        user = User(
            google_id="google-123",
            email="alice@example.com",
            name="Alice",
            picture="https://example.com/alice.jpg",
        )
        db_session.add(user)
        db_session.flush()

        fetched = db_session.get(User, user.id)
        assert fetched is not None
        assert fetched.email == "alice@example.com"
        assert fetched.google_id == "google-123"
        assert fetched.name == "Alice"
        assert fetched.picture == "https://example.com/alice.jpg"
        assert fetched.created_at is not None

    def test_google_id_is_unique(self, db_session: Session) -> None:
        db_session.add(User(google_id="dup-id", email="a@example.com", name="A"))
        db_session.flush()

        with pytest.raises(Exception):
            db_session.add(User(google_id="dup-id", email="b@example.com", name="B"))
            db_session.flush()

    def test_email_is_unique(self, db_session: Session) -> None:
        db_session.add(User(google_id="id-1", email="same@example.com", name="A"))
        db_session.flush()

        with pytest.raises(Exception):
            db_session.add(User(google_id="id-2", email="same@example.com", name="B"))
            db_session.flush()
```

- [ ] **Step 2: Run test to confirm it fails (User not importable)**

```bash
.venv/bin/pytest tests/test_users.py -v
```

Expected: `ImportError` — `cannot import name 'User' from 'backend.models'`.

- [ ] **Step 3: Add User model to backend/models.py**

Open `backend/models.py`. `Base` is imported from `backend.database` — do **not** add a new `Base` definition. Append the `User` class at the end of the file (after `Sequence`). Add any missing imports (`String` may already be present; `unique=True` does not need a new import):

```python
class User(Base):
    """Persisted Google account — created or updated on each OAuth login."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    google_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    picture: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
```

`Base`, `Integer`, `String`, `DateTime`, `func`, `Mapped`, `mapped_column`, and `datetime` are already imported in the file — only add imports for anything that is missing after reading the current file.

- [ ] **Step 4: Generate the Alembic migration**

```bash
just makemigrations "add users table"
```

Expected: A new file created in `alembic/versions/` containing `op.create_table('users', ...)`.

- [ ] **Step 5: Run tests — they should now pass**

```bash
.venv/bin/pytest tests/test_users.py -v
```

Expected: 3 tests pass. The `engine` fixture in `conftest.py` applies the new migration via `command.upgrade(alembic_cfg, "head")` so the `users` table exists.

- [ ] **Step 6: Commit**

```bash
git add backend/models.py tests/test_users.py alembic/versions/
git commit -m "feat(users): add User ORM model and Alembic migration"
```

---

### Task 3: Add UserResponse schema and update security.py for extra JWT claims

**Files:**
- Modify: `backend/schemas.py`
- Modify: `backend/security.py`
- Test: existing `tests/test_auth.py` (verify no regression)

- [ ] **Step 1: Add UserResponse to backend/schemas.py**

Open `backend/schemas.py` and **append only** the following class at the end of the file — do not alter the existing `TokenResponse`, `SequenceCreate`, `SequenceUpdate`, or `SequenceResponse` classes:

```python
class UserResponse(BaseModel):
    """User profile as returned by the API — used for both /users/ list and /users/me."""

    id: int
    email: str
    name: str
    picture: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

`datetime`, `BaseModel`, and `ConfigDict` are already imported in `schemas.py` — no new imports needed.

- [ ] **Step 2: Update create_access_token in backend/security.py to accept extra claims**

Open `backend/security.py`. The file currently uses `datetime.now(timezone.utc)` (not `UTC`). Find `create_access_token` and update its signature to support optional extra claims (used to embed `name` in the Google-issued JWT). Keep the existing `timezone.utc` style — do not change the import:

```python
def create_access_token(subject: str, extra_claims: dict[str, str] | None = None) -> str:
    """Create a signed JWT access token.

    Args:
        subject: The JWT ``sub`` claim — the authenticated user's email or username.
        extra_claims: Optional additional claims to include in the payload (e.g. ``name``).

    Returns:
        A signed JWT string.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, object] = {"sub": subject, "exp": expire}
    if extra_claims:
        payload.update(extra_claims)
    return str(jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm))
```

All existing callers pass only `subject=` so this is backward-compatible. No import changes needed. The `str()` wrapper is required to satisfy basedpyright strict mode — preserve it from the existing code.

- [ ] **Step 3: Run existing auth tests to confirm no regression**

```bash
.venv/bin/pytest tests/test_auth.py -v
```

Expected: All existing auth tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/schemas.py backend/security.py
git commit -m "feat(schemas): add UserResponse DTO and extra_claims support in create_access_token"
```

---

## Chunk 2: Backend OAuth2 + Users Endpoints

### Task 4: Create backend/google_oauth.py

**Files:**
- Create: `backend/google_oauth.py`
- Create: `tests/test_google_oauth.py`

- [ ] **Step 1: Write failing tests for google_oauth.py**

Create `tests/test_google_oauth.py`:

```python
"""Unit tests for Google OAuth2 helpers in backend/google_oauth.py.

These tests do not touch the database — they test pure functions and mock
all outbound HTTP calls.
"""

import time
from unittest.mock import MagicMock, patch

import allure
import pytest
from fastapi import HTTPException

from backend.google_oauth import (
    GoogleUserInfo,
    _STATE_TTL_SECONDS,
    _state_store,
    build_google_redirect_url,
    exchange_code_for_tokens,
    fetch_google_user_info,
    generate_state,
    validate_and_consume_state,
)


@allure.feature("Google OAuth2")  # pyright: ignore[reportUnknownMemberType]
@allure.story("State Management")  # pyright: ignore[reportUnknownMemberType]
class TestStateManagement:
    def setup_method(self) -> None:
        """Clear the state store before each test."""
        _state_store.clear()

    def test_generate_state_returns_unique_tokens(self) -> None:
        s1 = generate_state()
        s2 = generate_state()
        assert s1 != s2
        assert len(s1) > 16

    def test_generate_state_stores_timestamp(self) -> None:
        before = time.monotonic()
        state = generate_state()
        after = time.monotonic()
        assert state in _state_store
        assert before <= _state_store[state] <= after

    def test_validate_and_consume_state_removes_state(self) -> None:
        state = generate_state()
        validate_and_consume_state(state)
        assert state not in _state_store

    def test_validate_and_consume_state_raises_on_unknown(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            validate_and_consume_state("not-a-real-state")
        assert exc_info.value.status_code == 400

    def test_validate_and_consume_state_raises_on_expired(self) -> None:
        state = generate_state()
        # Backdate the timestamp so the state appears expired
        _state_store[state] = time.monotonic() - _STATE_TTL_SECONDS - 1
        with pytest.raises(HTTPException) as exc_info:
            validate_and_consume_state(state)
        assert exc_info.value.status_code == 400


@allure.feature("Google OAuth2")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Google API Helpers")  # pyright: ignore[reportUnknownMemberType]
class TestGoogleApiHelpers:
    def test_build_google_redirect_url_contains_required_params(self) -> None:
        url = build_google_redirect_url("test-state-abc")
        assert "accounts.google.com" in url
        assert "response_type=code" in url
        assert "state=test-state-abc" in url
        assert "scope=" in url
        assert "email" in url
        assert "profile" in url

    def test_exchange_code_for_tokens_calls_google_endpoint(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "goog-tok", "token_type": "Bearer"}
        mock_response.raise_for_status = MagicMock()

        with patch("backend.google_oauth.httpx.post", return_value=mock_response) as mock_post:
            result = exchange_code_for_tokens("auth-code-123")

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "oauth2.googleapis.com/token" in call_kwargs[0][0]
        assert result["access_token"] == "goog-tok"

    def test_fetch_google_user_info_returns_parsed_profile(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "sub": "google-uid-999",
            "email": "bob@example.com",
            "name": "Bob",
            "picture": "https://example.com/bob.jpg",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("backend.google_oauth.httpx.get", return_value=mock_response):
            info = fetch_google_user_info("some-access-token")

        assert isinstance(info, GoogleUserInfo)
        assert info.google_id == "google-uid-999"
        assert info.email == "bob@example.com"
        assert info.name == "Bob"
        assert info.picture == "https://example.com/bob.jpg"

    def test_fetch_google_user_info_handles_missing_picture(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "sub": "google-uid-000",
            "email": "nopic@example.com",
            "name": "No Pic",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("backend.google_oauth.httpx.get", return_value=mock_response):
            info = fetch_google_user_info("token")

        assert info.picture is None
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
.venv/bin/pytest tests/test_google_oauth.py -v
```

Expected: `ModuleNotFoundError: No module named 'backend.google_oauth'`.

- [ ] **Step 3: Create backend/google_oauth.py**

```python
"""Google OAuth2 Authorization Code Flow helpers.

All httpx calls use the synchronous API (httpx.post / httpx.get) to match
the project's sync-first architecture (FastAPI def handlers).

State store note: uses an in-memory dict — requires single-worker deployment.
States are cleaned up on validation; no background cleanup is performed.
"""

import time
import urllib.parse
from dataclasses import dataclass

import httpx
from fastapi import HTTPException

from backend.config import settings

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

_STATE_TTL_SECONDS = 600  # 10 minutes

# Maps state token → monotonic timestamp of creation.
# POC only: in-memory, not safe under multi-worker deployments.
_state_store: dict[str, float] = {}


@dataclass
class GoogleUserInfo:
    """Parsed Google userinfo API response."""

    google_id: str
    email: str
    name: str
    picture: str | None


def generate_state() -> str:
    """Generate a CSRF state token and register it in the store.

    Returns:
        A URL-safe random string to use as the OAuth ``state`` parameter.
    """
    import secrets

    state = secrets.token_urlsafe(32)
    _state_store[state] = time.monotonic()
    return state


def validate_and_consume_state(state: str) -> None:
    """Validate and remove a state token from the store.

    Args:
        state: The ``state`` query parameter received in the OAuth callback.

    Raises:
        HTTPException: 400 if the state is unknown or expired.
    """
    ts = _state_store.pop(state, None)
    if ts is None or (time.monotonic() - ts) > _STATE_TTL_SECONDS:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")


def build_google_redirect_url(state: str) -> str:
    """Build the Google OAuth2 authorization URL.

    Args:
        state: A CSRF state token generated by :func:`generate_state`.

    Returns:
        The full Google consent screen URL to redirect the browser to.
    """
    redirect_uri = f"{settings.backend_url}/auth/google/callback"
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
    }
    return f"{_GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


def exchange_code_for_tokens(code: str) -> dict[str, str]:
    """Exchange an authorization code for Google tokens.

    Args:
        code: The ``code`` query parameter received in the OAuth callback.

    Returns:
        The Google token response dict (contains ``access_token`` at minimum).

    Raises:
        httpx.HTTPStatusError: If Google returns an error response.
    """
    redirect_uri = f"{settings.backend_url}/auth/google/callback"
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
    return dict(response.json())


def fetch_google_user_info(access_token: str) -> GoogleUserInfo:
    """Fetch the authenticated user's profile from Google.

    Args:
        access_token: A Google OAuth2 access token.

    Returns:
        Parsed :class:`GoogleUserInfo` with the user's Google ID, email, name, and picture.

    Raises:
        httpx.HTTPStatusError: If Google returns an error response.
    """
    response = httpx.get(
        _GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    response.raise_for_status()
    data: dict[str, object] = response.json()
    return GoogleUserInfo(
        google_id=str(data["sub"]),
        email=str(data["email"]),
        name=str(data["name"]),
        picture=str(data["picture"]) if "picture" in data else None,
    )
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
.venv/bin/pytest tests/test_google_oauth.py -v
```

Expected: All 9 tests pass.

- [ ] **Step 5: Run type checker**

```bash
.venv/bin/basedpyright backend/google_oauth.py
```

Expected: 0 errors.

- [ ] **Step 6: Commit**

```bash
git add backend/google_oauth.py tests/test_google_oauth.py
git commit -m "feat(oauth): add Google OAuth2 helpers with state management"
```

---

### Task 5: Create backend/user_routes.py — OAuth endpoints

**Files:**
- Create: `backend/user_routes.py`
- Modify: `tests/test_users.py` (add OAuth endpoint tests)

- [ ] **Step 1: Write failing tests for the OAuth endpoints**

Add to `tests/test_users.py` (after the existing `TestUserModel` class):

```python
import re
from unittest.mock import MagicMock, patch

from backend.google_oauth import GoogleUserInfo


@allure.feature("Users")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Google Login Redirect")  # pyright: ignore[reportUnknownMemberType]
class TestGoogleLogin:
    def test_login_redirects_to_google(self, client: TestClient) -> None:
        response = client.get("/auth/google/login", follow_redirects=False)
        assert response.status_code == 307
        location = response.headers["location"]
        assert "accounts.google.com" in location
        assert "state=" in location
        assert "response_type=code" in location

    def test_login_includes_required_scopes(self, client: TestClient) -> None:
        response = client.get("/auth/google/login", follow_redirects=False)
        location = response.headers["location"]
        assert "email" in location
        assert "profile" in location


@allure.feature("Users")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Google OAuth Callback")  # pyright: ignore[reportUnknownMemberType]
class TestGoogleCallback:
    def setup_method(self) -> None:
        """Clear the OAuth state store before each test to prevent cross-test leakage."""
        from backend.google_oauth import _state_store
        _state_store.clear()

    def _make_mock_google(
        self,
        google_id: str = "gid-1",
        email: str = "alice@example.com",
        name: str = "Alice",
        picture: str | None = "https://img.example.com/alice.jpg",
    ) -> MagicMock:
        """Return a mock that replaces exchange_code_for_tokens + fetch_google_user_info."""
        mock = MagicMock()
        mock.exchange.return_value = {"access_token": "fake-goog-token"}
        mock.userinfo.return_value = GoogleUserInfo(
            google_id=google_id, email=email, name=name, picture=picture
        )
        return mock

    def test_callback_creates_user_and_redirects_with_jwt(
        self, client: TestClient, db_session: Session
    ) -> None:
        from backend.google_oauth import generate_state

        state = generate_state()
        mock = self._make_mock_google()

        with (
            patch("backend.user_routes.exchange_code_for_tokens", mock.exchange),
            patch("backend.user_routes.fetch_google_user_info", mock.userinfo),
        ):
            response = client.get(
                f"/auth/google/callback?code=test-code&state={state}",
                follow_redirects=False,
            )

        assert response.status_code in (302, 307)
        location = response.headers["location"]
        assert "auth/callback" in location
        assert "token=" in location

        # Verify user was persisted in DB
        from sqlalchemy import select
        from backend.models import User

        user = db_session.execute(
            select(User).where(User.email == "alice@example.com")
        ).scalar_one_or_none()
        assert user is not None
        assert user.google_id == "gid-1"
        assert user.name == "Alice"

    def test_callback_updates_existing_user_profile(
        self, client: TestClient, db_session: Session
    ) -> None:
        from sqlalchemy import select
        from backend.google_oauth import generate_state
        from backend.models import User

        # Pre-seed an existing user
        db_session.add(
            User(
                google_id="gid-update",
                email="bob@example.com",
                name="Old Name",
                picture=None,
            )
        )
        db_session.flush()

        state = generate_state()
        mock = self._make_mock_google(
            google_id="gid-update",
            email="bob@example.com",
            name="New Name",
            picture="https://img.example.com/bob.jpg",
        )

        with (
            patch("backend.user_routes.exchange_code_for_tokens", mock.exchange),
            patch("backend.user_routes.fetch_google_user_info", mock.userinfo),
        ):
            response = client.get(
                f"/auth/google/callback?code=code&state={state}",
                follow_redirects=False,
            )

        assert response.status_code in (302, 307)
        db_session.expire_all()
        user = db_session.execute(
            select(User).where(User.email == "bob@example.com")
        ).scalar_one()
        assert user.name == "New Name"
        assert user.picture == "https://img.example.com/bob.jpg"

    def test_callback_rejects_invalid_state(self, client: TestClient) -> None:
        response = client.get(
            "/auth/google/callback?code=some-code&state=invalid-state",
            follow_redirects=False,
        )
        assert response.status_code == 400

    def test_callback_rejects_expired_state(self, client: TestClient) -> None:
        from backend.google_oauth import _STATE_TTL_SECONDS, _state_store, generate_state

        state = generate_state()
        _state_store[state] = _state_store[state] - _STATE_TTL_SECONDS - 1

        response = client.get(
            f"/auth/google/callback?code=code&state={state}",
            follow_redirects=False,
        )
        assert response.status_code == 400
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
.venv/bin/pytest tests/test_users.py::TestGoogleLogin tests/test_users.py::TestGoogleCallback -v
```

Expected: `404 Not Found` for all OAuth endpoint tests (routes not yet registered).

- [ ] **Step 3: Create backend/user_routes.py**

```python
"""User management and Google OAuth2 routes."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
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
def google_callback(code: str, state: str, session: SessionDep) -> RedirectResponse:
    """Handle Google's OAuth2 callback, upsert the user, and issue a JWT.

    Args:
        code: The authorization code from Google.
        state: The CSRF state token to validate.
        session: The database session.

    Returns:
        A redirect to the frontend /auth/callback page with the JWT in ``?token=``.

    Raises:
        HTTPException: 400 if the state is invalid or expired.
    """
    validate_and_consume_state(state)
    tokens = exchange_code_for_tokens(code)
    user_info = fetch_google_user_info(tokens["access_token"])

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
    else:
        existing.name = user_info.name
        existing.picture = user_info.picture

    session.commit()

    jwt_token = create_access_token(
        subject=user_info.email,
        extra_claims={"name": user_info.name},
    )
    frontend_callback = f"{settings.frontend_url}/auth/callback?token={jwt_token}"
    return RedirectResponse(url=frontend_callback)


@router.get("/users/", response_model=list[UserResponse])
@handle_exception(logger)
def list_users(session: SessionDep) -> list[User]:
    """Return all users who have logged in, most recent first.

    Returns:
        A list of :class:`UserResponse` objects.
    """
    return list(session.execute(select(User).order_by(User.created_at.desc())).scalars())


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
```

- [ ] **Step 4: Register user_router in backend/main.py**

Open `backend/main.py`. Make two changes:

**1. Remove the module-level auth_routes import AND include.** The file currently has both a top-level import and an include call — remove both lines:

```python
# DELETE these two lines (they may not be adjacent):
from backend.auth_routes import router as auth_router   # ← remove this import
app.include_router(auth_router)                         # ← remove this include
```

**2. Add the user router unconditionally and the auth router conditionally.** Add these lines in the same location (after the existing `from backend.routes import router` and `app.include_router(router)` calls):

```python
from backend.user_routes import router as user_router

app.include_router(user_router)

if settings.enable_password_auth:
    from backend.auth_routes import router as auth_router
    app.include_router(auth_router)
```

Moving the `auth_routes` import inside the `if` block is intentional — it ensures the import (and thus the router registration) only happens when the setting is enabled.

- [ ] **Step 5: Run the OAuth endpoint tests**

```bash
.venv/bin/pytest tests/test_users.py -v
```

Expected: All tests pass.

- [ ] **Step 6: Run the full backend test suite to confirm no regressions**

```bash
just backend-test
```

Expected: All tests pass (the `auth_token` fixture still works because `pytest-env` sets `ENABLE_PASSWORD_AUTH=true`).

- [ ] **Step 7: Run type checker**

```bash
.venv/bin/basedpyright backend/user_routes.py backend/main.py
```

Expected: 0 errors.

- [ ] **Step 8: Run linter**

```bash
just backend-check
```

Expected: 0 ruff errors.

- [ ] **Step 9: Commit**

```bash
git add backend/user_routes.py backend/main.py tests/test_users.py
git commit -m "feat(users): add Google OAuth2 endpoints and user management routes"
```

---

### Task 6: Add /users/ and /users/me tests

**Files:**
- Modify: `tests/test_users.py` (add endpoint tests)

- [ ] **Step 1: Write failing tests for /users/ and /users/me**

Add to `tests/test_users.py` (after `TestGoogleCallback`):

```python
@allure.feature("Users")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Users List")  # pyright: ignore[reportUnknownMemberType]
class TestUsersList:
    def test_list_users_returns_empty_list_by_default(self, client: TestClient) -> None:
        response = client.get("/users/")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_users_returns_seeded_users(
        self, client: TestClient, db_session: Session
    ) -> None:
        from backend.models import User

        db_session.add(User(google_id="g1", email="a@test.com", name="Alice", picture=None))
        db_session.add(User(google_id="g2", email="b@test.com", name="Bob", picture=None))
        db_session.flush()

        response = client.get("/users/")
        assert response.status_code == 200
        emails = [u["email"] for u in response.json()]
        assert "a@test.com" in emails
        assert "b@test.com" in emails

    def test_list_users_is_public(self, client: TestClient) -> None:
        """No auth required for the users list."""
        response = client.get("/users/")
        assert response.status_code == 200


@allure.feature("Users")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Users Me")  # pyright: ignore[reportUnknownMemberType]
class TestUsersMe:
    def test_me_returns_own_profile(
        self, client: TestClient, db_session: Session, auth_token: str
    ) -> None:
        """Seed a User row matching the admin JWT subject, then call /users/me."""
        from backend.models import User

        # admin_username defaults to "admin" — this matches the JWT subject
        # issued by POST /auth/token (subject=form_data.username)
        db_session.add(
            User(google_id="g-admin", email="admin", name="Admin User", picture=None)
        )
        db_session.flush()

        response = client.get(
            "/users/me", headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin"
        assert data["name"] == "Admin User"

    def test_me_requires_authentication(self, client: TestClient) -> None:
        response = client.get("/users/me")
        assert response.status_code == 401

    def test_me_returns_404_when_user_not_in_db(
        self, client: TestClient, auth_token: str
    ) -> None:
        """JWT is valid but no User row exists — 404."""
        response = client.get(
            "/users/me", headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404
```

- [ ] **Step 2: Run all user tests**

```bash
.venv/bin/pytest tests/test_users.py -v
```

Expected: All tests pass.

- [ ] **Step 3: Run linter and type checker**

```bash
just backend-check
```

Expected: 0 ruff errors, 0 basedpyright errors.

- [ ] **Step 4: Commit**

```bash
git add tests/test_users.py
git commit -m "test(users): add /users/ and /users/me endpoint tests"
```

---

## Chunk 3: Frontend Auth + Users + E2E

### Task 7: Create useAuth composable

**Files:**
- Create: `frontend/src/composables/useAuth.ts`
- Create: `frontend/src/__tests__/composables.useAuth.test.ts`

- [ ] **Step 1: Write failing Vitest tests for useAuth**

Create `frontend/src/__tests__/composables.useAuth.test.ts`:

```typescript
import { beforeEach, describe, expect, it, vi } from 'vitest'

// Mock vue-router before importing useAuth
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

// Provide a minimal localStorage mock
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} },
  }
})()
Object.defineProperty(global, 'localStorage', { value: localStorageMock })

// A JWT that expires far in the future (exp: year 2099)
// Payload: { sub: "alice@example.com", name: "Alice", exp: 4070908800 }
const VALID_TOKEN =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  btoa(JSON.stringify({ sub: 'alice@example.com', name: 'Alice', exp: 4070908800 }))
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_') +
  '.fake-signature'

// A JWT that expired in the past (exp: year 2000)
const EXPIRED_TOKEN =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  btoa(JSON.stringify({ sub: 'old@example.com', name: 'Old', exp: 946684800 }))
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_') +
  '.fake-signature'

describe('useAuth', () => {
  beforeEach(() => {
    localStorageMock.clear()
    vi.resetModules()
  })

  it('isAuthenticated is false when localStorage is empty', async () => {
    const { useAuth } = await import('../composables/useAuth')
    const { isAuthenticated } = useAuth()
    expect(isAuthenticated.value).toBe(false)
  })

  it('isAuthenticated is true after setToken with valid JWT', async () => {
    const { useAuth } = await import('../composables/useAuth')
    const { isAuthenticated, setToken } = useAuth()
    setToken(VALID_TOKEN)
    expect(isAuthenticated.value).toBe(true)
  })

  it('isAuthenticated is false for an expired JWT', async () => {
    localStorageMock.setItem('access_token', EXPIRED_TOKEN)
    const { useAuth } = await import('../composables/useAuth')
    const { isAuthenticated } = useAuth()
    expect(isAuthenticated.value).toBe(false)
  })

  it('user returns decoded email and name from JWT', async () => {
    const { useAuth } = await import('../composables/useAuth')
    const { user, setToken } = useAuth()
    setToken(VALID_TOKEN)
    expect(user.value?.email).toBe('alice@example.com')
    expect(user.value?.name).toBe('Alice')
  })

  it('user is null when not authenticated', async () => {
    const { useAuth } = await import('../composables/useAuth')
    const { user } = useAuth()
    expect(user.value).toBeNull()
  })

  it('logout clears token and localStorage', async () => {
    localStorageMock.setItem('access_token', VALID_TOKEN)
    const { useAuth } = await import('../composables/useAuth')
    const { isAuthenticated, logout } = useAuth()
    expect(isAuthenticated.value).toBe(true)
    logout()
    expect(isAuthenticated.value).toBe(false)
    expect(localStorageMock.getItem('access_token')).toBeNull()
  })

  it('setToken persists token to localStorage', async () => {
    const { useAuth } = await import('../composables/useAuth')
    const { setToken } = useAuth()
    setToken(VALID_TOKEN)
    expect(localStorageMock.getItem('access_token')).toBe(VALID_TOKEN)
  })
})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd frontend && npx vitest run src/__tests__/composables.useAuth.test.ts
```

Expected: `Error: Cannot find module '../composables/useAuth'`.

- [ ] **Step 3: Create frontend/src/composables/useAuth.ts**

```typescript
/**
 * useAuth — single source of truth for authentication state.
 *
 * Backed by a Vue ref so that setToken() and logout() trigger reactive updates
 * immediately without needing to re-mount components or re-read localStorage.
 *
 * The localStorage key 'access_token' matches the existing api/sequences.ts client.
 */

import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

const STORAGE_KEY = 'access_token'

interface JwtPayload {
  sub: string
  name?: string
  exp: number
}

function decodePayload(token: string): JwtPayload | null {
  try {
    const payloadB64 = token.split('.')[1]
    if (!payloadB64) return null
    // Real JWTs use base64url encoding (- and _ instead of + and /).
    // atob() requires standard base64 — normalise before decoding.
    const standardB64 = payloadB64.replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(atob(standardB64)) as JwtPayload
  } catch {
    return null
  }
}

// Module-level ref — shared across all useAuth() calls in a component tree.
const _token = ref<string | null>(localStorage.getItem(STORAGE_KEY))

export function useAuth() {
  const router = useRouter()

  const token = computed(() => _token.value)

  const isAuthenticated = computed<boolean>(() => {
    if (!_token.value) return false
    const payload = decodePayload(_token.value)
    if (!payload) return false
    return payload.exp * 1000 > Date.now()
  })

  const user = computed<{ email: string; name: string } | null>(() => {
    if (!_token.value) return null
    const payload = decodePayload(_token.value)
    if (!payload) return null
    return {
      email: payload.sub,
      name: payload.name ?? payload.sub,
    }
  })

  function setToken(t: string): void {
    localStorage.setItem(STORAGE_KEY, t)
    _token.value = t
  }

  function login(): void {
    void router.push('/login')
  }

  function logout(): void {
    localStorage.removeItem(STORAGE_KEY)
    _token.value = null
    void router.push('/')
  }

  return { token, isAuthenticated, user, setToken, login, logout }
}
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd frontend && npx vitest run src/__tests__/composables.useAuth.test.ts
```

Expected: All 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/composables/useAuth.ts frontend/src/__tests__/composables.useAuth.test.ts
git commit -m "feat(frontend): add useAuth composable with ref-backed localStorage state"
```

---

### Task 8: Create LoginView.vue and AuthCallbackView.vue

**Files:**
- Create: `frontend/src/views/LoginView.vue`
- Create: `frontend/src/views/AuthCallbackView.vue`
- Create: `frontend/src/__tests__/LoginView.test.ts`
- Create: `frontend/src/__tests__/AuthCallbackView.test.ts`

- [ ] **Step 1: Write failing Vitest test for LoginView**

Create `frontend/src/__tests__/LoginView.test.ts`:

```typescript
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import LoginView from '../views/LoginView.vue'

describe('LoginView', () => {
  it('renders a sign-in button', () => {
    const wrapper = mount(LoginView, {
      global: { stubs: { RouterLink: true } },
    })
    expect(wrapper.text()).toContain('Sign in with Google')
  })

  it('sign-in button links to /auth/google/login', () => {
    const wrapper = mount(LoginView, {
      global: { stubs: { RouterLink: true } },
    })
    const link = wrapper.find('a[href="/auth/google/login"]')
    expect(link.exists()).toBe(true)
  })
})
```

- [ ] **Step 2: Write failing Vitest test for AuthCallbackView**

Create `frontend/src/__tests__/AuthCallbackView.test.ts`:

```typescript
import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'
import AuthCallbackView from '../views/AuthCallbackView.vue'

const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} },
  }
})()
Object.defineProperty(global, 'localStorage', { value: localStorageMock })

describe('AuthCallbackView', () => {
  beforeEach(() => {
    localStorageMock.clear()
    vi.resetModules()
  })

  it('stores token from URL in localStorage and navigates to /', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/auth/callback', component: AuthCallbackView },
        { path: '/', component: { template: '<div>home</div>' } },
      ],
    })
    await router.push('/auth/callback?token=test-jwt-token')

    mount(AuthCallbackView, {
      global: { plugins: [router] },
    })
    await flushPromises()

    expect(localStorageMock.getItem('access_token')).toBe('test-jwt-token')
    expect(router.currentRoute.value.path).toBe('/')
  })

  it('navigates to / even when no token is present', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/auth/callback', component: AuthCallbackView },
        { path: '/', component: { template: '<div>home</div>' } },
      ],
    })
    await router.push('/auth/callback')

    mount(AuthCallbackView, {
      global: { plugins: [router] },
    })
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/')
  })
})
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
cd frontend && npx vitest run src/__tests__/LoginView.test.ts src/__tests__/AuthCallbackView.test.ts
```

Expected: `Cannot find module '../views/LoginView.vue'` and similar.

- [ ] **Step 4: Create frontend/src/views/LoginView.vue**

```vue
<template>
  <div class="login-page">
    <div class="login-card">
      <h1 class="login-title">Welcome</h1>
      <p class="login-subtitle">Sign in to manage sequences</p>
      <a href="/auth/google/login" class="login-button">
        Sign in with Google
      </a>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}

.login-card {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 2.5rem 3rem;
  text-align: center;
  max-width: 380px;
  width: 100%;
}

.login-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #f8fafc;
  margin-bottom: 0.5rem;
}

.login-subtitle {
  color: #94a3b8;
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
}

.login-button {
  display: inline-block;
  background: #3b82f6;
  color: #fff;
  padding: 0.625rem 1.5rem;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  text-decoration: none;
  transition: background 0.15s;
}

.login-button:hover {
  background: #2563eb;
}
</style>
```

- [ ] **Step 5: Create frontend/src/views/AuthCallbackView.vue**

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const route = useRoute()
const router = useRouter()
const { setToken } = useAuth()

onMounted(() => {
  const token = route.query.token
  if (typeof token === 'string' && token.length > 0) {
    setToken(token)
  }
  void router.push('/')
})
</script>

<template>
  <div class="callback-page">
    <p>Signing you in…</p>
  </div>
</template>

<style scoped>
.callback-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  color: #94a3b8;
}
</style>
```

- [ ] **Step 6: Run tests to confirm they pass**

```bash
cd frontend && npx vitest run src/__tests__/LoginView.test.ts src/__tests__/AuthCallbackView.test.ts
```

Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/views/LoginView.vue frontend/src/views/AuthCallbackView.vue \
        frontend/src/__tests__/LoginView.test.ts frontend/src/__tests__/AuthCallbackView.test.ts
git commit -m "feat(frontend): add LoginView and AuthCallbackView"
```

---

### Task 9: Create frontend/src/api/users.ts and UsersView.vue

**Files:**
- Create: `frontend/src/api/users.ts`
- Create: `frontend/src/views/UsersView.vue`
- Create: `frontend/src/__tests__/UsersView.test.ts`

- [ ] **Step 1: Create frontend/src/api/users.ts**

```typescript
export interface User {
  id: number
  email: string
  name: string
  picture: string | null
  created_at: string
}

const BASE_URL = '/users'

async function request<T>(url: string): Promise<T> {
  const response = await fetch(url)
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error((detail as { detail?: string }).detail ?? response.statusText)
  }
  return response.json() as Promise<T>
}

export const usersApi = {
  list(): Promise<User[]> {
    return request<User[]>(BASE_URL + '/')
  },
}
```

- [ ] **Step 2: Write failing Vitest test for UsersView**

Create `frontend/src/__tests__/UsersView.test.ts`:

```typescript
import { mount, flushPromises } from '@vue/test-utils'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import UsersView from '../views/UsersView.vue'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

const mockUsers = [
  { id: 1, email: 'alice@example.com', name: 'Alice', picture: null, created_at: '2026-01-01T00:00:00Z' },
  { id: 2, email: 'bob@example.com', name: 'Bob', picture: 'https://img.example.com/bob.jpg', created_at: '2026-01-02T00:00:00Z' },
]

describe('UsersView', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('renders a list of users after loading', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => mockUsers,
    } as Response)

    const wrapper = mount(UsersView)
    await flushPromises()

    expect(wrapper.text()).toContain('Alice')
    expect(wrapper.text()).toContain('alice@example.com')
    expect(wrapper.text()).toContain('Bob')
  })

  it('shows a loading state initially', () => {
    vi.spyOn(global, 'fetch').mockImplementation(() => new Promise(() => {}))
    const wrapper = mount(UsersView)
    expect(wrapper.text()).toContain('Loading')
  })

  it('shows an error message when the fetch fails', async () => {
    vi.spyOn(global, 'fetch').mockRejectedValue(new Error('Network error'))
    const wrapper = mount(UsersView)
    await flushPromises()
    expect(wrapper.text()).toMatch(/error|failed/i)
  })
})
```

- [ ] **Step 3: Run test to confirm it fails**

```bash
cd frontend && npx vitest run src/__tests__/UsersView.test.ts
```

Expected: `Cannot find module '../views/UsersView.vue'`.

- [ ] **Step 4: Create frontend/src/views/UsersView.vue**

```vue
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { usersApi, type User } from '../api/users'
import { formatDate } from '../utils/date'

const users = ref<User[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    users.value = await usersApi.list()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load users'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="users-page">
    <h1 class="page-title">Users</h1>

    <p v-if="loading" class="state-message">Loading…</p>
    <p v-else-if="error" class="state-message state-message--error">{{ error }}</p>

    <table v-else class="users-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Email</th>
          <th>Joined</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="user in users" :key="user.id">
          <td class="user-name">
            <img
              v-if="user.picture"
              :src="user.picture"
              :alt="user.name"
              class="user-avatar"
            />
            <span v-else class="user-avatar user-avatar--placeholder">
              {{ user.name.charAt(0).toUpperCase() }}
            </span>
            {{ user.name }}
          </td>
          <td>{{ user.email }}</td>
          <td>{{ formatDate(user.created_at) }}</td>
        </tr>
        <tr v-if="users.length === 0">
          <td colspan="3" class="empty-state">No users have logged in yet.</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.users-page {
  padding: 1.5rem;
  max-width: 800px;
}

.page-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #f8fafc;
  margin-bottom: 1.25rem;
}

.state-message {
  color: #94a3b8;
  font-size: 0.875rem;
}

.state-message--error {
  color: #f87171;
}

.users-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.users-table th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  color: #94a3b8;
  border-bottom: 1px solid #334155;
  font-weight: 500;
}

.users-table td {
  padding: 0.625rem 0.75rem;
  border-bottom: 1px solid #1e293b;
  color: #e2e8f0;
  vertical-align: middle;
}

.user-name {
  display: flex;
  align-items: center;
  gap: 0.625rem;
}

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.user-avatar--placeholder {
  background: #3b82f6;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-state {
  color: #64748b;
  font-style: italic;
  text-align: center;
}
</style>
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
cd frontend && npx vitest run src/__tests__/UsersView.test.ts
```

Expected: All 3 tests pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/users.ts frontend/src/views/UsersView.vue \
        frontend/src/__tests__/UsersView.test.ts
git commit -m "feat(frontend): add UsersView and users API client"
```

---

### Task 10: Update Vue Router with new routes

**Files:**
- Modify: `frontend/src/router/index.ts`

- [ ] **Step 1: Add the three new routes to the router**

Open `frontend/src/router/index.ts` and update it:

```typescript
import { createRouter, createWebHistory } from 'vue-router'
import SequenceListView from '../views/SequenceListView.vue'
import SequenceDetailView from '../views/SequenceDetailView.vue'
import LoginView from '../views/LoginView.vue'
import AuthCallbackView from '../views/AuthCallbackView.vue'
import UsersView from '../views/UsersView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/sequences',
    },
    {
      path: '/sequences',
      name: 'sequences',
      component: SequenceListView,
    },
    {
      path: '/sequences/:id',
      name: 'sequence-detail',
      component: SequenceDetailView,
      props: (route) => ({ id: Number(route.params.id) }),
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
    },
    {
      path: '/auth/callback',
      name: 'auth-callback',
      component: AuthCallbackView,
    },
    {
      path: '/users',
      name: 'users',
      component: UsersView,
    },
  ],
})

export default router
```

- [ ] **Step 2: Run the frontend check to verify no TypeScript errors**

```bash
cd frontend && npx vue-tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/router/index.ts
git commit -m "feat(frontend): add login, auth-callback, and users routes"
```

---

### Task 11: Update AppNavbar with auth state and Users link

**Files:**
- Modify: `frontend/src/components/layout/AppNavbar.vue`

- [ ] **Step 1: Update AppNavbar.vue**

Open `frontend/src/components/layout/AppNavbar.vue` and replace the entire file:

```vue
<script setup lang="ts">
import { useAuth } from '../../composables/useAuth'

const { isAuthenticated, user, login, logout } = useAuth()
</script>

<template>
  <header class="navbar">
    <div class="navbar__brand">
      <RouterLink to="/sequences" class="navbar__logo">
        Sequence Manager
      </RouterLink>
    </div>
    <nav class="navbar__links">
      <RouterLink to="/sequences" class="navbar__link">Sequences</RouterLink>
      <RouterLink to="/users" class="navbar__link">Users</RouterLink>
    </nav>
    <div class="navbar__auth">
      <template v-if="isAuthenticated && user">
        <img
          v-if="false"
          class="navbar__avatar"
          alt="avatar"
        />
        <span class="navbar__user-email">{{ user.email }}</span>
        <button class="navbar__logout-btn" @click="logout">Logout</button>
      </template>
      <button v-else class="navbar__login-btn" @click="login">
        Sign in with Google
      </button>
    </div>
  </header>
</template>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.5rem;
  height: 56px;
  background: #1e293b;
  color: #f8fafc;
  border-bottom: 1px solid #334155;
  flex-shrink: 0;
}

.navbar__logo {
  font-size: 1.125rem;
  font-weight: 600;
  color: #f8fafc;
  text-decoration: none;
  letter-spacing: -0.01em;
}

.navbar__links {
  display: flex;
  gap: 1rem;
}

.navbar__link {
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.875rem;
  transition: color 0.15s;
}

.navbar__link:hover,
.navbar__link.router-link-active {
  color: #f8fafc;
}

.navbar__auth {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.navbar__user-email {
  font-size: 0.8125rem;
  color: #cbd5e1;
}

.navbar__login-btn,
.navbar__logout-btn {
  background: #3b82f6;
  color: #fff;
  border: none;
  border-radius: 5px;
  padding: 0.375rem 0.875rem;
  font-size: 0.8125rem;
  cursor: pointer;
  transition: background 0.15s;
}

.navbar__logout-btn {
  background: #475569;
}

.navbar__login-btn:hover {
  background: #2563eb;
}

.navbar__logout-btn:hover {
  background: #334155;
}
</style>
```

- [ ] **Step 2: Update SequenceListView.vue to hide write actions when not authenticated**

Open `frontend/src/views/SequenceListView.vue`. Find the template sections that contain the Create button and Edit/Delete buttons. Wrap them with `v-if="isAuthenticated"`.

Add the composable import inside `<script setup>`:

```typescript
import { useAuth } from '../composables/useAuth'
const { isAuthenticated } = useAuth()
```

Then in the template, locate the Create button (usually near the top of the view) and any Edit/Delete buttons in the table rows. Add `v-if="isAuthenticated"` to each:

```html
<!-- Example: Create button -->
<button v-if="isAuthenticated" @click="openCreateDialog" class="...">
  Create Sequence
</button>

<!-- Example: Edit/Delete buttons in table row -->
<button v-if="isAuthenticated" @click="openEditDialog(seq)" class="...">Edit</button>
<button v-if="isAuthenticated" @click="openDeleteDialog(seq)" class="...">Delete</button>
```

**Note:** Read the current `SequenceListView.vue` fully before editing to identify the exact template locations. Add `v-if="isAuthenticated"` only to the write-action buttons — do not alter the table or read-only parts.

- [ ] **Step 3: Run frontend check**

```bash
cd frontend && npx vue-tsc --noEmit && npx eslint src/
```

Expected: 0 errors.

- [ ] **Step 4: Run all Vitest tests**

```bash
cd frontend && npx vitest run
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/layout/AppNavbar.vue frontend/src/views/SequenceListView.vue
git commit -m "feat(frontend): add auth state to Navbar and conditional write UI in SequenceListView"
```

---

### Task 12: Playwright E2E tests for auth flow and users page

**Files:**
- Identify the existing Playwright E2E test location (run `ls frontend/` and `ls frontend/tests/` or check `frontend/playwright.config.ts`)
- Create new E2E test file alongside existing ones

- [ ] **Step 1: Find the Playwright config and existing E2E test directory**

```bash
ls /Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/
```

Look for `playwright.config.ts` and an `e2e/` or `tests/` directory containing `.spec.ts` files.

- [ ] **Step 2: Create the auth E2E test file next to existing E2E tests**

The file path will be determined by Step 1, but follows the pattern `frontend/e2e/auth.spec.ts` or `frontend/tests/e2e/auth.spec.ts`. Create it with the content below, adjusting the path to match what you found:

```typescript
import { test, expect } from '@playwright/test'
import * as allure from 'allure-playwright'
import { injectAuthToken } from './helpers/api'

/**
 * Auth flow E2E tests.
 *
 * These tests do NOT contact Google. injectAuthToken() obtains a JWT via
 * POST /auth/token (registered when ENABLE_PASSWORD_AUTH=true) and injects
 * it directly into localStorage — simulating a completed OAuth login.
 */

const FRONTEND_URL = 'http://localhost:5173'

test.describe('Auth UI', () => {
  test.beforeEach(async () => {
    await allure.epic('Frontend')
    await allure.feature('Auth UI')
  })

  test('unauthenticated user sees Sign in button in navbar', async ({ page }) => {
    await allure.story('Unauthenticated state')
    await page.goto(`${FRONTEND_URL}/sequences`)
    await expect(page.getByText('Sign in with Google')).toBeVisible()
  })

  test('authenticated user sees their email in navbar', async ({ page }) => {
    await allure.story('Authenticated state')
    await injectAuthToken(page)
    await page.goto(`${FRONTEND_URL}/sequences`)
    await expect(page.getByText('admin')).toBeVisible()
    await expect(page.getByText('Logout')).toBeVisible()
  })

  test('authenticated user sees Create button on sequences page', async ({ page }) => {
    await allure.story('Authenticated state')
    await injectAuthToken(page)
    await page.goto(`${FRONTEND_URL}/sequences`)
    await expect(page.getByRole('button', { name: /create/i })).toBeVisible()
  })

  test('unauthenticated user does not see Create button', async ({ page }) => {
    await allure.story('Unauthenticated state')
    await page.goto(`${FRONTEND_URL}/sequences`)
    await expect(page.getByRole('button', { name: /create/i })).not.toBeVisible()
  })

  test('logout button clears auth state', async ({ page }) => {
    await allure.story('Logout')
    await injectAuthToken(page)
    await page.goto(`${FRONTEND_URL}/sequences`)
    await page.getByText('Logout').click()
    await expect(page.getByText('Sign in with Google')).toBeVisible()
  })
})

test.describe('Users page', () => {
  test.beforeEach(async () => {
    await allure.epic('Frontend')
    await allure.feature('Users Page')
  })

  test('users page is accessible without login', async ({ page }) => {
    await allure.story('Public access')
    await page.goto(`${FRONTEND_URL}/users`)
    await expect(page.getByText('Users')).toBeVisible()
  })

  test('users page shows the Users nav link', async ({ page }) => {
    await allure.story('Navigation')
    await page.goto(`${FRONTEND_URL}/sequences`)
    await expect(page.getByRole('link', { name: 'Users' })).toBeVisible()
  })
})
```

**Note:** `injectAuthToken` is already defined in `frontend/e2e/helpers/api.ts` — it calls `POST /auth/token` using the `E2E_ADMIN_PASSWORD` env var (defaulting to `'admin'`) and injects the JWT into localStorage. Do not re-implement it inline.

- [ ] **Step 3: Start the full stack for E2E testing**

```bash
just platform-up
just dev-up
```

Wait for both to report healthy. Verify the backend has `ENABLE_PASSWORD_AUTH=true` set in `.env`.

- [ ] **Step 4: Run the new E2E tests**

```bash
just frontend-e2e
```

Or run just the auth spec (adjust path to match what you found in Step 1):

```bash
cd frontend && npx playwright test e2e/auth.spec.ts --reporter=list
```

Expected: All 7 tests pass.

- [ ] **Step 5: Run the full CI gate**

```bash
just ci
```

Expected: All checks and tests pass.

- [ ] **Step 6: Update TASK_PLAN.md**

Open `TASK_PLAN.md`. Mark the Phase 4 remaining items and all Phase 5 items as complete:

```markdown
- [x] Login Flow UI and JWT persistence in localStorage
- [x] Edit Mode with conditional rendering based on auth state
```

And update or add a Phase 5 section:

```markdown
## Phase 5: Social Login & User Management ✅

- [x] Google OAuth2 backend (google_oauth.py + user_routes.py)
- [x] User model + Alembic migration
- [x] pytest-env dev dependency + pyproject.toml env config
- [x] admin_username / admin_password_hash / google_client_id / google_client_secret optional in config.py
- [x] Frontend login flow (LoginView, AuthCallbackView, useAuth composable)
- [x] Users page (UsersView + api/users.ts)
- [x] Navbar auth state
- [x] Sequences page conditional edit UI
- [x] Tests (backend unit + Vitest + Playwright E2E)
```

- [ ] **Step 7: Commit**

```bash
git add frontend/e2e/auth.spec.ts TASK_PLAN.md
git commit -m "test(e2e): add Playwright auth flow and users page tests"
```

---

### Task 13: Update architectural and frontend documentation

**Files:**
- Modify: `docs/architecture.md`
- Modify: `docs/frontend.md`

- [ ] **Step 1: Read both docs in full before editing**

```bash
cat docs/architecture.md
cat docs/frontend.md
```

Read them completely — do not guess at existing content.

- [ ] **Step 2: Update docs/architecture.md**

Make the following targeted additions — do not rewrite existing sections:

**a) In the Overview paragraph**, update the description to mention auth:

Change:
> "The backend uses layered architecture, real-database integration tests, dependency injection, structured exception handling, and a full observability stack..."

To:
> "The backend uses layered architecture, real-database integration tests, dependency injection, structured exception handling, a full observability stack, and Google OAuth2 social login with JWT-based session management..."

**b) Add a new section under "Key Architectural Decisions"** titled `### Google OAuth2 Authentication (Backend-driven Authorization Code Flow)`:

```markdown
### Google OAuth2 Authentication (Backend-driven Authorization Code Flow)

Authentication uses Google's OAuth2 Authorization Code Flow with server-side token exchange.
The browser is redirected to `/auth/google/login`, which generates a CSRF state token and
redirects to Google's consent screen. Google redirects back to `/auth/google/callback`, where
the backend exchanges the authorization code for a Google access token (via `httpx` in sync
mode), fetches the user profile, upserts the `users` table row, and issues a project-scoped
JWT. The JWT is passed to the SPA as a `?token=` query parameter on a redirect to the frontend
`/auth/callback` page.

The client secret never leaves the backend. CSRF is prevented via the `state` parameter.
The in-memory state store requires single-worker deployment (the default for `just backend-dev`).

Key files: `backend/google_oauth.py` (OAuth2 protocol helpers), `backend/user_routes.py`
(OAuth endpoints + `/users/` + `/users/me`).
```

**c) Add a new `### users table` entry to the database schema section** (or add a note near the existing schema table if there is one):

```markdown
### `users` table

Persists Google account profiles on first login and updates `name`/`picture` on subsequent
logins. The `email` column is the JWT subject — used to resolve `WriteDep` to a full user
object in the `/users/me` endpoint.

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | Auto-increment |
| `google_id` | String UNIQUE | Stable Google account identifier |
| `email` | String UNIQUE | JWT subject; displayed in UI |
| `name` | String | Display name from Google profile |
| `picture` | String (nullable) | Avatar URL — refreshed on every login |
| `created_at` | DateTime(tz) | First login timestamp |
```

- [ ] **Step 3: Update docs/frontend.md**

Make the following targeted additions — do not rewrite existing sections:

**a) In the Tech Stack table**, add a new row for the auth composable if there is a "State" or "Composables" row, or add a note:

Add to the Key Architectural Decisions section a new entry:

```markdown
### Auth state: `useAuth` composable

Authentication state is managed by `frontend/src/composables/useAuth.ts` — a single source
of truth backed by a Vue `ref<string | null>` initialised from `localStorage.getItem('access_token')`.

Using a `ref` (rather than reading localStorage directly inside a computed) means that
`setToken()` and `logout()` trigger reactive UI updates immediately in the same tick without
needing a component re-mount.

The composable exposes:
- `isAuthenticated` — `ComputedRef<boolean>`: true if token exists and `exp` claim is in the future
- `user` — `ComputedRef<{ email, name } | null>`: decoded from the JWT payload
- `setToken(t)` — called by `AuthCallbackView` after the OAuth redirect
- `login()` / `logout()` — navigate to `/login` or clear state and go home

JWT payloads use base64url encoding; `decodePayload` normalises to standard base64 before
calling `atob()` so it works correctly with real JWTs from the backend.
```

**b) In the routes/pages section** (or wherever existing views are listed), add the three new pages:

```markdown
| `/login` | `LoginView.vue` | "Sign in with Google" — sets `window.location.href` to `/auth/google/login` (top-level navigation, not fetch — required for the cross-origin redirect to Google) |
| `/auth/callback` | `AuthCallbackView.vue` | Reads `?token=` from URL, calls `setToken()`, navigates to `/` |
| `/users` | `UsersView.vue` | Lists all users who have logged in (public — no auth required) |
```

**c) In the testing section**, add a note about the E2E auth strategy:

```markdown
Playwright E2E tests that require an authenticated state do **not** contact Google.
`injectAuthToken(page)` from `e2e/helpers/api.ts` calls `POST /auth/token` (available
when `ENABLE_PASSWORD_AUTH=true`) and injects the JWT into localStorage directly,
simulating a completed OAuth login.
```

- [ ] **Step 4: Verify docs render correctly (optional quick check)**

```bash
cat docs/architecture.md | grep -A5 "Google OAuth2"
cat docs/frontend.md | grep -A5 "useAuth"
```

Expected: The new sections appear in the output.

- [ ] **Step 5: Commit**

```bash
git add docs/architecture.md docs/frontend.md
git commit -m "docs(arch): document Google OAuth2 auth flow, users table, and useAuth composable"
```

---

- [ ] **Step 8: Squash commits before raising a PR**

```bash
git rebase -i origin/main
```

Mark all commits as `squash` except the first. Write a single conventional commit message:

```
feat(auth): implement Google OAuth2 social login and user management

- Add User model and Alembic migration (users table)
- Add Google OAuth2 Authorization Code Flow (backend/google_oauth.py)
- Add /auth/google/login, /auth/google/callback, /users/, /users/me endpoints
- Make auth router conditional on ENABLE_PASSWORD_AUTH setting
- Add useAuth composable (ref-backed, reactive localStorage)
- Add LoginView, AuthCallbackView, UsersView
- Add conditional write UI in SequenceListView and AppNavbar auth state
- Add backend unit tests, Vitest component tests, Playwright E2E tests
```

---

*End of plan.*
