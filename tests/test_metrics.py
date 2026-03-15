"""Tests for the /metrics (Prometheus) endpoint."""

import allure
from fastapi.testclient import TestClient


@allure.epic("Backend")  # pyright: ignore[reportUnknownMemberType]
@allure.feature("Observability")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Prometheus metrics")  # pyright: ignore[reportUnknownMemberType]
class TestMetrics:
    def test_metrics_returns_200(self, client: TestClient) -> None:
        response = client.get("/metrics")

        assert response.status_code == 200

    def test_metrics_content_type_is_prometheus_text_format(
        self, client: TestClient
    ) -> None:
        response = client.get("/metrics")

        assert "text/plain" in response.headers["content-type"]

    def test_metrics_exposes_http_request_duration(self, client: TestClient) -> None:
        client.get("/health")  # generate at least one sample
        response = client.get("/metrics")

        assert "http_request_duration_seconds" in response.text
