import { computed, ref, watch } from 'vue'
import {
  useExecutionHistoryQuery,
  useRoutinesQuery,
} from './queries/useRoutineQueries'

export function useExecutionHistoryPage() {
  const selectedRoutineId = ref<number | null>(null)
  const limit = ref(25)
  const page = ref(1)
  const offset = computed(() => (page.value - 1) * limit.value)

  const searchQuery = ref('')
  const debouncedSearch = ref('')

  let debounceTimer: ReturnType<typeof setTimeout> | null = null
  watch(searchQuery, (val) => {
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => {
      debouncedSearch.value = val
    }, 300)
  })

  // Reset to page 1 whenever filters or page size change
  watch([searchQuery, limit, selectedRoutineId], () => {
    page.value = 1
  })

  const routinesQuery = useRoutinesQuery()
  const historyQuery = useExecutionHistoryQuery(
    limit,
    offset,
    selectedRoutineId,
    debouncedSearch,
    undefined,
    6000,
  )

  const routines = computed(() => routinesQuery.data.value?.items ?? [])
  const routinesError = computed<string | null>(() => {
    const err = routinesQuery.error.value
    if (!err) return null
    return err instanceof Error ? err.message : 'Failed to load routines'
  })
  const executions = computed(() => historyQuery.data.value?.items ?? [])
  const executionsTotal = computed(() => historyQuery.data.value?.total ?? 0)
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
    executionsTotal,
    loading,
    error,
    searchQuery,
    selectedRoutineId,
    limit,
    page,
    durationLabel,
  }
}
