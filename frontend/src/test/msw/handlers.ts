import { http, HttpResponse } from 'msw'
import type { components, paths } from '../../api/generated/schema'
import type { Page } from '../../types/routine'

type ListUsersResponse =
  paths['/users/']['get']['responses']['200']['content']['application/json']
type RoutineResponse = components['schemas']['RoutineResponse']
type RunResponse = components['schemas']['RunResponse']
type ExecutionResponse = components['schemas']['ExecutionResponse']
type ActiveExecutionsResponse =
  paths['/executions/active']['get']['responses']['200']['content']['application/json']
type TokenResponse = components['schemas']['TokenResponse']

export const usersHandlers = {
  list(users: ListUsersResponse = []) {
    return http.get('/users/', () => HttpResponse.json(users))
  },

  error(status = 500, detail = 'Failed to load users') {
    return http.get('/users/', () => HttpResponse.json({ detail }, { status }))
  },

  pending() {
    return http.get('/users/', () => new Promise(() => {}))
  },
}

export const routinesHandlers = {
  list(routines: RoutineResponse[] = []) {
    const page: Page<RoutineResponse> = {
      items: routines,
      total: routines.length,
      limit: 25,
      offset: 0,
    }
    return http.get('/routines/', () => HttpResponse.json(page))
  },

  listError(status = 500, detail = 'Failed to load routines') {
    return http.get('/routines/', () => HttpResponse.json({ detail }, { status }))
  },

  listPending() {
    return http.get('/routines/', () => new Promise(() => {}))
  },

  create(routine: RoutineResponse) {
    return http.post('/routines/', async ({ request }) => {
      await request.json()
      return HttpResponse.json(routine, { status: 201 })
    })
  },

  get(routine: RoutineResponse) {
    return http.get('/routines/:routineId', () => HttpResponse.json(routine))
  },

  getError(status = 404, detail = 'Not found') {
    return http.get('/routines/:routineId', () => HttpResponse.json({ detail }, { status }))
  },

  delete() {
    return http.delete('/routines/:routineId', () => new HttpResponse(null, { status: 204 }))
  },

  update(routine: RoutineResponse) {
    return http.patch('/routines/:routineId', async ({ request }) => {
      await request.json()
      return HttpResponse.json(routine)
    })
  },

  runNow(response: RunResponse) {
    return http.post('/routines/:routineId/run', () =>
      HttpResponse.json(response, { status: 202 }),
    )
  },

  activeExecutions(executions: ActiveExecutionsResponse = []) {
    return http.get('/executions/active', () => HttpResponse.json(executions))
  },

  activeExecutionsPending() {
    return http.get('/executions/active', () => new Promise(() => {}))
  },

  executionHistory(executions: ExecutionResponse[] = []) {
    const page: Page<ExecutionResponse> = {
      items: executions,
      total: executions.length,
      limit: 25,
      offset: 0,
    }
    return http.get('/executions/history', () => HttpResponse.json(page))
  },

  executionHistoryPending() {
    return http.get('/executions/history', () => new Promise(() => {}))
  },
}

export const authHandlers = {
  login(response: TokenResponse) {
    return http.post('/auth/token', async ({ request }) => {
      await request.formData()
      return HttpResponse.json(response)
    })
  },
}

export const handlers = [
  usersHandlers.list(),
  routinesHandlers.list(),
  routinesHandlers.activeExecutions(),
  routinesHandlers.executionHistory(),
]
