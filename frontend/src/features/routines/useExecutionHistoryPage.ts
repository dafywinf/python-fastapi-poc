import { computed, ref } from 'vue'
import {
  useExecutionHistoryQuery,
  useRoutinesQuery,
} from './queries/useRoutineQueries'

export function useExecutionHistoryPage() {
  const selectedRoutineId = ref<number | null>(null)
  const limit = ref(20)

  const routinesQuery = useRoutinesQuery()
  const historyQuery = useExecutionHistoryQuery(limit, selectedRoutineId, 6000)

  const routines = computed(() => routinesQuery.data.value ?? [])
  const routinesError = computed<string | null>(() => {
    const err = routinesQuery.error.value
    if (!err) return null
    return err instanceof Error ? err.message : 'Failed to load routines'
  })
  const executions = computed(() => historyQuery.data.value ?? [])
  const loading = computed(() => historyQuery.isPending.value)
  const error = computed(() =>
    historyQuery.error.value instanceof Error
      ? historyQuery.error.value.message
      : null,
  )

  function durationLabel(
    startedAt: string,
    completedAt: string | null,
  ): string {
    if (!completedAt) return '—'
    const ms = new Date(completedAt).getTime() - new Date(startedAt).getTime()
    return `${Math.floor(ms / 1000)}s`
  }

  return {
    routines,
    routinesError,
    executions,
    loading,
    error,
    selectedRoutineId,
    limit,
    durationLabel,
  }
}
