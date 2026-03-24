"""Tests for JWT security utilities — claims allowlist, cookie auth, and revocation."""

import logging

import allure
import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import backend.security as security_mod
from backend.security import ExtraClaims, create_access_token


@allure.feature("Security")  # pyright: ignore[reportUnknownMemberType]
@allure.story("JWT ExtraClaims")  # pyright: ignore[reportUnknownMemberType]
class TestExtraClaims:
    def test_extra_claims_type_is_typed_dict(self) -> None:
        """ExtraClaims is a TypedDict with 'name' and optional 'picture' keys."""
        # Verify that ExtraClaims can be constructed with expected keys
        claims: ExtraClaims = {
            "name": "Alice",
            "picture": "https://example.com/pic.jpg",
        }
        assert claims["name"] == "Alice"
        assert claims["picture"] == "https://example.com/pic.jpg"
        # Verify that picture can be omitted
        claims_no_picture: ExtraClaims = {"name": "Bob"}  # type: ignore[typeddict-item]
        assert claims_no_picture["name"] == "Bob"

    def test_extra_claims_allowlist_contains_expected_keys(self) -> None:
        """_ALLOWED_EXTRA_CLAIMS backstop contains exactly name and picture."""
        allowed_extra_claims = getattr(security_mod, "_ALLOWED_EXTRA_CLAIMS")
        assert "name" in allowed_extra_claims
        assert "picture" in allowed_extra_claims
        assert "email" not in allowed_extra_claims
        assert "sub" not in allowed_extra_claims

    def test_create_access_token_includes_extra_claims(self) -> None:
        """Extra claims appear as top-level JWT claims."""
        import jwt

        from backend.config import settings

        token = create_access_token(
            subject="user@example.com",
            extra_claims={"name": "Alice", "picture": "https://example.com/pic.jpg"},
        )
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        assert payload["name"] == "Alice"
        assert payload["picture"] == "https://example.com/pic.jpg"

    def test_create_access_token_filters_unknown_extra_claims(self) -> None:
        """Unknown extra claims are filtered out by the runtime backstop."""
        import jwt

        from backend.config import settings

        # Inject bad key directly at runtime
        bad_dict: ExtraClaims = {"name": "Alice", "picture": ""}  # type: ignore[typeddict-item]
        bad_dict_raw: dict[str, str] = {key: value for key, value in bad_dict.items()}
        bad_dict_raw["email"] = "alice@example.com"  # not in _ALLOWED_EXTRA_CLAIMS
        token = create_access_token(
            subject="user@example.com",
            extra_claims=bad_dict_raw,  # type: ignore[arg-type]
        )
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        assert "email" not in payload

    def test_create_access_token_includes_jti(self) -> None:
        """Tokens include a unique jti claim for revocation."""
        import jwt

        from backend.config import settings

        token = create_access_token(subject="user@example.com")
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        assert "jti" in payload
        assert isinstance(payload["jti"], str)
        assert len(payload["jti"]) > 0

    def test_jti_is_unique_per_token(self) -> None:
        """Each call to create_access_token generates a distinct jti."""
        import jwt

        from backend.config import settings

        t1 = create_access_token(subject="user@example.com")
        t2 = create_access_token(subject="user@example.com")
        algos = [settings.jwt_algorithm]
        p1 = jwt.decode(t1, settings.jwt_secret_key, algorithms=algos)
        p2 = jwt.decode(t2, settings.jwt_secret_key, algorithms=algos)
        assert p1["jti"] != p2["jti"]


@allure.feature("Security")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Cookie Auth")  # pyright: ignore[reportUnknownMemberType]
class TestCookieAuth:
    def test_cookie_auth_returns_401_without_cookie(self, client: TestClient) -> None:
        """Protected endpoint returns 401 when no access_token cookie is present."""
        response = client.get("/users/me")
        assert response.status_code == 401

    def test_cookie_auth_allows_access_with_valid_cookie(
        self, auth_client: TestClient, db_session: Session
    ) -> None:
        """Protected endpoint returns 200 with valid access_token cookie."""
        from backend.models import User

        db_session.add(
            User(
                google_id="test-cookie-auth-gid",
                email="test@example.com",
                name="Test",
                picture=None,
            )
        )
        db_session.flush()
        response = auth_client.get("/users/me")
        assert response.status_code == 200


