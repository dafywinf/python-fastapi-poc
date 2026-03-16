"""Tests for the POST /api/v1/telemetry endpoint."""

import allure
import pytest
from fastapi.testclient import TestClient
from httpx import Response

# ── Fixtures & helpers ─────────────────────────────────────────────────────


def _valid_event(
    event_type: str = "web_vital",
    name: str = "LCP",
    value: float = 1200.0,
) -> dict[str, object]:
    """Return a minimal valid TelemetryEvent dict."""
    return {
        "type": event_type,
        "name": name,
        "value": value,
        "timestamp": 1_700_000_000_000.0,
    }


def _post(client: TestClient, body: object) -> Response:
    return client.post("/api/v1/telemetry", json=body)  # type: ignore[return-value]


# ── Test classes ───────────────────────────────────────────────────────────


@allure.feature("Observability")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Telemetry ingestion")  # pyright: ignore[reportUnknownMemberType]
class TestTelemetryValidPayload:
    def test_single_event_returns_200(self, client: TestClient) -> None:
        payload = {"events": [_valid_event()]}

        response = _post(client, payload)

        assert response.status_code == 200

    def test_response_recorded_count_matches_event_count(
        self, client: TestClient
    ) -> None:
        events: list[dict[str, object]] = [
            _valid_event("web_vital", "LCP", 1500.0),
            _valid_event("web_vital", "CLS", 0.05),
            _valid_event("interaction", "button_click", 1.0),
        ]
        payload = {"events": events}  # pyright: ignore[reportUnknownVariableType]

        response = _post(client, payload)  # pyright: ignore[reportUnknownArgumentType]

        assert response.status_code == 200
        assert response.json()["recorded"] == 3

    def test_empty_events_list_returns_200(self, client: TestClient) -> None:
        payload: dict[str, object] = {"events": []}

        response = _post(client, payload)

        assert response.status_code == 200
        assert response.json()["recorded"] == 0

    def test_optional_fields_accepted(self, client: TestClient) -> None:
        payload = {
            "events": [_valid_event()],
            "session_id": "sess-abc123",
            "page_url": "https://example.com/sequences",
        }

        response = _post(client, payload)

        assert response.status_code == 200

    @pytest.mark.parametrize(
        "event_type",
        ["web_vital", "interaction", "error", "custom"],
    )
    def test_all_valid_event_types_accepted(
        self, client: TestClient, event_type: str
    ) -> None:
        payload = {"events": [_valid_event(event_type=event_type)]}

        response = _post(client, payload)

        assert response.status_code == 200

    def test_event_with_labels_accepted(self, client: TestClient) -> None:
        event = {**_valid_event(), "labels": {"route": "/sequences", "rating": "good"}}
        payload = {"events": [event]}

        response = _post(client, payload)

        assert response.status_code == 200


@allure.feature("Observability")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Telemetry validation")  # pyright: ignore[reportUnknownMemberType]
class TestTelemetryInvalidPayload:
    def test_missing_events_field_returns_422(self, client: TestClient) -> None:
        response = _post(client, {})

        assert response.status_code == 422

    def test_invalid_event_type_returns_422(self, client: TestClient) -> None:
        event = {**_valid_event(), "type": "unknown_type"}
        payload = {"events": [event]}

        response = _post(client, payload)

        assert response.status_code == 422

    def test_missing_required_name_field_returns_422(
        self, client: TestClient
    ) -> None:
        event = {k: v for k, v in _valid_event().items() if k != "name"}
        payload = {"events": [event]}

        response = _post(client, payload)

        assert response.status_code == 422

    def test_non_numeric_value_returns_422(self, client: TestClient) -> None:
        event = {**_valid_event(), "value": "not-a-number"}
        payload = {"events": [event]}

        response = _post(client, payload)

        assert response.status_code == 422

    def test_empty_name_returns_422(self, client: TestClient) -> None:
        event = {**_valid_event(), "name": ""}
        payload = {"events": [event]}

        response = _post(client, payload)

        assert response.status_code == 422

    def test_events_not_a_list_returns_422(self, client: TestClient) -> None:
        payload = {"events": "not-a-list"}

        response = _post(client, payload)

        assert response.status_code == 422


@allure.feature("Observability")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Telemetry metrics reflection")  # pyright: ignore[reportUnknownMemberType]
class TestTelemetryMetricsReflection:
    def test_web_vital_event_appears_in_prometheus_metrics(
        self, client: TestClient
    ) -> None:
        payload = {"events": [_valid_event("web_vital", "LCP", 2000.0)]}
        _post(client, payload)

        metrics_response = client.get("/metrics")

        assert metrics_response.status_code == 200
        assert "client_telemetry_events_total" in metrics_response.text

    def test_web_vital_histogram_appears_in_prometheus_metrics(
        self, client: TestClient
    ) -> None:
        payload = {"events": [_valid_event("web_vital", "INP", 300.0)]}
        _post(client, payload)

        metrics_response = client.get("/metrics")

        assert "client_web_vital_value" in metrics_response.text

    def test_interaction_event_increments_counter(
        self, client: TestClient
    ) -> None:
        payload = {"events": [_valid_event("interaction", "nav_click", 1.0)]}
        _post(client, payload)

        metrics_response = client.get("/metrics")

        assert "client_telemetry_events_total" in metrics_response.text
