"""Tests for the /health endpoint."""

import allure
from fastapi.testclient import TestClient


@allure.feature("Health")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Service liveness")  # pyright: ignore[reportUnknownMemberType]
def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
