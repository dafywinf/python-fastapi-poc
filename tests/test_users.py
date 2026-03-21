"""Tests for user persistence and the /users endpoints."""

import secrets
import time
from unittest.mock import MagicMock, patch

import allure
import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.google_oauth import GoogleUserInfo, generate_state
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

        with pytest.raises(IntegrityError):
            db_session.add(User(google_id="dup-id", email="b@example.com", name="B"))
            db_session.flush()

    def test_email_is_unique(self, db_session: Session) -> None:
        db_session.add(User(google_id="id-1", email="same@example.com", name="A"))
        db_session.flush()

        with pytest.raises(IntegrityError):
            db_session.add(User(google_id="id-2", email="same@example.com", name="B"))
            db_session.flush()


@allure.feature("Users")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Google Login Redirect")  # pyright: ignore[reportUnknownMemberType]
class TestGoogleLogin:
    def test_login_redirects_to_google(
        self, fake_redis: fakeredis.FakeRedis, client: TestClient
    ) -> None:
        response = client.get("/auth/google/login", follow_redirects=False)
        assert response.status_code == 307
        location = response.headers["location"]
        assert "accounts.google.com" in location
        assert "state=" in location
        assert "response_type=code" in location

    def test_login_includes_required_scopes(
        self, fake_redis: fakeredis.FakeRedis, client: TestClient
    ) -> None:
        response = client.get("/auth/google/login", follow_redirects=False)
        location = response.headers["location"]
        assert "email" in location
        assert "profile" in location


@allure.feature("Users")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Google OAuth Callback")  # pyright: ignore[reportUnknownMemberType]
class TestGoogleCallback:
    def _make_mock_google(
        self,
        google_id: str = "gid-1",
        email: str = "alice@example.com",
        name: str = "Alice",
        picture: str | None = "https://img.example.com/alice.jpg",
    ) -> MagicMock:
        """Return a mock replacing exchange_code_for_tokens + fetch_google_user_info."""
        mock = MagicMock()
        mock.exchange.return_value = {"access_token": "fake-goog-token"}
        mock.userinfo.return_value = GoogleUserInfo(
            google_id=google_id, email=email, name=name, picture=picture
        )
        return mock

    def test_callback_creates_user_and_redirects_with_jwt(
        self,
        fake_redis: fakeredis.FakeRedis,
        client: TestClient,
        db_session: Session,
    ) -> None:
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
        assert "#token=" in location

        # Verify user was persisted in DB
        user = db_session.execute(
            select(User).where(User.email == "alice@example.com")
        ).scalar_one_or_none()
        assert user is not None
        assert user.google_id == "gid-1"
        assert user.name == "Alice"

    def test_callback_updates_existing_user_profile(
        self,
        fake_redis: fakeredis.FakeRedis,
        client: TestClient,
        db_session: Session,
    ) -> None:
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

    def test_callback_rejects_invalid_state(
        self, fake_redis: fakeredis.FakeRedis, client: TestClient
    ) -> None:
        response = client.get(
            "/auth/google/callback?code=some-code&state=invalid-state",
            follow_redirects=False,
        )
        assert response.status_code == 400

    def test_callback_rejects_expired_state(
        self, fake_redis: fakeredis.FakeRedis, client: TestClient
    ) -> None:
        state = secrets.token_urlsafe(32)
        # Write directly with TTL=1, wait for expiry
        fake_redis.setex(f"oauth:state:{state}", 1, "1")
        time.sleep(2)

        response = client.get(
            f"/auth/google/callback?code=code&state={state}",
            follow_redirects=False,
        )
        assert response.status_code == 400

    def test_callback_rejects_replayed_state(
        self,
        fake_redis: fakeredis.FakeRedis,
        client: TestClient,
    ) -> None:
        """A state token consumed by a successful callback cannot be replayed."""
        state = generate_state()
        mock = self._make_mock_google()

        with (
            patch("backend.user_routes.exchange_code_for_tokens", mock.exchange),
            patch("backend.user_routes.fetch_google_user_info", mock.userinfo),
        ):
            first = client.get(
                f"/auth/google/callback?code=code&state={state}",
                follow_redirects=False,
            )
            second = client.get(
                f"/auth/google/callback?code=code&state={state}",
                follow_redirects=False,
            )

        assert first.status_code in (302, 307)
        assert second.status_code == 400

    def test_callback_returns_400_when_user_denies_consent(
        self, fake_redis: fakeredis.FakeRedis, client: TestClient
    ) -> None:
        """Google redirects with ?error=access_denied when the user cancels.

        The endpoint must not return a raw FastAPI 422 (missing 'code' param)
        but instead a graceful 400.
        """
        state = generate_state()
        response = client.get(
            f"/auth/google/callback?error=access_denied&state={state}",
            follow_redirects=False,
        )
        assert response.status_code == 400


@allure.feature("Users")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Users List")  # pyright: ignore[reportUnknownMemberType]
class TestUsersList:
    def test_list_users_returns_empty_list_by_default(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/users/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_users_returns_seeded_users(
        self, client: TestClient, db_session: Session, auth_headers: dict[str, str]
    ) -> None:
        db_session.add(
            User(google_id="g1", email="a@test.com", name="Alice", picture=None)
        )
        db_session.add(
            User(google_id="g2", email="b@test.com", name="Bob", picture=None)
        )
        db_session.flush()

        response = client.get("/users/", headers=auth_headers)
        assert response.status_code == 200
        emails = [u["email"] for u in response.json()]
        assert "a@test.com" in emails
        assert "b@test.com" in emails

    def test_list_users_requires_authentication(self, client: TestClient) -> None:
        response = client.get("/users/")
        assert response.status_code == 401


@allure.feature("Users")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Users Me")  # pyright: ignore[reportUnknownMemberType]
class TestUsersMe:
    def test_me_returns_own_profile(
        self, client: TestClient, db_session: Session, auth_token: str
    ) -> None:
        """Seed a User row matching the admin JWT subject, then call /users/me."""
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
