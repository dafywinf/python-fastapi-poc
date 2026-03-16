/**
 * Client-side telemetry module.
 *
 * Collects Web Vitals and custom interaction events, buffers them in-memory,
 * and flushes them as a single JSON batch to POST /api/v1/telemetry every
 * FLUSH_INTERVAL_MS milliseconds (default 30 s).
 *
 * Additional flushes happen on page-hide and before-unload so events are not
 * lost when the user navigates away.
 *
 * Failures are swallowed silently — telemetry must never disrupt the UX.
 */

// ── Types ────────────────────────────────────────────────────────────────────

export interface TelemetryEvent {
  /** Broad category: web_vital | interaction | error | custom */
  type: 'web_vital' | 'interaction' | 'error' | 'custom'
  /** Specific metric name, e.g. "LCP", "button_click" */
  name: string
  /** Numeric measurement (ms for Web Vitals; unitless for counts) */
  value: number
  /** Client-side Unix timestamp in milliseconds */
  timestamp: number
  /** Optional low-cardinality extra dimensions */
  labels?: Record<string, string>
}

export interface TelemetryPayload {
  events: TelemetryEvent[]
  session_id?: string
  page_url?: string
}

export interface TelemetryResponse {
  recorded: number
}

// ── TelemetryClient ──────────────────────────────────────────────────────────

export class TelemetryClient {
  private readonly endpoint: string
  private readonly flushIntervalMs: number
  private readonly sessionId: string

  private buffer: TelemetryEvent[] = []
  private intervalId: ReturnType<typeof setInterval> | null = null
  private boundPageHideHandler: () => void
  private boundBeforeUnloadHandler: () => void

  constructor(endpoint = '/api/v1/telemetry', flushIntervalMs = 30_000) {
    this.endpoint = endpoint
    this.flushIntervalMs = flushIntervalMs
    this.sessionId = this._generateSessionId()
    this.boundPageHideHandler = () => this.flush()
    this.boundBeforeUnloadHandler = () => this.flush()
  }

  /**
   * Start the flush timer and register page-lifecycle event listeners.
   * Call once on application boot (e.g. in main.ts).
   */
  init(): void {
    this.intervalId = setInterval(() => this.flush(), this.flushIntervalMs)
    document.addEventListener('visibilitychange', this.boundPageHideHandler)
    window.addEventListener('beforeunload', this.boundBeforeUnloadHandler)
  }

  /**
   * Stop the flush timer and remove event listeners.
   * Useful in tests and when unmounting the application.
   */
  destroy(): void {
    if (this.intervalId !== null) {
      clearInterval(this.intervalId)
      this.intervalId = null
    }
    document.removeEventListener('visibilitychange', this.boundPageHideHandler)
    window.removeEventListener('beforeunload', this.boundBeforeUnloadHandler)
  }

  /**
   * Add a telemetry event to the in-memory buffer.
   * The buffer is drained on the next flush.
   */
  track(event: TelemetryEvent): void {
    this.buffer.push(event)
  }

  /**
   * Convenience helper for recording a Web Vital metric.
   *
   * @param name - Web Vital name (LCP, CLS, INP, FID, TTFB)
   * @param value - Measured value in milliseconds (CLS is score × 1000)
   */
  trackWebVital(name: string, value: number): void {
    this.track({
      type: 'web_vital',
      name,
      value,
      timestamp: Date.now(),
    })
  }

  /**
   * Convenience helper for recording a user interaction.
   *
   * @param name - Interaction name, e.g. "create_sequence_button_click"
   * @param durationMs - Optional duration in milliseconds
   */
  trackInteraction(name: string, durationMs = 0): void {
    this.track({
      type: 'interaction',
      name,
      value: durationMs,
      timestamp: Date.now(),
    })
  }

  /**
   * Drain the buffer and POST all queued events to the telemetry endpoint.
   * No-ops if the buffer is empty.  Failures are silently discarded — the
   * buffer has already been cleared before the fetch so events are not
   * double-counted on the next flush.
   */
  async flush(): Promise<void> {
    if (this.buffer.length === 0) return

    const events = this.buffer.splice(0) // drain atomically

    const payload: TelemetryPayload = {
      events,
      session_id: this.sessionId,
      page_url: typeof window !== 'undefined' ? window.location.href : undefined,
    }

    try {
      await fetch(this.endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        // keepalive: true allows the request to outlive page unload
        keepalive: true,
      })
    } catch {
      // Graceful failure: telemetry errors must never surface to the user.
      // Events have already been removed from the buffer — they are discarded
      // rather than re-queued to avoid unbounded growth during an outage.
    }
  }

  // ── Private ────────────────────────────────────────────────────────────────

  private _generateSessionId(): string {
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`
  }
}

// ── Singleton ─────────────────────────────────────────────────────────────────

/**
 * Application-wide telemetry client.
 * Call `telemetry.init()` once in main.ts, then `telemetry.track(...)` anywhere.
 */
export const telemetry = new TelemetryClient()
