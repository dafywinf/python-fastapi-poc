import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { HttpError } from '../../api/client'
import { useAuth } from '../../composables/useAuth'
import type { StagedAction } from '../../types/routine'
import {
  useDeleteRoutineMutation,
  useRunRoutineMutation,
} from './mutations/useRoutineMutations'
import { useRoutineQuery } from './queries/useRoutineQueries'

export function useRoutineViewPage(routineId: number) {
  const router = useRouter()
  const toast = useToast()
  const { isAuthenticated } = useAuth()

  const routineQuery = useRoutineQuery(routineId)
  const runMutation = useRunRoutineMutation()
  const deleteRoutineMutation = useDeleteRoutineMutation()

  const routine = computed(() => routineQuery.data.value ?? null)
  const loading = computed(() => routineQuery.isPending.value)
  const pageError = computed(() => {
    const error = routineQuery.error.value
    if (!error) return null
    if (error instanceof HttpError && error.status === 404) return 'Routine not found'
    return error instanceof Error ? error.message : 'Failed to load routine'
  })

  const runNowLoading = computed(() => runMutation.isPending.value)

  const deleteDialogOpen = ref(false)
  const deleteError = ref<string | null>(null)
  const deleting = computed(() => deleteRoutineMutation.isPending.value)

  // Convert sorted actions to StagedAction for RoutineActionsList (read-only)
  const viewActions = computed<StagedAction[]>(() => {
    if (!routine.value) return []
    return [...routine.value.actions]
      .sort((a, b) => a.position - b.position)
      .map((a) => ({ ...a, _key: `e-${a.id}` }))
  })

  const scheduleConfigSummary = computed<string | null>(() => {
    if (!routine.value?.schedule_config) return null
    const cfg = routine.value.schedule_config
    if ('cron' in cfg) return `(${cfg.cron})`
    if ('seconds' in cfg) return `(every ${cfg.seconds}s)`
    return null
  })

  const metadataItems = computed(() => {
    if (!routine.value) return []
    return [
      {
        label: 'Name',
        kind: 'text' as const,
        value: routine.value.name,
        className: 'text-slate-900',
      },
      {
        label: 'Description',
        kind: 'text' as const,
        value: routine.value.description ?? '—',
        className: 'text-slate-500',
      },
      {
        label: 'Schedule',
        kind: 'schedule' as const,
        scheduleType: routine.value.schedule_type,
        summary: scheduleConfigSummary.value,
      },
      {
        label: 'Active',
        kind: 'text' as const,
        value: routine.value.is_active ? '✓ Active' : 'Inactive',
        className: routine.value.is_active
          ? 'text-green-600 font-semibold'
          : 'text-slate-400',
      },
    ]
  })

  function actionConfigSummary(action: StagedAction): string {
    const cfg = action.config
    if ('message' in cfg) return `echo: ${cfg.message}`
    if ('seconds' in cfg) return `sleep ${cfg.seconds}s`
    return ''
  }

  function openDeleteDialog(): void {
    deleteError.value = null
    deleteDialogOpen.value = true
  }

  async function confirmDelete(): Promise<void> {
    deleteError.value = null
    try {
      await deleteRoutineMutation.mutateAsync(routineId)
      deleteDialogOpen.value = false
      await router.push({ name: 'routines' })
    } catch (e) {
      deleteError.value = e instanceof Error ? e.message : 'Delete failed'
    }
  }

  async function runNow(): Promise<void> {
    if (!routine.value) return
    try {
      await runMutation.mutateAsync(routine.value.id)
      toast.add({
        severity: 'success',
        summary: 'Queued',
        detail: `${routine.value.name} added to the execution queue`,
        life: 3000,
      })
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to queue run'
      toast.add({
        severity: 'error',
        summary: 'Run Now failed',
        detail: msg,
        life: 4000,
      })
    }
  }

  function goToEdit(): void {
    void router.push({ name: 'routine-edit', params: { id: routineId } })
  }

  return {
    isAuthenticated,
    routine,
    loading,
    pageError,
    runNowLoading,
    deleteDialogOpen,
    deleteError,
    deleting,
    viewActions,
    metadataItems,
    actionConfigSummary,
    openDeleteDialog,
    confirmDelete,
    runNow,
    goToEdit,
  }
}
