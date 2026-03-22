"""End-to-end tests for the Prometheus + Grafana + Loki observability stack.

Requires the full platform and app to be running before executing:

    just platform-up   # starts PostgreSQL, Prometheus, Grafana, and Loki
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
LOKI_URL = "http://localhost:3100"
DASHBOARD_UID = "fastapi-observability"
LOKI_DASHBOARD_UID = "fastapi-loki"


def _grafana() -> httpx.Client:
    return httpx.Client(base_url=GRAFANA_URL, timeout=10, auth=("admin", "admin"))


def _prometheus() -> httpx.Client:
    return httpx.Client(base_url=PROMETHEUS_URL, timeout=10)


def _loki() -> httpx.Client:
    """Return an httpx client configured for the Loki API."""
    return httpx.Client(base_url=LOKI_URL, timeout=10)


@allure.epic("Backend")  # pyright: ignore[reportUnknownMemberType]
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
        assert (
            fastapi_targets[0]["health"] == "up"
        ), f"fastapi target is not up: {fastapi_targets[0]['lastError']}"

    def test_request_duration_metric_has_data(self) -> None:
        import time

        # Generate a request then poll until Prometheus has scraped it.
        httpx.get(f"{FASTAPI_URL}/health")

        deadline = time.time() + 30
        result: list[object] = []
        while time.time() < deadline:
            with _prometheus() as client:
                response = client.get(
                    "/api/v1/query",
                    params={"query": "http_request_duration_seconds_count"},
                )
            result = response.json()["data"]["result"]
            if result:
                break
            time.sleep(2)

        assert len(result) > 0, "http_request_duration_seconds_count has no data"


@allure.epic("Backend")  # pyright: ignore[reportUnknownMemberType]
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
        assert (
            health.json()["status"] == "OK"
        ), f"Prometheus datasource unhealthy: {health.json()}"

    def test_dashboard_is_provisioned(self) -> None:
        with _grafana() as client:
            response = client.get(f"/api/dashboards/uid/{DASHBOARD_UID}")

        assert (
            response.status_code == 200
        ), f"Dashboard '{DASHBOARD_UID}' not found in Grafana"
        title = response.json()["dashboard"]["title"]
        assert "FastAPI" in title, f"Unexpected dashboard title: {title}"

    def test_dashboard_panels_return_data(self) -> None:
        """Assert every panel query in the provisioned dashboard returns data."""
        import time

        # Generate traffic then wait for Prometheus to scrape it.
        # The scrape interval is 15 s; polling avoids a hard sleep.
        for _ in range(5):
            httpx.get(f"{FASTAPI_URL}/health")
            httpx.get(f"{FASTAPI_URL}/routines/")

        # Wait until Prometheus has scraped non-/metrics handler data AND
        # rate() resolves (requires ≥2 scrapes at 15 s interval).
        # Poll on both conditions together to avoid false-positive on
        # Prometheus's own scrape of /metrics satisfying a broader query.
        deadline = time.time() + 45
        while time.time() < deadline:
            _q = 'http_requests_total{job="fastapi",handler!="/metrics"}'
            with _prometheus() as prom:
                counter = prom.get(
                    "/api/v1/query",
                    params={"query": f"sum({_q})"},
                )
                rate_q = prom.get(
                    "/api/v1/query",
                    params={"query": f"rate({_q}[1m])"},
                )
            counter_ok = bool(counter.json().get("data", {}).get("result"))
            rate_ok = bool(rate_q.json().get("data", {}).get("result"))
            if counter_ok and rate_ok:
                break
            time.sleep(2)
        else:
            pytest.fail(
                "Timed out waiting for Prometheus data — "
                "ensure the app has been running for at least 30 s"
            )

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
                frames = result.json().get("results", {}).get("A", {}).get("frames", [])
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


@allure.epic("Backend")  # pyright: ignore[reportUnknownMemberType]
@allure.feature("Observability")  # pyright: ignore[reportUnknownMemberType]
@allure.story("Loki")  # pyright: ignore[reportUnknownMemberType]
@pytest.mark.e2e
class TestLoki:
    def test_loki_is_ready(self) -> None:
        with _loki() as client:
            response = client.get("/ready")
        assert response.status_code == 200
        assert response.text.strip() == "ready"

    def test_loki_receives_fastapi_logs(self) -> None:
        import time

        httpx.get(f"{FASTAPI_URL}/health")
        time.sleep(2)  # allow Loki ingester to make logs queryable

        with _loki() as client:
            response = client.get(
                "/loki/api/v1/query_range",
                params={
                    "query": '{application="fastapi"}',
                    "limit": 10,
                    "start": str(int((time.time() - 300) * 1_000_000_000)),
                    "end": str(int(time.time() * 1_000_000_000)),
                },
            )

        assert response.status_code == 200
        result = response.json()["data"]["result"]
        assert len(result) > 0, "No log streams found for {application='fastapi'}"

    def test_loki_datasource_is_healthy(self) -> None:
        with _grafana() as client:
            response = client.get("/api/datasources/name/Loki")
            assert response.status_code == 200, "Loki datasource not found in Grafana"
            uid = response.json()["uid"]
            health = client.get(f"/api/datasources/uid/{uid}/health")
        assert health.status_code == 200
        assert (
            health.json()["status"] == "OK"
        ), f"Loki datasource unhealthy: {health.json()}"

    def test_loki_dashboard_is_provisioned(self) -> None:
        with _grafana() as client:
            response = client.get(f"/api/dashboards/uid/{LOKI_DASHBOARD_UID}")
        assert (
            response.status_code == 200
        ), f"Dashboard '{LOKI_DASHBOARD_UID}' not found"
        assert response.json()["dashboard"]["title"] == "FastAPI Logs"

    def test_loki_dashboard_panels_have_data(self) -> None:
        """Assert every LogQL panel in the Loki dashboard returns data.

        Mirrors the existing test_dashboard_panels_return_data for Prometheus,
        but uses the Loki datasource and Grafana's /api/ds/query endpoint with
        LogQL instant queries.
        """
        import time

        # Generate INFO traffic so the app emits log lines that Loki ingests
        for _ in range(5):
            httpx.get(f"{FASTAPI_URL}/health")
            httpx.get(f"{FASTAPI_URL}/routines/")

        # Push a synthetic ERROR entry so the Error Count panel has data.
        # This exercises the full Loki ingestion path for error-level logs
        # without requiring a real 500 from the app (which @handle_exception
        # would only emit for non-HTTPExceptions — never in a clean run).
        ts = str(int(time.time() * 1_000_000_000))
        with _loki() as loki_client:
            loki_client.post(
                "/loki/api/v1/push",
                json={
                    "streams": [
                        {
                            "stream": {"application": "fastapi"},
                            "values": [
                                [ts, '{"levelname": "ERROR", "message": "e2e test"}']
                            ],
                        }
                    ]
                },
            )

        time.sleep(2)  # allow Loki ingester to make logs queryable

        with _grafana() as client:
            # Resolve Loki datasource UID
            ds_response = client.get("/api/datasources/name/Loki")
            assert ds_response.status_code == 200, "Loki datasource not found"
            ds_uid = ds_response.json()["uid"]

            # Fetch Loki dashboard panels
            dash_response = client.get(f"/api/dashboards/uid/{LOKI_DASHBOARD_UID}")
            assert dash_response.status_code == 200
            panels = dash_response.json()["dashboard"].get("panels", [])

            # Collect all LogQL expressions across all panels
            expressions: list[tuple[str, str]] = []
            for panel in panels:
                title = panel.get("title", "untitled")
                for target in panel.get("targets", []):
                    expr = target.get("expr", "").strip()
                    if expr:
                        expressions.append((title, expr))

            assert len(expressions) > 0, "No LogQL expressions found in Loki dashboard"

            empty_panels: list[str] = []
            for panel_title, expr in expressions:
                result = client.post(
                    "/api/ds/query",
                    json={
                        "queries": [
                            {
                                "refId": "A",
                                "datasource": {"type": "loki", "uid": ds_uid},
                                "expr": expr,
                                "instant": True,
                                "range": False,
                                "maxLines": 10,
                                "intervalMs": 2000,
                            }
                        ],
                        "from": "now-5m",
                        "to": "now",
                    },
                )
                frames = result.json().get("results", {}).get("A", {}).get("frames", [])
                has_data = any(
                    len(f.get("data", {}).get("values", [[]])[0]) > 0
                    for f in frames
                    if f.get("data", {}).get("values")
                )
                if not has_data:
                    empty_panels.append(f"'{panel_title}': {expr}")

        assert empty_panels == [], (
            "The following Loki dashboard panels returned no data:\n"
            + "\n".join(f"  - {p}" for p in empty_panels)
        )
