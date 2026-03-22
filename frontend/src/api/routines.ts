import type {
  Action,
  ActionCreate,
  ActionUpdate,
  Routine,
  RoutineCreate,
  RoutineExecution,
  RoutineUpdate,
} from '../types/routine'

const ROUTINES_BASE = '/routines'
const ACTIONS_BASE = '/actions'
const EXECUTIONS_BASE = '/executions'

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('access_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...authHeaders(), ...options?.headers },
  })
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(detail.detail ?? response.statusText)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const routinesApi = {
  list(): Promise<Routine[]> {
    return request<Routine[]>(ROUTINES_BASE + '/')
  },

  get(id: number): Promise<Routine> {
    return request<Routine>(`${ROUTINES_BASE}/${id}`)
  },

  create(payload: RoutineCreate): Promise<Routine> {
    return request<Routine>(ROUTINES_BASE + '/', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  update(id: number, payload: RoutineUpdate): Promise<Routine> {
    return request<Routine>(`${ROUTINES_BASE}/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  },

  delete(id: number): Promise<void> {
    return request<void>(`${ROUTINES_BASE}/${id}`, { method: 'DELETE' })
  },

  listActions(routineId: number): Promise<Action[]> {
    return request<Action[]>(`${ROUTINES_BASE}/${routineId}/actions`)
  },

  createAction(routineId: number, payload: ActionCreate): Promise<Action> {
    return request<Action>(`${ROUTINES_BASE}/${routineId}/actions`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  updateAction(id: number, payload: ActionUpdate): Promise<Action> {
    return request<Action>(`${ACTIONS_BASE}/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  },

  deleteAction(id: number): Promise<void> {
    return request<void>(`${ACTIONS_BASE}/${id}`, { method: 'DELETE' })
  },

  runNow(id: number): Promise<{ execution_id: number }> {
    return request<{ execution_id: number }>(`${ROUTINES_BASE}/${id}/run`, { method: 'POST' })
  },

  activeExecutions(): Promise<RoutineExecution[]> {
    return request<RoutineExecution[]>(`${EXECUTIONS_BASE}/active`)
  },

  executionHistory(limit?: number, routineId?: number): Promise<RoutineExecution[]> {
    const url = `${EXECUTIONS_BASE}/history?limit=${limit ?? 10}${routineId ? `&routine_id=${routineId}` : ''}`
    return request<RoutineExecution[]>(url)
  },
}
