/**
 * Tests for the sequences API client.
 *
 * fetch is replaced with a lightweight mock so tests run in jsdom without a
 * real server.  Each suite restores the mock after every test.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import * as allure from 'allure-js-commons'
import { sequencesApi } from '../api/sequences'
import type { Sequence } from '../types/sequence'

// ── Fixtures ─────────────────────────────────────────────────────────────────

const SEQUENCE: Sequence = {
  id: 1,
  name: 'Alpha',
  description: 'A test sequence',
  created_at: '2026-01-01T00:00:00Z',
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function mockFetch(body: unknown, status = 200): void {
  const response = new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response))
}

function mockFetchError(status: number, detail: string): void {
  const response = new Response(JSON.stringify({ detail }), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response))
}

// ── Test suites ───────────────────────────────────────────────────────────────

describe('sequencesApi.list', () => {
  beforeEach(() => {
    allure.feature('Sequences API')
    allure.story('List')
  })
  afterEach(() => vi.unstubAllGlobals())

  it('returns an array of sequences on success', async () => {
    mockFetch([SEQUENCE])

    const result = await sequencesApi.list()

    expect(result).toHaveLength(1)
    expect(result[0]).toMatchObject({ id: 1, name: 'Alpha' })
  })

  it('calls the correct endpoint', async () => {
    mockFetch([])

    await sequencesApi.list()

    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/sequences/',
      expect.objectContaining({ headers: { 'Content-Type': 'application/json' } }),
    )
  })

  it('returns an empty array when no sequences exist', async () => {
    mockFetch([])

    const result = await sequencesApi.list()

    expect(result).toEqual([])
  })
})

describe('sequencesApi.get', () => {
  beforeEach(() => {
    allure.feature('Sequences API')
    allure.story('Retrieve')
  })
  afterEach(() => vi.unstubAllGlobals())

  it('returns the sequence for a valid id', async () => {
    mockFetch(SEQUENCE)

    const result = await sequencesApi.get(1)

    expect(result).toMatchObject({ id: 1, name: 'Alpha' })
  })

  it('calls the correct endpoint with the id', async () => {
    mockFetch(SEQUENCE)

    await sequencesApi.get(42)

    expect(vi.mocked(fetch)).toHaveBeenCalledWith('/sequences/42', expect.anything())
  })

  it('throws an error for a 404 response', async () => {
    mockFetchError(404, 'Sequence 99 not found')

    await expect(sequencesApi.get(99)).rejects.toThrow('Sequence 99 not found')
  })
})

describe('sequencesApi.create', () => {
  beforeEach(() => {
    allure.feature('Sequences API')
    allure.story('Create')
  })
  afterEach(() => vi.unstubAllGlobals())

  it('posts to the sequences endpoint and returns the created record', async () => {
    mockFetch(SEQUENCE, 201)

    await allure.step('Send create request', async () => {
      const result = await sequencesApi.create({ name: 'Alpha', description: 'A test sequence' })

      await allure.step('Verify response shape', async () => {
        expect(result).toMatchObject({ id: 1, name: 'Alpha' })
      })

      await allure.step('Verify request was POST to /sequences/', async () => {
        expect(vi.mocked(fetch)).toHaveBeenCalledWith(
          '/sequences/',
          expect.objectContaining({
            method: 'POST',
            body: JSON.stringify({ name: 'Alpha', description: 'A test sequence' }),
          }),
        )
      })
    })
  })

  it('sends null description when not provided', async () => {
    mockFetch({ ...SEQUENCE, description: null }, 201)

    await sequencesApi.create({ name: 'Beta' })

    const body = JSON.parse((vi.mocked(fetch).mock.calls[0]![1] as RequestInit).body as string)
    expect(body.description).toBeUndefined()
  })

  it('throws when the server returns a 422', async () => {
    mockFetchError(422, 'Field required')

    await expect(sequencesApi.create({ name: '' })).rejects.toThrow('Field required')
  })
})

describe('sequencesApi.update', () => {
  beforeEach(() => {
    allure.feature('Sequences API')
    allure.story('Partial Update')
  })
  afterEach(() => vi.unstubAllGlobals())

  it('sends a PATCH request and returns the updated record', async () => {
    const updated = { ...SEQUENCE, name: 'Updated' }
    mockFetch(updated)

    await allure.step('Send update request', async () => {
      const result = await sequencesApi.update(1, { name: 'Updated' })

      await allure.step('Verify updated name in response', async () => {
        expect(result.name).toBe('Updated')
      })

      await allure.step('Verify PATCH method and endpoint', async () => {
        expect(vi.mocked(fetch)).toHaveBeenCalledWith(
          '/sequences/1',
          expect.objectContaining({ method: 'PATCH' }),
        )
      })
    })
  })

  it('throws for a 404 response', async () => {
    mockFetchError(404, 'Sequence 99 not found')

    await expect(sequencesApi.update(99, { name: 'Ghost' })).rejects.toThrow(
      'Sequence 99 not found',
    )
  })
})

describe('sequencesApi.delete', () => {
  beforeEach(() => {
    allure.feature('Sequences API')
    allure.story('Delete')
  })
  afterEach(() => vi.unstubAllGlobals())

  it('sends a DELETE request and resolves with undefined on 204', async () => {
    mockFetch(null, 204)

    await allure.step('Send delete request', async () => {
      const result = await sequencesApi.delete(1)

      await allure.step('Verify response is undefined', async () => {
        expect(result).toBeUndefined()
      })

      await allure.step('Verify DELETE method and endpoint', async () => {
        expect(vi.mocked(fetch)).toHaveBeenCalledWith(
          '/sequences/1',
          expect.objectContaining({ method: 'DELETE' }),
        )
      })
    })
  })

  it('throws for a 404 response', async () => {
    mockFetchError(404, 'Sequence 99 not found')

    await expect(sequencesApi.delete(99)).rejects.toThrow('Sequence 99 not found')
  })
})