@allure.feature("Security")  # pyright: ignore[reportUnknownMemberType]
@allure.story("JWT Revocation")  # pyright: ignore[reportUnknownMemberType]
class TestRevocation:
    def test_revoked_token_rejected(self, fake_redis: fakeredis.FakeRedis) -> None:
        """A token whose jti is in the revocation set returns 401."""
        import jwt

        from backend.config import settings
        from backend.main import app

        token = create_access_token(subject="alice@example.com")
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        jti = payload["jti"]
        fake_redis.set(f"oauth:revoked:{jti}", "1")

        with TestClient(app, cookies={"access_token": token}) as client:
            response = client.get("/users/me")
        assert response.status_code == 401

    def test_redis_down_during_revocation_fails_closed(
        self,
        client: TestClient,
        fake_redis: fakeredis.FakeRedis,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When Redis is unavailable, revocation check must return 503 (fail-closed).

        Must patch backend.security.get_redis (the imported name used by
        _decode_token_subject) — patching only backend.redis_client.get_redis
        won't work due to Python's import-time name binding.
        """
        import redis as redis_lib

        import backend.security as security_mod

        del fake_redis

        def broken_get_redis() -> None:
            raise redis_lib.ConnectionError("Redis down")

        monkeypatch.setattr(security_mod, "get_redis", broken_get_redis)

        token = create_access_token(subject="alice@example.com")
        client.cookies.set("access_token", token)
        response = client.get("/users/me")
        assert response.status_code == 503


@allure.feature("Security")  # pyright: ignore[reportUnknownMemberType]
@allure.story("JWT Decode Logging")  # pyright: ignore[reportUnknownMemberType]
class TestJWTDecodeLogging:
    def test_anomalous_jwt_error_logs_at_warning(
        self,
        fake_redis: fakeredis.FakeRedis,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A JWTError that is not an ExpiredSignatureError must log at WARNING level.

        Tamper with the token signature so jose raises JWTError (bad signature)
        which is not an ExpiredSignatureError — this is anomalous and should be
        surfaced at WARNING so operators can detect algorithm confusion or forgery
        attempts.

        Uses monkeypatch to intercept logger.warning calls directly on the
        module-level logger in backend.security, avoiding pytest caplog
        capture interactions that occur when TestClient(app) has been used
        in a preceding test.
        """
        decode_token_subject = getattr(security_mod, "_decode_token_subject")

        token = create_access_token(subject="alice@example.com")
        # Corrupt the signature segment (last part of the JWT)
        parts = token.split(".")
        parts[-1] = parts[-1][:-4] + "XXXX"
        bad_token = ".".join(parts)

        warning_calls: list[tuple[object, ...]] = []

        def _capture_warning(*args: object, **kwargs: object) -> None:
            warning_calls.append(args)

        monkeypatch.setattr(security_mod.logger, "warning", _capture_warning)

        try:
            decode_token_subject(bad_token)
        except Exception:
            pass  # expected to raise HTTPException

        assert len(warning_calls) > 0, (
            "Expected logger.warning to be called for anomalous JWT error,"
            " but it was not called"
        )
        first_msg = str(warning_calls[0][0]) if warning_calls else ""
        assert (
            "JWT" in first_msg or "jwt" in first_msg.lower() or "anomalous" in first_msg
        ), f"Expected JWT-related warning message, got: {first_msg}"

    def test_expired_jwt_logs_at_debug_not_warning(
        self,
        fake_redis: fakeredis.FakeRedis,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """An ExpiredSignatureError must log only at DEBUG — not at WARNING.

        Expired tokens are routine (normal token lifecycle) and should not
        pollute operator alerting channels.
        """
        # Create an already-expired token
        from datetime import datetime, timedelta, timezone

        from jose import jwt as jose_jwt

        from backend.config import settings

        decode_token_subject = getattr(security_mod, "_decode_token_subject")

        payload = {
            "sub": "alice@example.com",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=60),
            "jti": "test-jti",
        }
        expired_token = str(
            jose_jwt.encode(  # pyright: ignore[reportUnknownMemberType]
                payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
            )
        )

        with caplog.at_level(logging.DEBUG, logger="backend.security"):
            try:
                decode_token_subject(expired_token)
            except Exception:
                pass  # expected to raise HTTPException

        warning_events = [r for r in caplog.records if r.levelno == logging.WARNING]
        # No warning should be emitted for a routine expiry
        assert not any(
            "JWT" in r.message or "jwt" in r.message.lower() for r in warning_events
        ), (
            "Expected no WARNING log for expired JWT, but got: "
            f"{[r.message for r in warning_events]}"
        )
