import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { routinesApi } from '../../../api/routines'
import { routineKeys } from './keys'

export function useRoutinesQuery() {
  return useQuery({
    queryKey: routineKeys.list(),
    queryFn: routinesApi.list,
  })
}

export function useRoutineQuery(routineId: MaybeRefOrGetter<number>) {
  return useQuery({
    queryKey: computed(() => routineKeys.detail(toValue(routineId))),
    queryFn: () => routinesApi.get(toValue(routineId)),
  })
}

export function useActiveExecutionsQuery(intervalMs = 3000) {
  return useQuery({
    queryKey: routineKeys.activeExecutions(),
    queryFn: routinesApi.activeExecutions,
    refetchInterval: intervalMs,
  })
}

export function useExecutionHistoryQuery(
  limit: MaybeRefOrGetter<number>,
  routineId?: MaybeRefOrGetter<number | null | undefined>,
  intervalMs = 5000,
) {
  return useQuery({
    queryKey: computed(() =>
      routineKeys.history(toValue(limit), toValue(routineId)),
    ),
    queryFn: () =>
      routinesApi.executionHistory(
        toValue(limit),
        toValue(routineId) ?? undefined,
      ),
    refetchInterval: intervalMs,
  })
}
