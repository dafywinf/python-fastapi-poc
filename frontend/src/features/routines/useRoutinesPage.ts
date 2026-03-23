import { computed, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useAuth } from '../../composables/useAuth'
import type { Routine, RoutineCreate, RoutineUpdate } from '../../types/routine'
import {
  useActiveExecutionsQuery,
  useExecutionHistoryQuery,
  useRoutinesQuery,
} from './queries/useRoutineQueries'
import {
  useCreateRoutineMutation,
  useDeleteRoutineMutation,
  useRunRoutineMutation,
  useUpdateRoutineMutation,
} from './mutations/useRoutineMutations'

export function useRoutinesPage() {
  const toast = useToast()
  const { isAuthenticated } = useAuth()

  const routinesQuery = useRoutinesQuery()
  const activeQuery = useActiveExecutionsQuery()
  const historyLimit = ref(10)
  const historyQuery = useExecutionHistoryQuery(historyLimit)

  const createMutation = useCreateRoutineMutation()
  const updateMutation = useUpdateRoutineMutation()
  const deleteMutation = useDeleteRoutineMutation()
  const runMutation = useRunRoutineMutation()

  const routines = computed(() => routinesQuery.data.value ?? [])
  const loadingRoutines = computed(() => routinesQuery.isPending.value)
  const routinesError = computed(() =>
    routinesQuery.error.value instanceof Error
      ? routinesQuery.error.value.message
      : null,
  )

  const activeExecutions = computed(() => activeQuery.data.value ?? [])
  const loadingActive = computed(() => activeQuery.isPending.value)
  const activeError = computed<string | null>(() => {
    const err = activeQuery.error.value
    if (!err) return null
    return err instanceof Error ? err.message : 'Failed to load active executions'
  })

  const historyExecutions = computed(() => historyQuery.data.value ?? [])
  const loadingHistory = computed(() => historyQuery.isPending.value)
  const historyError = computed<string | null>(() => {
    const err = historyQuery.error.value
    if (!err) return null
    return err instanceof Error ? err.message : 'Failed to load execution history'
  })

  const formDialogOpen = ref(false)
  const editingRoutine = ref<Routine | null>(null)
  const form = ref<RoutineCreate>({
    name: '',
    description: null,
    schedule_type: 'manual',
    schedule_config: null,
    is_active: true,
  })
  const formError = ref<string | null>(null)
  const formValidationErrors = ref<{
    name?: string
    cronExpression?: string
    intervalSeconds?: string
  }>({})

  const cronExpression = ref('')
  const intervalSeconds = ref<number>(60)
  const intervalSecondsStr = computed({
    get: () => String(intervalSeconds.value),
    set: (v: string) => {
      intervalSeconds.value = parseInt(v, 10) || 60
    },
  })

  const scheduleConfig = computed<RoutineCreate['schedule_config']>(() => {
    if (form.value.schedule_type === 'cron') {
      return cronExpression.value ? { cron: cronExpression.value } : null
    }
    if (form.value.schedule_type === 'interval') {
      return intervalSeconds.value > 0
        ? { seconds: intervalSeconds.value }
        : null
    }
    return null
  })

  const submitting = computed(
    () => createMutation.isPending.value || updateMutation.isPending.value,
  )

  function openCreate(): void {
    editingRoutine.value = null
    form.value = {
      name: '',
      description: null,
      schedule_type: 'manual',
      schedule_config: null,
      is_active: true,
    }
    cronExpression.value = ''
    intervalSeconds.value = 60
    formError.value = null
    formValidationErrors.value = {}
    formDialogOpen.value = true
  }

  function openEdit(routine: Routine): void {
    editingRoutine.value = routine
    form.value = {
      name: routine.name,
      description: routine.description,
      schedule_type: routine.schedule_type,
      schedule_config: routine.schedule_config,
      is_active: routine.is_active,
    }
    if (
      routine.schedule_type === 'cron' &&
      routine.schedule_config &&
      'cron' in routine.schedule_config
    ) {
      cronExpression.value = routine.schedule_config.cron
    } else {
      cronExpression.value = ''
    }
    if (
      routine.schedule_type === 'interval' &&
      routine.schedule_config &&
      'seconds' in routine.schedule_config
    ) {
      intervalSeconds.value = routine.schedule_config.seconds
    } else {
      intervalSeconds.value = 60
    }
    formError.value = null
    formValidationErrors.value = {}
    formDialogOpen.value = true
  }

  function validateRoutineForm(): boolean {
    const errors: typeof formValidationErrors.value = {}

    if (!form.value.name.trim()) {
      errors.name = 'Name is required'
    }

    if (
      form.value.schedule_type === 'cron' &&
      !cronExpression.value.trim()
    ) {
      errors.cronExpression = 'Cron expression is required'
    }

    if (
      form.value.schedule_type === 'interval' &&
      intervalSeconds.value <= 0
    ) {
      errors.intervalSeconds = 'Interval must be greater than 0'
    }

    formValidationErrors.value = errors
    return Object.keys(errors).length === 0
  }

  async function submitForm(): Promise<void> {
    formError.value = null
    if (!validateRoutineForm()) {
      return
    }
    const payload: RoutineCreate = {
      ...form.value,
      name: form.value.name.trim(),
      schedule_config: scheduleConfig.value,
    }

    try {
      if (editingRoutine.value) {
        await updateMutation.mutateAsync({
          id: editingRoutine.value.id,
          payload: payload as RoutineUpdate,
        })
      } else {
        await createMutation.mutateAsync(payload)
      }
      formDialogOpen.value = false
    } catch (e) {
      formError.value = e instanceof Error ? e.message : 'Save failed'
    }
  }

  const deleteDialogOpen = ref(false)
  const deletingRoutine = ref<Routine | null>(null)
  const deleteError = ref<string | null>(null)
  const deleting = computed(() => deleteMutation.isPending.value)

  function openDelete(routine: Routine): void {
    deletingRoutine.value = routine
    deleteError.value = null
    deleteDialogOpen.value = true
  }

  async function confirmDelete(): Promise<void> {
    if (!deletingRoutine.value) return
    deleteError.value = null
    try {
      await deleteMutation.mutateAsync(deletingRoutine.value.id)
      deleteDialogOpen.value = false
    } catch (e) {
      deleteError.value = e instanceof Error ? e.message : 'Delete failed'
    }
  }

  const runNowLoading = ref<Record<number, boolean>>({})

  async function runNow(routine: Routine): Promise<void> {
    runNowLoading.value[routine.id] = true
    try {
      await runMutation.mutateAsync(routine.id)
      toast.add({
        severity: 'success',
        summary: 'Started',
        detail: `${routine.name} is running`,
        life: 3000,
      })
      await activeQuery.refetch()
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to start'
      toast.add({
        severity: msg.includes('already running') ? 'warn' : 'error',
        summary: 'Run Now',
        detail: msg,
        life: 4000,
      })
    } finally {
      delete runNowLoading.value[routine.id]
    }
  }

  function elapsedSeconds(startedAt: string): number {
    return Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000)
  }

  function durationSeconds(
    startedAt: string,
    completedAt: string | null,
  ): number | null {
    if (!completedAt) return null
    return Math.floor(
      (new Date(completedAt).getTime() - new Date(startedAt).getTime()) / 1000,
    )
  }

  return {
    isAuthenticated,
    routines,
    loadingRoutines,
    routinesError,
    activeExecutions,
    loadingActive,
    activeError,
    historyLimit,
    historyExecutions,
    loadingHistory,
    historyError,
    elapsedSeconds,
    durationSeconds,
    formDialogOpen,
    editingRoutine,
    form,
    formError,
    formValidationErrors,
    submitting,
    cronExpression,
    intervalSecondsStr,
    openCreate,
    openEdit,
    submitForm,
    deleteDialogOpen,
    deletingRoutine,
    deleteError,
    deleting,
    openDelete,
    confirmDelete,
    runNowLoading,
    runNow,
  }
}
