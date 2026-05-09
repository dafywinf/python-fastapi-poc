export const routineKeys = {
  all: ['routines'] as const,
  lists: () => [...routineKeys.all, 'list'] as const,
  list: (search?: string, limit?: number, offset?: number) =>
    [...routineKeys.lists(), search ?? '', limit ?? 25, offset ?? 0] as const,
  details: () => [...routineKeys.all, 'detail'] as const,
  detail: (routineId: number) => [...routineKeys.details(), routineId] as const,
  executions: ['executions'] as const,
  activeExecutions: () => [...routineKeys.executions, 'active'] as const,
  history: (
    limit: number,
    offset: number,
    routineId?: number | null,
    search?: string,
    sinceMinutes?: number | null,
  ) =>
    [
      ...routineKeys.executions,
      'history',
      limit,
      offset,
      routineId ?? 'all',
      search ?? '',
      sinceMinutes ?? 'all',
    ] as const,
}
