"""Tests for user persistence and the /users endpoints."""

import asyncio
import secrets
import time
from unittest.mock import MagicMock, patch

import allure
import fakeredis
import pytest
from fastapi.testclient import TestClient
from limits.storage import MemoryStorage
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

    def test_login_includes_pkce_params(
        self, fake_redis: fakeredis.FakeRedis, client: TestClient
    ) -> None:
        response = client.get("/auth/google/login", follow_redirects=False)
        location = response.headers["location"]
        assert "code_challenge=" in location
        assert "code_challenge_method=S256" in location


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

    def test_callback_creates_user_and_sets_cookie(
        self,
        fake_redis: fakeredis.FakeRedis,
        client: TestClient,
        db_session: Session,
    ) -> None:
        state, _ = generate_state()
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
        set_cookie = response.headers.get("set-cookie", "")
        assert "access_token=" in set_cookie

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

        state, _ = generate_state()
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
        state, _ = generate_state()
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
        state, _ = generate_state()
        response = client.get(
            f"/auth/google/callback?error=access_denied&state={state}",
            follow_redirects=False,
        )
        assert response.status_code == 400


@allure.feature("Auth")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Cookie Delivery")  # pyright: ignore[reportUnknownMemberType]
class TestCookieDelivery:
    def test_callback_sets_access_token_cookie(
        self,
        client: TestClient,
        fake_redis: fakeredis.FakeRedis,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """OAuth callback sets access_token with correct HttpOnly cookie attributes.

        frontend_url is patched to https:// so the Secure flag is set — the secure
        flag is derived from the URL scheme, not a static True, to support local dev.
        """
        import backend.user_routes as user_routes_mod
        from backend.config import settings

        monkeypatch.setattr(
            user_routes_mod,
            "settings",
            settings.model_copy(update={"frontend_url": "https://localhost:5173"}),
        )

        state, _ = generate_state()

        def exchange_tokens(code: str, code_verifier: str) -> dict[str, str]:
            del code, code_verifier
            return {"access_token": "gtoken"}

        def fetch_user_info(token: str) -> GoogleUserInfo:
            del token
            return GoogleUserInfo(
                google_id="g1",
                email="alice@example.com",
                name="Alice",
                picture=None,
            )

        monkeypatch.setattr(
            user_routes_mod,
            "exchange_code_for_tokens",
            exchange_tokens,
        )
        monkeypatch.setattr(
            user_routes_mod,
            "fetch_google_user_info",
            fetch_user_info,
        )

        response = client.get(
            f"/auth/google/callback?state={state}&code=authcode",
            follow_redirects=False,
        )
        assert response.status_code in (302, 307)
        set_cookie = response.headers.get("set-cookie", "")
        assert "access_token=" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "Secure" in set_cookie
        assert "samesite=lax" in set_cookie.lower()
        assert "Path=/" in set_cookie
        assert "Max-Age=1800" in set_cookie

    def test_callback_no_longer_puts_token_in_url(
        self,
        client: TestClient,
        fake_redis: fakeredis.FakeRedis,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import backend.user_routes as user_routes_mod

        state, _ = generate_state()

        def exchange_tokens(code: str, code_verifier: str) -> dict[str, str]:
            del code, code_verifier
            return {"access_token": "gtoken"}

        def fetch_user_info(token: str) -> GoogleUserInfo:
            del token
            return GoogleUserInfo(
                google_id="g2",
                email="bob@example.com",
                name="Bob",
                picture=None,
            )

        monkeypatch.setattr(
            user_routes_mod,
            "exchange_code_for_tokens",
            exchange_tokens,
        )
        monkeypatch.setattr(
            user_routes_mod,
            "fetch_google_user_info",
            fetch_user_info,
        )

        response = client.get(
            f"/auth/google/callback?state={state}&code=authcode",
            follow_redirects=False,
        )
        location = response.headers.get("location", "")
        assert "token=" not in location


@allure.feature("Users")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Users List")  # pyright: ignore[reportUnknownMemberType]
class TestUsersList:
    def test_list_users_returns_empty_list_by_default(
        self, auth_client: TestClient
    ) -> None:
        response = auth_client.get("/users/")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_users_returns_seeded_users(
        self, auth_client: TestClient, db_session: Session
    ) -> None:
        db_session.add(
            User(google_id="g1", email="a@test.com", name="Alice", picture=None)
        )
        db_session.add(
            User(google_id="g2", email="b@test.com", name="Bob", picture=None)
        )
        db_session.flush()

        response = auth_client.get("/users/")
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
        self,
        client: TestClient,
        db_session: Session,
        auth_token: str,
        fake_redis: fakeredis.FakeRedis,
    ) -> None:
        """Seed a User row matching the admin JWT subject, then call /users/me."""
        # admin_username defaults to "admin" — this matches the JWT subject
        # issued by POST /auth/token (subject=form_data.username)
        db_session.add(
            User(google_id="g-admin", email="admin", name="Admin User", picture=None)
        )
        db_session.flush()

        client.cookies.set("access_token", auth_token)
        response = client.get("/users/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin"
        assert data["name"] == "Admin User"

    def test_me_requires_authentication(self, client: TestClient) -> None:
        response = client.get("/users/me")
        assert response.status_code == 401

    def test_me_returns_404_when_user_not_in_db(
        self,
        client: TestClient,
        fake_redis: fakeredis.FakeRedis,
    ) -> None:
        """JWT is valid but no User row exists — 404."""
        from backend.security import create_access_token

        del fake_redis
        client.cookies.set(
            "access_token", create_access_token(subject="missing@example.com")
        )
        response = client.get("/users/me")
        assert response.status_code == 404


@allure.feature("Auth")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Refresh Token")  # pyright: ignore[reportUnknownMemberType]
class TestRefreshToken:
    def _make_refresh_token(
        self, fake_redis: fakeredis.FakeRedis, email: str = "alice@example.com"
    ) -> str:
        """Store a refresh token directly in Redis, return the raw token string."""
        from backend.config import settings

        token = secrets.token_urlsafe(32)
        fake_redis.setex(
            f"oauth:refresh:{token}",
            settings.refresh_token_expire_days * 86400,
            email,
        )
        return token

    def test_refresh_issues_new_access_cookie(
        self,
        client: TestClient,
        fake_redis: fakeredis.FakeRedis,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import backend.user_routes as user_routes_mod
        from backend.config import settings

        monkeypatch.setattr(
            user_routes_mod,
            "settings",
            settings.model_copy(update={"frontend_url": "https://localhost:5173"}),
        )
        refresh_token = self._make_refresh_token(fake_redis)
        response = client.post(
            "/auth/refresh", cookies={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        assert "access_token" in response.cookies
        # Verify refresh_token cookie attributes
        set_cookie = response.headers.get("set-cookie", "")
        assert "refresh_token=" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "Secure" in set_cookie
        assert "samesite=strict" in set_cookie.lower()
        assert "Path=/auth" in set_cookie

    def test_refresh_rotates_token(
        self, client: TestClient, fake_redis: fakeredis.FakeRedis
    ) -> None:
        refresh_token = self._make_refresh_token(fake_redis)
        client.post("/auth/refresh", cookies={"refresh_token": refresh_token})
        # Same token rejected on second use
        response2 = client.post(
            "/auth/refresh", cookies={"refresh_token": refresh_token}
        )
        assert response2.status_code == 401

    def test_refresh_missing_cookie_returns_401(
        self, client: TestClient, fake_redis: fakeredis.FakeRedis
    ) -> None:
        response = client.post("/auth/refresh")
        assert response.status_code == 401

    def test_refresh_carries_forward_name_and_picture_claims(
        self,
        client: TestClient,
        fake_redis: fakeredis.FakeRedis,
        db_session: Session,
    ) -> None:
        """Refreshed access token must include name and picture claims from the DB.

        The original implementation passes no extra_claims to create_access_token,
        so the refreshed JWT is stripped of name/picture. This test verifies the fix.
        """
        from jose import jwt as jose_jwt

        email = "refresh-claims@example.com"
        db_session.add(
            User(
                google_id="g-refresh",
                email=email,
                name="Refresh User",
                picture="https://img.example.com/refresh.jpg",
            )
        )
        db_session.flush()

        refresh_token = self._make_refresh_token(fake_redis, email=email)
        response = client.post(
            "/auth/refresh", cookies={"refresh_token": refresh_token}
        )
        assert response.status_code == 200

        access_token_value = response.cookies["access_token"]
        claims = jose_jwt.get_unverified_claims(access_token_value)  # pyright: ignore[reportUnknownMemberType]
        assert (
            claims.get("name") == "Refresh User"
        ), f"Expected 'name' claim in refreshed token, got claims: {claims}"
        assert (
            claims.get("picture") == "https://img.example.com/refresh.jpg"
        ), f"Expected 'picture' claim in refreshed token, got claims: {claims}"


@allure.feature("Auth")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Logout")  # pyright: ignore[reportUnknownMemberType]
class TestLogout:
    def test_logout_clears_cookies(
        self, auth_client: TestClient, fake_redis: fakeredis.FakeRedis
    ) -> None:
        response = auth_client.post("/auth/logout")
        assert response.status_code == 204
        # Cookies cleared — Max-Age=0 or explicit delete
        set_cookie = response.headers.get("set-cookie", "")
        assert "Max-Age=0" in set_cookie or "max-age=0" in set_cookie.lower()

    def test_logout_revokes_access_token(
        self, auth_client: TestClient, fake_redis: fakeredis.FakeRedis
    ) -> None:
        response = auth_client.post("/auth/logout")
        assert response.status_code == 204
        # Check a revocation key was written in Redis
        revoked_keys = list(fake_redis.keys("oauth:revoked:*"))  # pyright: ignore[reportUnknownMemberType,reportArgumentType,reportUnknownVariableType]
        assert len(revoked_keys) == 1  # pyright: ignore[reportUnknownArgumentType]

    def test_revoked_token_is_rejected_on_protected_endpoint(
        self, auth_client: TestClient, fake_redis: fakeredis.FakeRedis
    ) -> None:
        """Revoked access token must be rejected with 401 on protected endpoints.

        Full circuit: authenticate → logout → reuse old token → expect 401.
        """
        # Capture the access token cookie value before logout
        old_token = auth_client.cookies.get("access_token")
        assert old_token is not None, "auth_client must have an access_token cookie"

        # Perform logout — this should write the jti to the revocation blocklist
        logout_response = auth_client.post("/auth/logout")
        assert logout_response.status_code == 204

        # Verify a revocation entry was written
        revoked_keys = list(fake_redis.keys("oauth:revoked:*"))  # pyright: ignore[reportUnknownMemberType,reportArgumentType,reportUnknownVariableType]
        assert len(revoked_keys) == 1, "Expected exactly one revoked jti in Redis"  # pyright: ignore[reportUnknownArgumentType]

        # Reuse the old token on a protected endpoint using a fresh client
        # (auth_client cookies are cleared by logout, so we set manually)
        auth_client.cookies.set("access_token", old_token)
        response = auth_client.get("/users/me")
        assert response.status_code == 401

    def test_refresh_token_invalid_after_logout(
        self, auth_client: TestClient, fake_redis: fakeredis.FakeRedis
    ) -> None:
        """After logout the refresh token must be deleted from Redis.

        Verifies that POST /auth/refresh returns 401 when the refresh token
        has been removed by the logout handler.
        """
        from backend.config import settings

        # Set up a known refresh token in Redis
        refresh_token_value = secrets.token_urlsafe(32)
        fake_redis.setex(
            f"oauth:refresh:{refresh_token_value}",
            settings.refresh_token_expire_days * 86400,
            "test@example.com",
        )

        # Attach the refresh token cookie to auth_client so logout can read it
        auth_client.cookies.set("refresh_token", refresh_token_value)

        # Perform logout — this should delete the refresh token from Redis
        logout_response = auth_client.post("/auth/logout")
        assert logout_response.status_code == 204

        # Confirm the refresh token key is gone from Redis
        assert fake_redis.exists(f"oauth:refresh:{refresh_token_value}") == 0

        # Attempting to refresh with the old token must now return 401
        response = auth_client.post(
            "/auth/refresh", cookies={"refresh_token": refresh_token_value}
        )
        assert response.status_code == 401


@allure.feature("Auth")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Rate Limiting")  # pyright: ignore[reportUnknownMemberType]
class TestRateLimiting:
    def test_rate_limiter_registered_on_app(self) -> None:
        from slowapi import Limiter

        from backend.main import app

        assert isinstance(app.state.limiter, Limiter)

    def test_login_endpoint_returns_429_after_limit(
        self, client: TestClient, fake_redis: fakeredis.FakeRedis
    ) -> None:
        """Exceeding the rate limit returns 429.

        RATELIMIT_ENABLED=false is set in the pytest env to disable limits in all
        other tests. slowapi reads this flag at Limiter construction time (module
        import), so patching the env var at test time has no effect.

        Instead, temporarily enable the limiter directly on the singleton, then
        restore it after the test.
        """
        from backend.rate_limiter import limiter

        previous_enabled = limiter.enabled
        previous_storage = limiter.limiter.storage
        del fake_redis

        limiter.enabled = True
        limiter.limiter.storage = MemoryStorage()
        try:
            responses = [
                client.get("/auth/google/login", follow_redirects=False)
                for _ in range(25)
            ]
        finally:
            limiter.enabled = previous_enabled
            limiter.limiter.storage = previous_storage

        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes


@allure.feature("Startup")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Startup Checks")  # pyright: ignore[reportUnknownMemberType]
class TestStartupChecks:
    def test_https_guard_raises_on_http_backend_url(
        self,
        fake_redis: fakeredis.FakeRedis,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """enforce_https=True + http:// URL must raise RuntimeError at startup.

        Uses async with lifespan(app): the startup code runs before the yield.
        If it raises, the error propagates out of the async with block.
        SCHEDULER_ENABLED=false (set in pytest env) so the scheduler never starts.
        fake_redis must be active so the Redis ping in startup succeeds, letting
        the HTTPS guard run.
        """
        from backend.config import settings
        from backend.main import app, lifespan

        monkeypatch.setattr(settings, "enforce_https", True)
        monkeypatch.setattr(settings, "backend_url", "http://localhost:8000")

        async def _run() -> None:
            async with lifespan(app):
                pass  # startup raises before yield if checks fail

        with pytest.raises(RuntimeError, match="must use HTTPS"):
            asyncio.run(_run())

    def test_redis_health_check_on_startup(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Redis ping failure at startup must raise (fail fast).

        Patch backend.main.get_redis (the imported name) so the ping call fails.
        """
        import redis as redis_lib

        import backend.main as main_mod
        from backend.main import app, lifespan

        def broken() -> None:
            raise redis_lib.ConnectionError("down")

        monkeypatch.setattr(main_mod, "get_redis", broken)

        async def _run() -> None:
            async with lifespan(app):
                pass

        with pytest.raises(redis_lib.ConnectionError):
            asyncio.run(_run())
