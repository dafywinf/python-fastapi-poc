"""Unit tests for Google OAuth2 helpers in backend/google_oauth.py.

These tests do not touch the database — they test pure functions and mock
all outbound HTTP calls.
"""

import time
from unittest.mock import MagicMock, patch

import allure
import httpx
import pytest
from fastapi import HTTPException

from backend.google_oauth import (
    STATE_TTL_SECONDS,
    build_google_redirect_url,
    exchange_code_for_tokens,
    fetch_google_user_info,
    generate_state,
    state_store,
    validate_and_consume_state,
)


@allure.feature("Google OAuth2")  # pyright: ignore[reportUnknownMemberType]
@allure.story("State Management")  # pyright: ignore[reportUnknownMemberType]
class TestStateManagement:
    def setup_method(self) -> None:
        """Clear the state store before each test."""
        state_store.clear()

    def test_generate_state_returns_unique_tokens(self) -> None:
        s1 = generate_state()
        s2 = generate_state()
        assert s1 != s2
        assert len(s1) > 16

    def test_generate_state_stores_timestamp(self) -> None:
        before = time.monotonic()
        state = generate_state()
        after = time.monotonic()
        assert state in state_store
        assert before <= state_store[state] <= after

    def test_validate_and_consume_state_removes_state(self) -> None:
        state = generate_state()
        validate_and_consume_state(state)
        assert state not in state_store

    def test_validate_and_consume_state_raises_on_unknown(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            validate_and_consume_state("not-a-real-state")
        assert exc_info.value.status_code == 400

    def test_validate_and_consume_state_raises_on_expired(self) -> None:
        state = generate_state()
        # Manually set the timestamp to be older than the TTL
        state_store[state] = time.monotonic() - STATE_TTL_SECONDS - 1
        with pytest.raises(HTTPException) as exc_info:
            validate_and_consume_state(state)
        assert exc_info.value.status_code == 400
        assert state not in state_store


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
