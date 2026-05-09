import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as allure from 'allure-js-commons'
import type { components, paths } from '../api/generated/schema'
import { routinesApi } from '../api/routines'
import { applyFrontendAllureLabels } from '../test/allure'
import { routinesHandlers } from '../test/msw/handlers'
import { server } from '../test/msw/server'

type ListRoutinesResponse =
  paths['/routines/']['get']['responses']['200']['content']['application/json']
type RoutineResponse = components['schemas']['RoutineResponse']
type ExecutionHistoryResponse =
  paths['/executions/history']['get']['responses']['200']['content']['application/json']

const routine: RoutineResponse = {
  id: 1,
  name: 'Test routine',
  description: null,
  schedule_type: 'manual',
  schedule_config: null,
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  actions: [],
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('routinesApi', () => {
  beforeEach(() => {
    applyFrontendAllureLabels('Vitest', 'base')
    allure.feature('routinesApi')
  })

  it('list calls GET /routines/', async () => {
    const fetchSpy = vi.spyOn(global, 'fetch')
    server.use(routinesHandlers.list([] satisfies ListRoutinesResponse))
    await routinesApi.list()
    expect(fetchSpy).toHaveBeenCalledWith(
      '/routines/',
      expect.objectContaining({ method: 'GET' }),
    )
    const [, options] = fetchSpy.mock.calls[0] ?? []
    expect(options).toBeDefined()
    expect((options as RequestInit).headers).toBeInstanceOf(Headers)
  })

  it('create calls POST /routines/', async () => {
    const fetchSpy = vi.spyOn(global, 'fetch')
    server.use(routinesHandlers.create(routine))

    const result = await routinesApi.create({
      name: 'Test',
      schedule_type: 'manual',
      schedule_config: null,
    })

    expect(result.id).toBe(1)
    expect(fetchSpy).toHaveBeenCalledWith(
      '/routines/',
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('delete calls DELETE and returns undefined', async () => {
    const fetchSpy = vi.spyOn(global, 'fetch')
    server.use(routinesHandlers.delete())
    const result = await routinesApi.delete(1)
    expect(result).toBeUndefined()
    expect(fetchSpy).toHaveBeenCalledWith(
      '/routines/1',
      expect.objectContaining({ method: 'DELETE' }),
    )
  })

  it('runNow calls POST /routines/{id}/run', async () => {
    const fetchSpy = vi.spyOn(global, 'fetch')
    server.use(routinesHandlers.runNow({ execution_id: 42 }))
    const result = await routinesApi.runNow(5)
    expect(result.execution_id).toBe(42)
    expect(fetchSpy).toHaveBeenCalledWith(
      '/routines/5/run',
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('executionHistory builds correct URL with params', async () => {
    const fetchSpy = vi.spyOn(global, 'fetch')
    const history: ExecutionHistoryResponse = []
    server.use(routinesHandlers.executionHistory(history))
    await routinesApi.executionHistory({ limit: 20, routineId: 3 })

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining('limit=20'),
      expect.anything(),
    )
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining('routine_id=3'),
      expect.anything(),
    )
  })
})
