export const routineKeys = {
  all: ['routines'] as const,
  lists: () => [...routineKeys.all, 'list'] as const,
  list: () => [...routineKeys.lists()] as const,
  details: () => [...routineKeys.all, 'detail'] as const,
  detail: (routineId: number) => [...routineKeys.details(), routineId] as const,
  executions: ['executions'] as const,
  activeExecutions: () => [...routineKeys.executions, 'active'] as const,
  history: (limit: number, routineId?: number | null) =>
    [...routineKeys.executions, 'history', limit, routineId ?? 'all'] as const,
}
