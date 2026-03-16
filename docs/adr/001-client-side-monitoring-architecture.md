# ADR 001: Client-Side Monitoring Architecture — Backend-as-Proxy

**Date:** 2026-03-16
**Status:** Accepted
**Deciders:** Engineering Team

---

## Context

We need to collect real-user monitoring (RUM) data — Web Vitals (LCP, CLS, INP, FID, TTFB),
custom interaction timings, and client-side errors — and surface them in the existing Grafana
observability stack alongside backend metrics.

Several patterns exist for shipping client-side telemetry to a metrics backend:

| Pattern | Description |
|---|---|
| **Direct to Prometheus Pushgateway** | Browser posts directly to a Pushgateway; Prometheus scrapes it |
| **Third-party SaaS RUM** | Events sent to Datadog, New Relic, etc. |
| **Backend-as-Proxy** | Browser posts to the FastAPI application; backend records Prometheus metrics |
| **OpenTelemetry Collector** | Browser sends OTLP; a collector translates to Prometheus |

---

## Decision

We adopt the **Backend-as-Proxy** pattern:

1. The browser buffers telemetry events locally (30-second flush interval, plus flush on
   page-hide and before-unload).
2. Events are posted as a JSON batch to `POST /api/v1/telemetry` on the FastAPI backend.
3. The FastAPI handler validates the payload via Pydantic V2 models and records the events
   as Prometheus metrics using `prometheus_client`.
4. Prometheus scrapes `/metrics` (already configured) and the data flows into Grafana.

---

## Rationale

### Security benefits

- **No CORS exposure of a metrics endpoint.** A Pushgateway or OTLP collector must be
  publicly reachable; the Backend-as-Proxy reuses the existing application URL and TLS
  certificate, and can be placed behind any existing authentication middleware without extra
  configuration.
- **Input validation.** Every telemetry payload is validated by Pydantic before metrics are
  recorded. Malformed or out-of-range values are rejected with `422 Unprocessable Entity`
  rather than silently corrupting metrics.
- **No new network surface area.** The telemetry route lives on the same origin as the API,
  so browser same-origin policies, CSPs, and API gateways require no changes.

### Reduced infrastructure complexity

- **No new services.** The Pushgateway, OpenTelemetry Collector, and third-party agents are
  all omitted. Prometheus already scrapes `/metrics`; custom metrics are simply added to the
  same registry.
- **No new credentials or secrets.** Third-party SaaS RUM requires API keys; the
  Backend-as-Proxy requires none.
- **Grafana reuse.** All telemetry metrics appear alongside existing FastAPI metrics in
  Grafana. No additional data sources, dashboards, or provisioning files are needed.

### Trade-offs accepted

- **Backend latency.** Telemetry batches add a small amount of POST load to FastAPI. This is
  mitigated by the 30-second buffer (one request per 30 s per browser tab) and the sync
  thread-pool architecture, which means telemetry handling never blocks the event loop.
- **Cardinality risk.** Prometheus labels from arbitrary client strings could cause label
  explosion. Mitigation: the `type` field is constrained to a `Literal` enum in Pydantic, and
  `name` values for web vitals are similarly restricted. Custom labels are disallowed in the
  current schema.
- **Data loss on failure.** If the backend is unavailable, buffered events are silently
  discarded (never re-queued). This is acceptable because RUM data is statistical — a small
  loss rate does not compromise the usefulness of aggregate percentiles.

---

## Consequences

- `POST /api/v1/telemetry` is added to the FastAPI application.
- `prometheus_client` is added as a direct dependency (it is already a transitive dependency
  via `prometheus-fastapi-instrumentator`; making it direct makes the usage explicit).
- A `TelemetryClient` TypeScript class is added to the frontend under
  `src/telemetry/telemetry.ts`. It is initialised once in `src/main.ts`.
- The existing Prometheus scrape configuration (`monitoring/prometheus/prometheus.yml`) and
  `docker-compose.yml` monitoring profile require no changes.

---

## Alternatives Rejected

### Prometheus Pushgateway

Rejected because it requires a publicly accessible additional service, complicates the network
topology, and does not validate incoming data.

### Third-party SaaS RUM (Datadog, New Relic, etc.)

Rejected because it introduces external dependencies, recurring cost, and requires sending
user-behaviour data to a third party.

### OpenTelemetry Collector

Rejected because it adds an additional process to operate and configure. It is the correct
long-term path if telemetry volume grows significantly, and this ADR should be revisited at
that point.
