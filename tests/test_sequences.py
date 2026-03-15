"""Tests for the /sequences CRUD endpoints."""

import allure
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_sequence(
    client: TestClient,
    auth_headers: dict[str, str],
    name: str = "Alpha",
    description: str | None = "desc",
) -> dict[str, object]:
    """POST a sequence with auth and return the parsed response body.

    Args:
        client: The test HTTP client.
        auth_headers: Authorization headers containing a valid Bearer token.
        name: Sequence name (default ``"Alpha"``).
        description: Optional description (default ``"desc"``).

    Returns:
        The parsed JSON response body of the created Sequence.
    """
    response = client.post(
        "/sequences/",
        json={"name": name, "description": description},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# POST /sequences/
# ---------------------------------------------------------------------------


@allure.epic("Backend")  # pyright: ignore[reportUnknownMemberType]
@allure.feature("Sequences")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Create")  # pyright: ignore[reportUnknownMemberType]
class TestCreateSequence:
    def test_creates_sequence_with_all_fields(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/sequences/",
            json={"name": "Alpha", "description": "My description"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Alpha"
        assert body["description"] == "My description"
        assert "id" in body
        assert "created_at" in body

    def test_creates_sequence_without_description(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/sequences/", json={"name": "Beta"}, headers=auth_headers
        )

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Beta"
        assert body["description"] is None

    def test_returns_422_when_name_missing(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/sequences/", json={"description": "no name"}, headers=auth_headers
        )

        assert response.status_code == 422

    def test_returns_422_when_body_empty(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.post("/sequences/", json={}, headers=auth_headers)

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /sequences/
# ---------------------------------------------------------------------------


@allure.epic("Backend")  # pyright: ignore[reportUnknownMemberType]
@allure.feature("Sequences")  # pyright: ignore[reportUnknownMemberType]
@allure.story("List")  # pyright: ignore[reportUnknownMemberType]
class TestListSequences:
    def test_returns_empty_list_when_no_sequences(self, client: TestClient) -> None:
        response = client.get("/sequences/")

        assert response.status_code == 200
        assert response.json() == []

    def test_returns_all_created_sequences(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        _create_sequence(client, auth_headers, name="Alpha")
        _create_sequence(client, auth_headers, name="Beta")

        response = client.get("/sequences/")

        assert response.status_code == 200
        names = {s["name"] for s in response.json()}
        assert names == {"Alpha", "Beta"}

    def test_response_contains_expected_fields(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        _create_sequence(client, auth_headers, name="Gamma")

        body = client.get("/sequences/").json()

        assert len(body) == 1
        keys = set(body[0].keys())
        assert keys == {"id", "name", "description", "created_at"}


# ---------------------------------------------------------------------------
# GET /sequences/{id}
# ---------------------------------------------------------------------------


@allure.epic("Backend")  # pyright: ignore[reportUnknownMemberType]
@allure.feature("Sequences")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Retrieve")  # pyright: ignore[reportUnknownMemberType]
class TestRetrieveSequence:
    def test_retrieves_existing_sequence(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        created = _create_sequence(client, auth_headers, name="Delta")
        sequence_id = created["id"]

        response = client.get(f"/sequences/{sequence_id}")

        assert response.status_code == 200
        assert response.json()["id"] == sequence_id
        assert response.json()["name"] == "Delta"

    def test_returns_404_for_unknown_id(self, client: TestClient) -> None:
        response = client.get("/sequences/99999")

        assert response.status_code == 404
        assert "99999" in response.json()["detail"]


# ---------------------------------------------------------------------------
# PATCH /sequences/{id}
# ---------------------------------------------------------------------------


@allure.epic("Backend")  # pyright: ignore[reportUnknownMemberType]
@allure.feature("Sequences")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Partial Update")  # pyright: ignore[reportUnknownMemberType]
class TestPartialUpdateSequence:
    def test_updates_name(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        created = _create_sequence(client, auth_headers, name="Original")
        sequence_id = created["id"]

        response = client.patch(
            f"/sequences/{sequence_id}", json={"name": "Updated"}, headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated"
        assert response.json()["description"] == created["description"]

    def test_updates_description(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        created = _create_sequence(
            client, auth_headers, name="Stable", description="old"
        )
        sequence_id = created["id"]

        response = client.patch(
            f"/sequences/{sequence_id}",
            json={"description": "new"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["description"] == "new"
        assert response.json()["name"] == "Stable"

    def test_updates_both_fields(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        created = _create_sequence(
            client, auth_headers, name="Old", description="old desc"
        )
        sequence_id = created["id"]

        response = client.patch(
            f"/sequences/{sequence_id}",
            json={"name": "New", "description": "new desc"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["name"] == "New"
        assert response.json()["description"] == "new desc"

    def test_empty_payload_leaves_record_unchanged(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        created = _create_sequence(
            client, auth_headers, name="Unchanged", description="same"
        )
        sequence_id = created["id"]

        response = client.patch(
            f"/sequences/{sequence_id}", json={}, headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Unchanged"
        assert response.json()["description"] == "same"

    def test_returns_404_for_unknown_id(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.patch(
            "/sequences/99999", json={"name": "Ghost"}, headers=auth_headers
        )

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /sequences/{id}
# ---------------------------------------------------------------------------


@allure.epic("Backend")  # pyright: ignore[reportUnknownMemberType]
@allure.feature("Sequences")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Delete")  # pyright: ignore[reportUnknownMemberType]
class TestDeleteSequence:
    def test_deletes_existing_sequence(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        created = _create_sequence(client, auth_headers, name="ToDelete")
        sequence_id = created["id"]

        response = client.delete(f"/sequences/{sequence_id}", headers=auth_headers)

        assert response.status_code == 204
        assert response.content == b""

    def test_sequence_no_longer_retrievable_after_delete(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        created = _create_sequence(client, auth_headers, name="Gone")
        sequence_id = created["id"]

        client.delete(f"/sequences/{sequence_id}", headers=auth_headers)
        response = client.get(f"/sequences/{sequence_id}")

        assert response.status_code == 404

    def test_returns_404_for_unknown_id(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.delete("/sequences/99999", headers=auth_headers)

        assert response.status_code == 404
