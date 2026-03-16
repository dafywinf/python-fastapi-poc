"""API route handlers for the client-side telemetry endpoint.

The handler receives batched telemetry events from the browser and records
them as Prometheus metrics, making them available via the existing /metrics
scrape endpoint.
"""

import logging

from fastapi import APIRouter
from prometheus_client import Counter, Histogram

from backend.exceptions import handle_exception
from backend.telemetry_schemas import TelemetryPayload, TelemetryResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

# ── Prometheus metrics ─────────────────────────────────────────────────────

_client_events_total = Counter(
    "client_telemetry_events_total",
    "Total number of client-side telemetry events received",
    ["type", "name"],
)

# Web Vital values are recorded in milliseconds (CLS is unitless score ×1000).
# Buckets cover the Good / Needs Improvement / Poor thresholds for LCP/INP/FID.
_web_vital_value = Histogram(
    "client_web_vital_value",
    "Web Vital metric value (milliseconds; CLS multiplied by 1000)",
    ["name"],
    buckets=[100, 200, 500, 1000, 2500, 4000, float("inf")],
)


# ── Route handler ──────────────────────────────────────────────────────────


@router.post("/", response_model=TelemetryResponse)
@handle_exception(logger)
def ingest(payload: TelemetryPayload) -> TelemetryResponse:
    """Accept a batch of client-side telemetry events.

    Validates the incoming JSON against the TelemetryPayload schema, then
    records each event as a Prometheus metric increment or observation.

    Args:
        payload: Validated telemetry batch from the browser.

    Returns:
        Confirmation with the count of recorded events.
    """
    for event in payload.events:
        _client_events_total.labels(type=event.type, name=event.name).inc()

        if event.type == "web_vital":
            _web_vital_value.labels(name=event.name).observe(event.value)

    logger.info(
        "Telemetry batch received",
        extra={
            "event_count": len(payload.events),
            "page_url": payload.page_url,
        },
    )

    return TelemetryResponse(recorded=len(payload.events))
