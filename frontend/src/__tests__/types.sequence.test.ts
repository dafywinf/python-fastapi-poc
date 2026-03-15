/**
 * Structural / contract tests for Sequence types.
 *
 * These verify that the TypeScript types match the shape returned by the API
 * and that runtime objects can be used wherever the type is expected.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import * as allure from 'allure-js-commons'
import type { Sequence, SequenceCreate, SequenceUpdate } from '../types/sequence'

describe('Sequence type contract', () => {
  beforeEach(() => {
    allure.epic('Frontend')
    allure.feature('Sequences')
    allure.story('Contract')
  })

  it('accepts a fully-populated sequence object', () => {
    const seq: Sequence = {
      id: 1,
      name: 'Alpha',
      description: 'desc',
      created_at: '2026-01-01T00:00:00Z',
    }

    expect(seq.id).toBe(1)
    expect(seq.name).toBe('Alpha')
    expect(seq.description).toBe('desc')
    expect(seq.created_at).toMatch(/^\d{4}-/)
  })

  it('accepts null description in Sequence', () => {
    const seq: Sequence = {
      id: 2,
      name: 'Beta',
      description: null,
      created_at: '2026-01-01T00:00:00Z',
    }

    expect(seq.description).toBeNull()
  })

  it('SequenceCreate requires only name', () => {
    const payload: SequenceCreate = { name: 'Gamma' }

    expect(payload.name).toBe('Gamma')
    expect(payload.description).toBeUndefined()
  })

  it('SequenceCreate accepts an optional description', () => {
    const payload: SequenceCreate = { name: 'Delta', description: 'some text' }

    expect(payload.description).toBe('some text')
  })

  it('SequenceUpdate allows all fields to be omitted', () => {
    const payload: SequenceUpdate = {}

    expect(Object.keys(payload)).toHaveLength(0)
  })

  it('SequenceUpdate accepts partial fields', () => {
    const byName: SequenceUpdate = { name: 'New Name' }
    const byDesc: SequenceUpdate = { description: 'New desc' }

    expect(byName.name).toBe('New Name')
    expect(byDesc.description).toBe('New desc')
  })
})
