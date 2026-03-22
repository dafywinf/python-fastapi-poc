/**
 * Tests for the routines API client.
 *
 * fetch is replaced with a lightweight mock so tests run in jsdom without a
 * real server. Each suite restores the mock after every test.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as allure from 'allure-js-commons'
import { routinesApi } from '../api/routines'

// ── Helpers ───────────────────────────────────────────────────────────────────

function mockFetch(body: unknown, status = 200): void {
  const response = new Response(
    status === 204 ? null : JSON.stringify(body),
    { status, headers: { 'Content-Type': 'application/json' } },
  )
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response))
}

afterEach(() => vi.unstubAllGlobals())

// ── Test suites ───────────────────────────────────────────────────────────────

describe('routinesApi', () => {
  beforeEach(() => {
    allure.epic('Frontend')
    allure.feature('routinesApi')
  })

  it('list calls GET /routines/', async () => {
    mockFetch([])
    await routinesApi.list()
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/routines/',
      expect.objectContaining({ headers: expect.objectContaining({ 'Content-Type': 'application/json' }) }),
    )
  })

  it('create calls POST /routines/', async () => {
    mockFetch({ id: 1, name: 'Test', actions: [] }, 201)
    await routinesApi.create({ name: 'Test', schedule_type: 'manual', schedule_config: null })
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/routines/',
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('delete calls DELETE and returns undefined', async () => {
    mockFetch(null, 204)
    const result = await routinesApi.delete(1)
    expect(result).toBeUndefined()
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/routines/1',
      expect.objectContaining({ method: 'DELETE' }),
    )
  })

  it('runNow calls POST /routines/{id}/run', async () => {
    mockFetch({ execution_id: 42 }, 202)
    const result = await routinesApi.runNow(5)
    expect(result.execution_id).toBe(42)
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/routines/5/run',
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('executionHistory builds correct URL with params', async () => {
    mockFetch([])
    await routinesApi.executionHistory(20, 3)
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      expect.stringContaining('limit=20'),
      expect.anything(),
    )
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      expect.stringContaining('routine_id=3'),
      expect.anything(),
    )
  })
})
