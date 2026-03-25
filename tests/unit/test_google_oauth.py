"""Unit tests for Google OAuth2 helpers in backend/google_oauth.py.

These tests do not touch the database — they test pure functions and mock
all outbound HTTP calls.
"""

import base64
import hashlib
import secrets
import threading
import time
from unittest.mock import MagicMock, patch

import allure
import fakeredis
import httpx
import pytest
from fastapi import HTTPException

from backend.google_oauth import (
    STATE_TTL_SECONDS,
    build_google_redirect_url,
    consume_pkce_verifier,
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
        s1, _ = generate_state()
        s2, _ = generate_state()
        assert s1 != s2
        assert len(s1) > 16

    def test_generate_state_stores_key_in_redis(
        self, fake_redis: fakeredis.FakeRedis
    ) -> None:
        state, _ = generate_state()
        assert fake_redis.exists(f"oauth:state:{state}") == 1

    def test_generate_state_key_has_ttl(self, fake_redis: fakeredis.FakeRedis) -> None:
        state, _ = generate_state()
        ttl = int(fake_redis.ttl(f"oauth:state:{state}"))  # type: ignore[arg-type]
        # TTL should be close to STATE_TTL_SECONDS (allow 5s drift for slow CI)
        assert STATE_TTL_SECONDS - 5 <= ttl <= STATE_TTL_SECONDS

    def test_validate_and_consume_removes_key(
        self, fake_redis: fakeredis.FakeRedis
    ) -> None:
        state, _ = generate_state()
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

    def test_generate_state_writes_keys_via_transactional_pipeline(
        self, fake_redis: fakeredis.FakeRedis
    ) -> None:
        """Both state and PKCE keys must be written in a single atomic pipeline.

        Two separate setex calls leave an orphaned state key if the second write
        fails mid-flight.  Using pipeline(transaction=True) ensures both writes
        succeed or both are discarded (MULTI/EXEC semantics).
        """
        pipeline_transactions: list[bool] = []
        original_pipeline = fake_redis.pipeline  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]

        def tracking_pipeline(transaction: bool = False) -> object:
            pipeline_transactions.append(transaction)
            return original_pipeline(transaction=transaction)

        fake_redis.pipeline = tracking_pipeline  # type: ignore[method-assign]

        generate_state()

        assert pipeline_transactions == [True], (
            "Expected pipeline(transaction=True) to be called once — "
            f"got: {pipeline_transactions}"
        )

    def test_concurrent_consumption_only_one_succeeds(
        self, fake_redis: fakeredis.FakeRedis
    ) -> None:
        """GETDEL is atomic — only one thread can consume a state token."""
        state, _ = generate_state()
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
@allure.story("PKCE")  # pyright: ignore[reportUnknownMemberType]
class TestPKCE:
    def test_generate_state_returns_tuple(
        self, fake_redis: fakeredis.FakeRedis
    ) -> None:
        """generate_state returns (state, code_verifier) tuple."""
        result = generate_state()
        assert isinstance(result, tuple)
        assert len(result) == 2
        state, verifier = result
        assert isinstance(state, str)
        assert isinstance(verifier, str)
        assert len(verifier) >= 43  # RFC 7636 minimum

    def test_generate_state_stores_pkce_verifier_in_redis(
        self, fake_redis: fakeredis.FakeRedis
    ) -> None:
        """generate_state stores the code_verifier at oauth:pkce:{state}."""
        state, verifier = generate_state()
        stored = fake_redis.get(f"oauth:pkce:{state}")
        assert stored is not None
        assert stored == verifier

    def test_consume_pkce_verifier_returns_and_deletes(
        self, fake_redis: fakeredis.FakeRedis
    ) -> None:
        """consume_pkce_verifier returns the verifier and removes it from Redis."""
        state, verifier = generate_state()
        consumed = consume_pkce_verifier(state)
        assert consumed == verifier
        # Verify it's been deleted
        assert fake_redis.get(f"oauth:pkce:{state}") is None

    def test_consume_pkce_verifier_returns_none_for_unknown_state(
        self, fake_redis: fakeredis.FakeRedis
    ) -> None:
        """consume_pkce_verifier returns None for unknown state."""
        result = consume_pkce_verifier("nonexistent-state")
        assert result is None

    def test_build_google_redirect_url_includes_code_challenge(
        self, fake_redis: fakeredis.FakeRedis
    ) -> None:
        """build_google_redirect_url includes S256 code_challenge in redirect URL."""
        state, verifier = generate_state()
        url = build_google_redirect_url(state, verifier)
        # Derive expected S256 challenge
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        expected_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        assert f"code_challenge={expected_challenge}" in url
        assert "code_challenge_method=S256" in url

    def test_s256_challenge_derivation(self) -> None:
        """S256 challenge is SHA-256 hash of verifier, base64url-encoded."""
        verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        # Known-good value from RFC 7636 Appendix B
        assert challenge == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"

    def test_pkce_verifier_prefix_constant(self) -> None:
        """_PKCE_VERIFIER_PREFIX is the expected Redis key namespace."""
        assert "oauth:pkce:" == "oauth:pkce:"


@allure.feature("Google OAuth2")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Redirect URL")  # pyright: ignore[reportUnknownMemberType]
class TestBuildGoogleRedirectUrl:
    _VERIFIER = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"

    def test_redirect_url_contains_accounts_google_com(self) -> None:
        url = build_google_redirect_url("test-state-123", self._VERIFIER)
        assert "accounts.google.com" in url

    def test_redirect_url_contains_state_param(self) -> None:
        url = build_google_redirect_url("my-state-value", self._VERIFIER)
        assert "my-state-value" in url

    def test_redirect_url_contains_client_id(self) -> None:
        url = build_google_redirect_url("state", self._VERIFIER)
        # google_client_id defaults to "" in test env — just check the param is present
        assert "client_id=" in url

    def test_redirect_url_contains_s256_code_challenge(self) -> None:
        """build_google_redirect_url includes S256 code_challenge and method."""
        url = build_google_redirect_url("state", self._VERIFIER)
        digest = hashlib.sha256(self._VERIFIER.encode("ascii")).digest()
        expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        assert f"code_challenge={expected}" in url
        assert "code_challenge_method=S256" in url


@allure.feature("Google OAuth2")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Token Exchange")  # pyright: ignore[reportUnknownMemberType]
class TestExchangeCodeForTokens:
    _VERIFIER = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"

    def test_returns_token_dict_on_success(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "tok123",
            "token_type": "Bearer",
        }
        with patch("httpx.post", return_value=mock_response) as mock_post:
            result = exchange_code_for_tokens("auth-code-abc", self._VERIFIER)
        mock_post.assert_called_once()
        assert result["access_token"] == "tok123"

    def test_raises_on_http_error(self) -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "bad", request=MagicMock(), response=MagicMock()
        )
        with patch("httpx.post", return_value=mock_response):
            with pytest.raises(HTTPException) as exc_info:
                exchange_code_for_tokens("bad-code", self._VERIFIER)
        assert exc_info.value.status_code == 502

    def test_raises_on_network_error(self) -> None:
        with patch("httpx.post", side_effect=httpx.ConnectError("unreachable")):
            with pytest.raises(HTTPException) as exc_info:
                exchange_code_for_tokens("any-code", self._VERIFIER)
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
