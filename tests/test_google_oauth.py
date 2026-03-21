"""Unit tests for Google OAuth2 helpers in backend/google_oauth.py.

These tests do not touch the database — they test pure functions and mock
all outbound HTTP calls.
"""

import base64
import json
import secrets
import threading
import time
from unittest.mock import MagicMock, patch

import allure
import fakeredis
import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.google_oauth import (
    STATE_TTL_SECONDS,
    GoogleUserInfo,
    build_google_redirect_url,
    exchange_code_for_tokens,
    fetch_google_user_info,
    generate_state,
    validate_and_consume_state,
)


@allure.feature("Google OAuth2")  # pyright: ignore[reportUnknownMemberType]
@allure.story("State Management")  # pyright: ignore[reportUnknownMemberType]
class TestStateManagement:
    def test_generate_state_returns_unique_tokens(
        self, fake_redis: fakeredis.FakeRedis
    ) -> None:
        s1 = generate_state()
        s2 = generate_state()
        assert s1 != s2
        assert len(s1) > 16

    def test_generate_state_stores_key_in_redis(
        self, fake_redis: fakeredis.FakeRedis
    ) -> None:
        state = generate_state()
        assert fake_redis.exists(f"oauth:state:{state}") == 1

    def test_generate_state_key_has_ttl(self, fake_redis: fakeredis.FakeRedis) -> None:
        state = generate_state()
        ttl = int(fake_redis.ttl(f"oauth:state:{state}"))  # type: ignore[arg-type]
        # TTL should be close to STATE_TTL_SECONDS (allow 5s drift for slow CI)
        assert STATE_TTL_SECONDS - 5 <= ttl <= STATE_TTL_SECONDS

    def test_validate_and_consume_removes_key(
        self, fake_redis: fakeredis.FakeRedis
    ) -> None:
        state = generate_state()
        validate_and_consume_state(state)
        assert fake_redis.exists(f"oauth:state:{state}") == 0

    def test_validate_rejects_unknown_state(
        self, fake_redis: fakeredis.FakeRedis
    ) -> None:
        with pytest.raises(HTTPException) as exc_info:
            validate_and_consume_state("not-a-real-state")
        assert exc_info.value.status_code == 400

    def test_validate_rejects_expired_state(
        self, fake_redis: fakeredis.FakeRedis
    ) -> None:
        state = secrets.token_urlsafe(32)
        # Write directly with TTL=1, wait for expiry
        fake_redis.setex(f"oauth:state:{state}", 1, "1")
        time.sleep(2)
        with pytest.raises(HTTPException) as exc_info:
            validate_and_consume_state(state)
        assert exc_info.value.status_code == 400

    def test_concurrent_consumption_only_one_succeeds(
        self, fake_redis: fakeredis.FakeRedis
    ) -> None:
        """GETDEL is atomic — only one thread can consume a state token."""
        state = generate_state()
        results: list[bool] = []
        lock = threading.Lock()

        def try_consume() -> None:
            try:
                validate_and_consume_state(state)
                with lock:
                    results.append(True)
            except HTTPException:
                with lock:
                    results.append(False)

        t1 = threading.Thread(target=try_consume)
        t2 = threading.Thread(target=try_consume)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert results.count(True) == 1
        assert results.count(False) == 1


@allure.feature("Google OAuth2")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Redirect URL")  # pyright: ignore[reportUnknownMemberType]
class TestBuildGoogleRedirectUrl:
    def test_redirect_url_contains_accounts_google_com(self) -> None:
        url = build_google_redirect_url("test-state-123")
        assert "accounts.google.com" in url

    def test_redirect_url_contains_state_param(self) -> None:
        url = build_google_redirect_url("my-state-value")
        assert "my-state-value" in url

    def test_redirect_url_contains_client_id(self) -> None:
        url = build_google_redirect_url("state")
        # google_client_id defaults to "" in test env — just check the param is present
        assert "client_id=" in url


