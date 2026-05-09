import type {
  Action,
  ActionCreate,
  ActionUpdate,
  ActiveRoutineExecution,
  Page,
  Routine,
  RoutineCreate,
  RoutineExecution,
  RoutineUpdate,
} from '../types/routine'
import { apiClient } from './client'

const ROUTINES_BASE = '/routines'
const ACTIONS_BASE = '/actions'
const EXECUTIONS_BASE = '/executions'

export const routinesApi = {
  list(params?: {
    search?: string
    limit?: number
    offset?: number
  }): Promise<Page<Routine>> {
    const p = new URLSearchParams()
    if (params?.search) p.set('search', params.search)
    if (params?.limit !== undefined) p.set('limit', String(params.limit))
    if (params?.offset !== undefined) p.set('offset', String(params.offset))
    const qs = p.toString()
    return apiClient.get<Page<Routine>>(`${ROUTINES_BASE}/${qs ? `?${qs}` : ''}`)
  },

  get(id: number): Promise<Routine> {
    return apiClient.get<Routine>(`${ROUTINES_BASE}/${id}`)
  },

  create(payload: RoutineCreate): Promise<Routine> {
    return apiClient.post<Routine>(ROUTINES_BASE + '/', payload)
  },

  update(id: number, payload: RoutineUpdate): Promise<Routine> {
    return apiClient.put<Routine>(`${ROUTINES_BASE}/${id}`, payload)
  },

  delete(id: number): Promise<void> {
    return apiClient.delete<void>(`${ROUTINES_BASE}/${id}`)
  },

  listActions(routineId: number): Promise<Action[]> {
    return apiClient.get<Action[]>(`${ROUTINES_BASE}/${routineId}/actions`)
  },

  createAction(routineId: number, payload: ActionCreate): Promise<Action> {
    return apiClient.post<Action>(
      `${ROUTINES_BASE}/${routineId}/actions`,
      payload,
    )
  },

  updateAction(id: number, payload: ActionUpdate): Promise<Action> {
    return apiClient.put<Action>(`${ACTIONS_BASE}/${id}`, payload)
  },

  reorderActions(routineId: number, actionIds: number[]): Promise<Action[]> {
    return apiClient.patch<Action[]>(
      `${ROUTINES_BASE}/${routineId}/actions/reorder`,
      { action_ids: actionIds },
    )
  },

  deleteAction(id: number): Promise<void> {
    return apiClient.delete<void>(`${ACTIONS_BASE}/${id}`)
  },

  runNow(id: number, scheduledFor?: Date): Promise<{ execution_id: number }> {
    const body = scheduledFor ? { scheduled_for: scheduledFor.toISOString() } : undefined
    return apiClient.post<{ execution_id: number }>(
      `${ROUTINES_BASE}/${id}/run`,
      body,
    )
  },

  getExecution(executionId: number): Promise<ActiveRoutineExecution> {
    return apiClient.get<ActiveRoutineExecution>(`${EXECUTIONS_BASE}/${executionId}`)
  },

  activeExecutions(): Promise<ActiveRoutineExecution[]> {
    return apiClient.get<ActiveRoutineExecution[]>(`${EXECUTIONS_BASE}/active`)
  },

  executionHistory(params?: {
    limit?: number
    offset?: number
    routineId?: number
    search?: string
    sinceMinutes?: number
  }): Promise<Page<RoutineExecution>> {
    const p = new URLSearchParams({ limit: String(params?.limit ?? 25) })
    if (params?.offset) p.set('offset', String(params.offset))
    if (params?.routineId !== undefined) p.set('routine_id', String(params.routineId))
    if (params?.search) p.set('search', params.search)
    if (params?.sinceMinutes !== undefined) p.set('since_minutes', String(params.sinceMinutes))
    return apiClient.get<Page<RoutineExecution>>(
      `${EXECUTIONS_BASE}/history?${p.toString()}`,
    )
  },
}
