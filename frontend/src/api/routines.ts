import type {
  Action,
  ActionCreate,
  ActionUpdate,
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
  list(): Promise<Routine[]> {
    return apiClient.get<Routine[]>(ROUTINES_BASE + '/')
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

  deleteAction(id: number): Promise<void> {
    return apiClient.delete<void>(`${ACTIONS_BASE}/${id}`)
  },

  runNow(id: number): Promise<{ execution_id: number }> {
    return apiClient.post<{ execution_id: number }>(
      `${ROUTINES_BASE}/${id}/run`,
    )
  },

  activeExecutions(): Promise<RoutineExecution[]> {
    return apiClient.get<RoutineExecution[]>(`${EXECUTIONS_BASE}/active`)
  },

  executionHistory(
    limit?: number,
    routineId?: number,
  ): Promise<RoutineExecution[]> {
    const params = new URLSearchParams({ limit: String(limit ?? 10) })
    if (routineId !== undefined) {
      params.set('routine_id', String(routineId))
    }
    return apiClient.get<RoutineExecution[]>(
      `${EXECUTIONS_BASE}/history?${params.toString()}`,
    )
  },
}
