import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { routinesApi } from '../../../api/routines'
import { routineKeys } from './keys'

export function useRoutinesQuery(
  search?: MaybeRefOrGetter<string | undefined>,
  limit?: MaybeRefOrGetter<number | undefined>,
  offset?: MaybeRefOrGetter<number | undefined>,
) {
  return useQuery({
    queryKey: computed(() =>
      routineKeys.list(toValue(search), toValue(limit), toValue(offset)),
    ),
    queryFn: () =>
      routinesApi.list({
        search: toValue(search) || undefined,
        limit: toValue(limit),
        offset: toValue(offset),
      }),
  })
}

export function useRoutineQuery(
  routineId: MaybeRefOrGetter<number>,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: computed(() => routineKeys.detail(toValue(routineId))),
    queryFn: () => routinesApi.get(toValue(routineId)),
    enabled: options?.enabled ?? true,
  })
}

export function useActiveExecutionsQuery(intervalMs = 2000) {
  return useQuery({
    queryKey: routineKeys.activeExecutions(),
    queryFn: routinesApi.activeExecutions,
    refetchInterval: intervalMs,
  })
}

export function useExecutionHistoryQuery(
  limit: MaybeRefOrGetter<number>,
  offset: MaybeRefOrGetter<number>,
  routineId?: MaybeRefOrGetter<number | null | undefined>,
  search?: MaybeRefOrGetter<string | undefined>,
  sinceMinutes?: MaybeRefOrGetter<number | null | undefined>,
  intervalMs = 5000,
) {
  return useQuery({
    queryKey: computed(() =>
      routineKeys.history(
        toValue(limit),
        toValue(offset),
        toValue(routineId),
        toValue(search),
        toValue(sinceMinutes),
      ),
    ),
    queryFn: () =>
      routinesApi.executionHistory({
        limit: toValue(limit),
        offset: toValue(offset),
        routineId: toValue(routineId) ?? undefined,
        search: toValue(search) || undefined,
        sinceMinutes: toValue(sinceMinutes) ?? undefined,
      }),
    refetchInterval: intervalMs,
  })
}
