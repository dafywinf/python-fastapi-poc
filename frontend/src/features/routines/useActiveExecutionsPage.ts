import { computed, watch } from 'vue'
import { useQueryClient } from '@tanstack/vue-query'
import { useActiveExecutionsQuery } from './queries/useRoutineQueries'
import { routineKeys } from './queries/keys'

export function useActiveExecutionsPage() {
  const query = useActiveExecutionsQuery()
  const queryClient = useQueryClient()

  const executions = computed(() => query.data.value ?? [])

  // When any execution disappears from the active list it has completed —
  // immediately invalidate history so the dashboard updates without waiting for
  // the next poll. Tracking all active IDs (not just running) catches fast
  // executions that complete before being observed as running.
  const activeIds = computed(() => new Set(executions.value.map((e) => e.id)))
  watch(activeIds, (current, previous) => {
    if (previous === undefined) return
    const anyGone = [...previous].some((id) => !current.has(id))
    if (anyGone) {
      queryClient.invalidateQueries({
        queryKey: [...routineKeys.executions, 'history'],
      })
    }
  })
  const loading = computed(() => query.isPending.value)
  const error = computed<string | null>(() => {
    const err = query.error.value
    if (!err) return null
    return err instanceof Error ? err.message : 'Failed to load active executions'
  })

  function elapsedSeconds(startedAt: string | null): number {
    if (!startedAt) return 0
    return Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000)
  }

  function queuedSeconds(queuedAt: string): number {
    return Math.floor((Date.now() - new Date(queuedAt).getTime()) / 1000)
  }

  function actionElapsedSeconds(startedAt: string | null): number | null {
    if (!startedAt) return null
    return Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000)
  }

  return { executions, loading, error, elapsedSeconds, queuedSeconds, actionElapsedSeconds }
}
