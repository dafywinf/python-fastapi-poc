"""Tests for authentication and authorization security boundaries."""

from datetime import datetime, timedelta, timezone

import allure
from fastapi.testclient import TestClient
from jose import jwt  # pyright: ignore[reportMissingModuleSource]

from backend.config import settings

# ---------------------------------------------------------------------------
# POST /auth/token
# ---------------------------------------------------------------------------


@allure.epic("Backend")  # pyright: ignore[reportUnknownMemberType]
@allure.feature("Security")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Token issuance")  # pyright: ignore[reportUnknownMemberType]
class TestAuthToken:
    def test_returns_token_for_valid_credentials(self, client: TestClient) -> None:
        response = client.post(
            "/auth/token", data={"username": "admin", "password": "testpass"}
        )

        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert isinstance(body["access_token"], str)
        assert len(body["access_token"]) > 0

    def test_returns_401_for_wrong_password(self, client: TestClient) -> None:
        response = client.post(
            "/auth/token", data={"username": "admin", "password": "wrongpassword"}
        )

        assert response.status_code == 401

    def test_returns_401_for_unknown_username(self, client: TestClient) -> None:
        response = client.post(
            "/auth/token", data={"username": "nobody", "password": "testpass"}
        )

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Write endpoints — must reject unauthenticated requests
# ---------------------------------------------------------------------------


@allure.epic("Backend")  # pyright: ignore[reportUnknownMemberType]
@allure.feature("Security")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Write access control")  # pyright: ignore[reportUnknownMemberType]
class TestWriteProtection:
    def test_post_sequences_requires_auth(self, client: TestClient) -> None:
        response = client.post("/sequences/", json={"name": "Sneaky"})

        assert response.status_code == 401

    def test_patch_sequence_requires_auth(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        with allure.step("Create a sequence with valid auth"):  # pyright: ignore[reportUnknownMemberType]
            create_resp = client.post(
                "/sequences/", json={"name": "Target"}, headers=auth_headers
            )
            assert create_resp.status_code == 201
            sequence_id = create_resp.json()["id"]

        with allure.step("Attempt PATCH without a token"):  # pyright: ignore[reportUnknownMemberType]
            response = client.patch(
                f"/sequences/{sequence_id}", json={"name": "Hijacked"}
            )

        assert response.status_code == 401

    def test_delete_sequence_requires_auth(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        with allure.step("Create a sequence with valid auth"):  # pyright: ignore[reportUnknownMemberType]
            create_resp = client.post(
                "/sequences/", json={"name": "Doomed"}, headers=auth_headers
            )
            assert create_resp.status_code == 201
            sequence_id = create_resp.json()["id"]

        with allure.step("Attempt DELETE without a token"):  # pyright: ignore[reportUnknownMemberType]
            response = client.delete(f"/sequences/{sequence_id}")

        assert response.status_code == 401

    def test_post_sequences_succeeds_with_valid_token(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/sequences/", json={"name": "Authorised"}, headers=auth_headers
        )

        assert response.status_code == 201

    def test_patch_sequence_succeeds_with_valid_token(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        with allure.step("Create a sequence"):  # pyright: ignore[reportUnknownMemberType]
            create_resp = client.post(
                "/sequences/", json={"name": "Before"}, headers=auth_headers
            )
            sequence_id = create_resp.json()["id"]

        with allure.step("PATCH with a valid token"):  # pyright: ignore[reportUnknownMemberType]
            response = client.patch(
                f"/sequences/{sequence_id}",
                json={"name": "After"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        assert response.json()["name"] == "After"

    def test_delete_sequence_succeeds_with_valid_token(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        with allure.step("Create a sequence"):  # pyright: ignore[reportUnknownMemberType]
            create_resp = client.post(
                "/sequences/", json={"name": "ToGo"}, headers=auth_headers
            )
            sequence_id = create_resp.json()["id"]

        with allure.step("DELETE with a valid token"):  # pyright: ignore[reportUnknownMemberType]
            response = client.delete(f"/sequences/{sequence_id}", headers=auth_headers)

        assert response.status_code == 204

    def test_returns_401_for_invalid_token(self, client: TestClient) -> None:
        response = client.post(
            "/sequences/",
            json={"name": "BadToken"},
            headers={"Authorization": "Bearer this.is.not.a.valid.jwt"},
        )

        assert response.status_code == 401

    def test_returns_401_for_expired_token(self, client: TestClient) -> None:
        expired_token = jwt.encode(  # pyright: ignore[reportUnknownMemberType]
            {
                "sub": settings.admin_username,
                "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
            },
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        response = client.post(
            "/sequences/",
            json={"name": "Expired"},
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401

    def test_returns_401_for_tampered_token(self, client: TestClient) -> None:
        valid_token = jwt.encode(  # pyright: ignore[reportUnknownMemberType]
            {
                "sub": settings.admin_username,
                "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            },
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        tampered = valid_token[:-4] + "xxxx"
        response = client.post(
            "/sequences/",
            json={"name": "Tampered"},
            headers={"Authorization": f"Bearer {tampered}"},
        )

        assert response.status_code == 401

    def test_returns_401_for_token_missing_sub_claim(self, client: TestClient) -> None:
        token_without_sub = jwt.encode(  # pyright: ignore[reportUnknownMemberType]
            {"exp": datetime.now(timezone.utc) + timedelta(minutes=30)},
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        response = client.post(
            "/sequences/",
            json={"name": "NoSub"},
            headers={"Authorization": f"Bearer {token_without_sub}"},
        )

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Read endpoints — must remain publicly accessible
# ---------------------------------------------------------------------------


@allure.epic("Backend")  # pyright: ignore[reportUnknownMemberType]
@allure.feature("Security")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Public read access")  # pyright: ignore[reportUnknownMemberType]
class TestReadPublic:
    def test_list_sequences_accessible_without_auth(self, client: TestClient) -> None:
        response = client.get("/sequences/")

        assert response.status_code == 200

    def test_retrieve_sequence_accessible_without_auth(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        with allure.step("Create a sequence with auth"):  # pyright: ignore[reportUnknownMemberType]
            create_resp = client.post(
                "/sequences/", json={"name": "Public"}, headers=auth_headers
            )
            sequence_id = create_resp.json()["id"]

        with allure.step("Retrieve the sequence without auth"):  # pyright: ignore[reportUnknownMemberType]
            response = client.get(f"/sequences/{sequence_id}")

        assert response.status_code == 200
        assert response.json()["name"] == "Public"