@allure.feature("Google OAuth2")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Token Exchange")  # pyright: ignore[reportUnknownMemberType]
class TestExchangeCodeForTokens:
    def test_returns_token_dict_on_success(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "tok123",
            "token_type": "Bearer",
        }
        with patch("httpx.post", return_value=mock_response) as mock_post:
            result = exchange_code_for_tokens("auth-code-abc")
        mock_post.assert_called_once()
        assert result["access_token"] == "tok123"

    def test_raises_on_http_error(self) -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "bad", request=MagicMock(), response=MagicMock()
        )
        with patch("httpx.post", return_value=mock_response):
            with pytest.raises(HTTPException) as exc_info:
                exchange_code_for_tokens("bad-code")
        assert exc_info.value.status_code == 502

    def test_raises_on_network_error(self) -> None:
        with patch("httpx.post", side_effect=httpx.ConnectError("unreachable")):
            with pytest.raises(HTTPException) as exc_info:
                exchange_code_for_tokens("any-code")
        assert exc_info.value.status_code == 502


@allure.feature("Google OAuth2")  # pyright: ignore[reportUnknownMemberType]
@allure.story("User Info")  # pyright: ignore[reportUnknownMemberType]
class TestFetchGoogleUserInfo:
    def test_returns_google_user_info_on_success(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "sub": "google-id-123",
            "email": "jane@example.com",
            "name": "Jane Doe",
            "picture": "https://example.com/photo.jpg",
        }
        with patch("httpx.get", return_value=mock_response):
            info = fetch_google_user_info("access-token-xyz")
        assert info.google_id == "google-id-123"
        assert info.email == "jane@example.com"
        assert info.name == "Jane Doe"
        assert info.picture == "https://example.com/photo.jpg"

    def test_raises_on_http_error(self) -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "bad", request=MagicMock(), response=MagicMock()
        )
        with patch("httpx.get", return_value=mock_response):
            with pytest.raises(HTTPException) as exc_info:
                fetch_google_user_info("bad-token")
        assert exc_info.value.status_code == 502

    def test_raises_on_network_error(self) -> None:
        with patch("httpx.get", side_effect=httpx.ConnectError("unreachable")):
            with pytest.raises(HTTPException) as exc_info:
                fetch_google_user_info("any-token")
        assert exc_info.value.status_code == 502


@allure.feature("Google OAuth2")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Callback")  # pyright: ignore[reportUnknownMemberType]
class TestGoogleCallbackRedirect:
    _USER_INFO = GoogleUserInfo(
        google_id="google-123",
        email="user@example.com",
        name="Test User",
        picture=None,
    )

    def test_callback_redirects_with_fragment_not_query(
        self, fake_redis: fakeredis.FakeRedis, client: TestClient
    ) -> None:
        """JWT must be in the URL fragment (#token=) not the query string (?token=)."""
        state = generate_state()

        with (
            patch(
                "backend.user_routes.exchange_code_for_tokens",
                return_value={"access_token": "google-access-token"},
            ),
            patch(
                "backend.user_routes.fetch_google_user_info",
                return_value=self._USER_INFO,
            ),
        ):
            response = client.get(
                f"/auth/google/callback?code=auth-code&state={state}",
                follow_redirects=False,
            )

        assert response.status_code in (302, 307)
        location = response.headers["location"]
        assert "#token=" in location, f"Expected fragment token, got: {location}"
        assert (
            "?token=" not in location
        ), f"Token must not be in query string: {location}"

    def test_callback_fragment_contains_valid_jwt_with_correct_claims(
        self, fake_redis: fakeredis.FakeRedis, client: TestClient
    ) -> None:
        """The JWT in the fragment must encode the user's email and name."""
        state = generate_state()

        with (
            patch(
                "backend.user_routes.exchange_code_for_tokens",
                return_value={"access_token": "google-access-token"},
            ),
            patch(
                "backend.user_routes.fetch_google_user_info",
                return_value=self._USER_INFO,
            ),
        ):
            response = client.get(
                f"/auth/google/callback?code=auth-code&state={state}",
                follow_redirects=False,
            )

        location = response.headers["location"]
        fragment = location.split("#", 1)[1]
        token = fragment.split("token=", 1)[1]

        # Decode the JWT payload (middle segment) without verifying the signature
        padding = "=" * (-len(token.split(".")[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(token.split(".")[1] + padding))
        assert payload["sub"] == "user@example.com"
        assert payload["name"] == "Test User"
