"""Pydantic V2 schemas for the client-side telemetry endpoint."""

from typing import Literal

from pydantic import BaseModel, Field


class TelemetryEvent(BaseModel):
    """A single client-side telemetry event.

    Attributes:
        type: Broad category of the event. Constrained to a known set of
            values to prevent Prometheus label-cardinality explosion.
        name: Specific metric name (e.g. "LCP", "button_click").
        value: Numeric measurement. Units are type/name dependent —
            milliseconds for Web Vitals, a count for interactions.
        timestamp: Client-side Unix timestamp in milliseconds.
        labels: Optional extra dimensions. Must remain low-cardinality.
    """

    type: Literal["web_vital", "interaction", "error", "custom"]
    name: str = Field(min_length=1, max_length=128)
    value: float
    timestamp: float
    labels: dict[str, str] = Field(default_factory=dict)


class TelemetryPayload(BaseModel):
    """Batch of client-side telemetry events sent from the browser.

    Attributes:
        events: One or more events collected during the flush interval.
        session_id: Optional opaque browser-session identifier.
        page_url: URL of the page that produced the events.
    """

    events: list[TelemetryEvent]
    session_id: str | None = None
    page_url: str | None = None


class TelemetryResponse(BaseModel):
    """Confirmation returned after successfully processing a telemetry batch.

    Attributes:
        recorded: Number of events accepted and recorded as Prometheus metrics.
    """

    recorded: int
