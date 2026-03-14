"""End-to-end tests for the Prometheus + Grafana observability stack.

Requires the full platform and app to be running before executing:

    just platform-up   # starts PostgreSQL, Prometheus, and Grafana
    just dev           # starts the FastAPI app on port 8000

Run with:

    just e2e
"""

import allure
import httpx
import pytest

FASTAPI_URL = "http://localhost:8000"
PROMETHEUS_URL = "http://localhost:9090"
GRAFANA_URL = "http://localhost:3000"
DASHBOARD_UID = "fastapi-observability"


def _grafana() -> httpx.Client:
    return httpx.Client(base_url=GRAFANA_URL, timeout=10, auth=("admin", "admin"))


def _prometheus() -> httpx.Client:
    return httpx.Client(base_url=PROMETHEUS_URL, timeout=10)


@allure.feature("Observability")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Prometheus")  # pyright: ignore[reportUnknownMemberType]
@pytest.mark.e2e
class TestPrometheus:
    def test_fastapi_target_is_up(self) -> None:
        with _prometheus() as client:
            response = client.get("/api/v1/targets")

        assert response.status_code == 200
        targets = response.json()["data"]["activeTargets"]
        fastapi_targets = [t for t in targets if t["labels"].get("job") == "fastapi"]

        assert len(fastapi_targets) == 1, "Expected exactly one fastapi scrape target"
        assert fastapi_targets[0]["health"] == "up", (
            f"fastapi target is not up: {fastapi_targets[0]['lastError']}"
        )

    def test_request_duration_metric_has_data(self) -> None:
        # Generate at least one request so the metric is non-zero
        httpx.get(f"{FASTAPI_URL}/health")

        with _prometheus() as client:
            response = client.get(
                "/api/v1/query",
                params={"query": "http_request_duration_seconds_count"},
            )

        assert response.status_code == 200
        result = response.json()["data"]["result"]
        assert len(result) > 0, "http_request_duration_seconds_count has no data"


@allure.feature("Observability")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Grafana")  # pyright: ignore[reportUnknownMemberType]
@pytest.mark.e2e
class TestGrafana:
    def test_grafana_is_healthy(self) -> None:
        with _grafana() as client:
            response = client.get("/api/health")

        assert response.status_code == 200
        assert response.json()["database"] == "ok"

    def test_prometheus_datasource_is_healthy(self) -> None:
        with _grafana() as client:
            response = client.get("/api/datasources/name/Prometheus")
            assert response.status_code == 200, "Prometheus datasource not found"
            uid = response.json()["uid"]

            health = client.get(f"/api/datasources/uid/{uid}/health")

        assert health.status_code == 200
        assert health.json()["status"] == "OK", (
            f"Prometheus datasource unhealthy: {health.json()}"
        )

    def test_dashboard_is_provisioned(self) -> None:
        with _grafana() as client:
            response = client.get(f"/api/dashboards/uid/{DASHBOARD_UID}")

        assert response.status_code == 200, (
            f"Dashboard '{DASHBOARD_UID}' not found in Grafana"
        )
        title = response.json()["dashboard"]["title"]
        assert "FastAPI" in title, f"Unexpected dashboard title: {title}"

    def test_dashboard_panels_return_data(self) -> None:
        """Assert every panel query in the provisioned dashboard returns data.

        This test will fail if the dashboard PromQL expressions do not match
        the metric names produced by prometheus-fastapi-instrumentator — which
        is the known 'no data' issue with the currently committed dashboard.
        """
        # Generate traffic so Prometheus has recent samples to return
        for _ in range(5):
            httpx.get(f"{FASTAPI_URL}/health")
            httpx.get(f"{FASTAPI_URL}/sequences/")

        with _grafana() as client:
            # Resolve datasource UID
            ds_response = client.get("/api/datasources/name/Prometheus")
            assert ds_response.status_code == 200
            ds_uid = ds_response.json()["uid"]

            # Fetch dashboard panels
            dash_response = client.get(f"/api/dashboards/uid/{DASHBOARD_UID}")
            assert dash_response.status_code == 200
            panels = dash_response.json()["dashboard"].get("panels", [])

            # Collect all PromQL targets across all panels
            expressions: list[tuple[str, str]] = []
            for panel in panels:
                title = panel.get("title", "untitled")
                for target in panel.get("targets", []):
                    expr = target.get("expr", "").strip()
                    if expr:
                        expressions.append((title, expr))

            assert len(expressions) > 0, "No PromQL expressions found in dashboard"

            empty_panels: list[str] = []
            for panel_title, expr in expressions:
                result = client.post(
                    "/api/ds/query",
                    json={
                        "queries": [
                            {
                                "refId": "A",
                                "datasource": {"type": "prometheus", "uid": ds_uid},
                                "expr": expr,
                                "instant": True,
                                "range": False,
                                "maxDataPoints": 100,
                                "intervalMs": 15000,
                            }
                        ],
                        "from": "now-5m",
                        "to": "now",
                    },
                )
                frames = (
                    result.json()
                    .get("results", {})
                    .get("A", {})
                    .get("frames", [])
                )
                has_data = any(
                    len(f.get("data", {}).get("values", [[]])[0]) > 0
                    for f in frames
                    if f.get("data", {}).get("values")
                )
                if not has_data:
                    empty_panels.append(f"'{panel_title}': {expr}")

        assert empty_panels == [], (
            "The following dashboard panels returned no data:\n"
            + "\n".join(f"  - {p}" for p in empty_panels)
        )
