"""Integration tests for Google OAuth2 callback endpoints."""

from unittest.mock import patch

import allure
import fakeredis
import pytest
from fastapi.testclient import TestClient

import backend.google_oauth as google_oauth_mod
from backend.google_oauth import GoogleUserInfo, generate_state


@allure.feature("Google OAuth2")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Callback")  # pyright: ignore[reportUnknownMemberType]
class TestGoogleCallbackRedirect:
    _USER_INFO = GoogleUserInfo(
        google_id="google-123",
        email="user@example.com",
        name="Test User",
        picture=None,
    )

    def test_callback_sets_cookie_not_fragment(
        self, fake_redis: fakeredis.FakeRedis, client: TestClient
    ) -> None:
        """Callback delivers JWT via HttpOnly cookie, not URL fragment."""
        state, _ = generate_state()

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
        assert "#token=" not in location, "Token must not be in URL fragment"
        assert "?token=" not in location, "Token must not be in query string"
        # Token should be in set-cookie header instead
        set_cookie = response.headers.get("set-cookie", "")
        assert "access_token=" in set_cookie


@allure.feature("Google OAuth2")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Observability")  # pyright: ignore[reportUnknownMemberType]
class TestObservability:
    def test_invalid_state_emits_structured_log(
        self,
        client: TestClient,
        fake_redis: fakeredis.FakeRedis,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Submitting an invalid state token must emit oauth.state.invalid log event."""
        warning_events: list[str] = []

        def capture_warning(message: str, *args: object, **kwargs: object) -> None:
            del message, args
            extra = kwargs.get("extra")
            if isinstance(extra, dict):
                event = extra.get("event")  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
                if isinstance(event, str):
                    warning_events.append(event)

        monkeypatch.setattr(google_oauth_mod.logger, "warning", capture_warning)

        response = client.get(
            "/auth/google/callback?state=invalid-state&code=authcode",
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert (
            "oauth.state.invalid" in warning_events
        ), f"Expected oauth.state.invalid in warning events but got: {warning_events}"
