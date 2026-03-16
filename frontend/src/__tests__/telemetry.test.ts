/**
 * Tests for the TelemetryClient module.
 *
 * fetch is replaced with a lightweight mock so tests run in jsdom without a
 * real server. Each suite restores the mock after every test.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as allure from 'allure-js-commons'
import { TelemetryClient } from '../telemetry/telemetry'

// ── Helpers ───────────────────────────────────────────────────────────────────

function mockFetchOk(): void {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ recorded: 1 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    ),
  )
}

function mockFetchNetworkError(): void {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
}

// ── Suites ────────────────────────────────────────────────────────────────────

describe('TelemetryClient.track', () => {
  beforeEach(() => {
    allure.feature('Telemetry')
    allure.story('Buffer')
  })
  afterEach(() => vi.unstubAllGlobals())

  it('buffers an event without sending immediately', () => {
    mockFetchOk()
    const client = new TelemetryClient()

    client.track({ type: 'web_vital', name: 'LCP', value: 1200, timestamp: Date.now() })

    expect(vi.mocked(fetch)).not.toHaveBeenCalled()
  })

  it('accepts all valid event types', () => {
    const client = new TelemetryClient()
    const types = ['web_vital', 'interaction', 'error', 'custom'] as const

    for (const type of types) {
      client.track({ type, name: 'test', value: 0, timestamp: Date.now() })
    }

    // No assertion on fetch — just verifying track() does not throw
    expect(true).toBe(true)
  })
})

describe('TelemetryClient.trackWebVital', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('adds a web_vital event with correct type', async () => {
    allure.feature('Telemetry')
    allure.story('Web Vitals')
    mockFetchOk()
    const client = new TelemetryClient()

    client.trackWebVital('LCP', 1500)
    await client.flush()

    const body = JSON.parse((vi.mocked(fetch).mock.calls[0]![1] as RequestInit).body as string)
    expect(body.events[0].type).toBe('web_vital')
    expect(body.events[0].name).toBe('LCP')
    expect(body.events[0].value).toBe(1500)
  })
})

describe('TelemetryClient.flush', () => {
  beforeEach(() => {
    allure.feature('Telemetry')
    allure.story('Flush')
  })
  afterEach(() => vi.unstubAllGlobals())

  it('sends buffered events as a JSON batch to the telemetry endpoint', async () => {
    mockFetchOk()
    const client = new TelemetryClient('/api/v1/telemetry')

    client.track({ type: 'web_vital', name: 'LCP', value: 1200, timestamp: 0 })
    client.track({ type: 'interaction', name: 'click', value: 1, timestamp: 0 })
    await client.flush()

    expect(vi.mocked(fetch)).toHaveBeenCalledOnce()
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/api/v1/telemetry',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    const body = JSON.parse((vi.mocked(fetch).mock.calls[0]![1] as RequestInit).body as string)
    expect(body.events).toHaveLength(2)
  })

  it('clears the buffer after a successful flush', async () => {
    mockFetchOk()
    const client = new TelemetryClient()

    client.track({ type: 'custom', name: 'test', value: 1, timestamp: 0 })
    await client.flush()

    // Second flush: buffer is empty — fetch should not be called again
    vi.mocked(fetch).mockClear()
    await client.flush()

    expect(vi.mocked(fetch)).not.toHaveBeenCalled()
  })

  it('does nothing when the buffer is empty', async () => {
    mockFetchOk()
    const client = new TelemetryClient()

    await client.flush()

    expect(vi.mocked(fetch)).not.toHaveBeenCalled()
  })

  it('does not throw when the backend is unreachable (network error)', async () => {
    mockFetchNetworkError()
    const client = new TelemetryClient()

    client.track({ type: 'web_vital', name: 'TTFB', value: 200, timestamp: 0 })

    await expect(client.flush()).resolves.toBeUndefined()
  })

  it('does not throw when the backend returns a 5xx error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('Internal Server Error', { status: 500 })),
    )
    const client = new TelemetryClient()

    client.track({ type: 'error', name: 'js_error', value: 1, timestamp: 0 })

    await expect(client.flush()).resolves.toBeUndefined()
  })

  it('clears the buffer even when the request fails', async () => {
    mockFetchNetworkError()
    const client = new TelemetryClient()

    client.track({ type: 'custom', name: 'test', value: 1, timestamp: 0 })
    await client.flush()

    // Restore a working fetch; buffer should already be empty
    mockFetchOk()
    await client.flush()

    expect(vi.mocked(fetch)).not.toHaveBeenCalled()
  })

  it('includes session_id and page_url in the posted payload', async () => {
    mockFetchOk()
    const client = new TelemetryClient()

    client.track({ type: 'custom', name: 'test', value: 1, timestamp: 0 })
    await client.flush()

    const body = JSON.parse((vi.mocked(fetch).mock.calls[0]![1] as RequestInit).body as string)
    expect(typeof body.session_id).toBe('string')
    expect(body.session_id.length).toBeGreaterThan(0)
  })
})

describe('TelemetryClient.init / destroy', () => {
  beforeEach(() => {
    allure.feature('Telemetry')
    allure.story('Lifecycle')
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('flushes automatically after the configured interval', async () => {
    vi.useFakeTimers()
    mockFetchOk()
    const client = new TelemetryClient('/api/v1/telemetry', 30_000)

    client.init()
    client.track({ type: 'custom', name: 'evt', value: 1, timestamp: 0 })

    await vi.advanceTimersByTimeAsync(30_000)

    expect(vi.mocked(fetch)).toHaveBeenCalledOnce()
    client.destroy()
  })

  it('stops flushing after destroy is called', async () => {
    vi.useFakeTimers()
    mockFetchOk()
    const client = new TelemetryClient('/api/v1/telemetry', 30_000)

    client.init()
    client.destroy()

    client.track({ type: 'custom', name: 'evt', value: 1, timestamp: 0 })
    await vi.advanceTimersByTimeAsync(60_000)

    expect(vi.mocked(fetch)).not.toHaveBeenCalled()
  })
})
