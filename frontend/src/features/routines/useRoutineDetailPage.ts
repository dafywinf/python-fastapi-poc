import { computed, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import { HttpError } from '../../api/client'
import { useAuth } from '../../composables/useAuth'
import type { Action, ActionCreate, RoutineUpdate } from '../../types/routine'
import {
  useCreateActionMutation,
  useDeleteActionMutation,
  useReorderActionMutation,
  useRunRoutineMutation,
  useUpdateRoutineMutation,
} from './mutations/useRoutineMutations'
import { useRoutineQuery } from './queries/useRoutineQueries'

export function useRoutineDetailPage(routineId: number) {
  const toast = useToast()
  const { isAuthenticated } = useAuth()

  const routineQuery = useRoutineQuery(routineId)
  const updateMutation = useUpdateRoutineMutation(routineId)
  const createActionMutation = useCreateActionMutation(routineId)
  const reorderActionMutation = useReorderActionMutation(routineId)
  const deleteActionMutation = useDeleteActionMutation(routineId)
  const runMutation = useRunRoutineMutation()

  const routine = computed(() => routineQuery.data.value ?? null)
  const loading = computed(() => routineQuery.isPending.value)
  const pageError = computed(() => {
    const error = routineQuery.error.value
    if (!error) {
      return null
    }
    if (error instanceof HttpError && error.status === 404) {
      return 'Routine not found'
    }
    return error instanceof Error
      ? error.message
      : 'Failed to load routine'
  })

  const editing = ref(false)
  const form = ref<
    RoutineUpdate & {
      description?: string | null
      schedule_type?: 'cron' | 'interval' | 'manual'
    }
  >({})
  const saveError = ref<string | null>(null)
  const saveValidationErrors = ref<{
    name?: string
    cronExpression?: string
    intervalSeconds?: string
  }>({})
  const saving = computed(() => updateMutation.isPending.value)

  const editCronExpression = ref('')
  const editIntervalSeconds = ref<number>(60)
  const editIntervalSecondsStr = computed({
    get: () => String(editIntervalSeconds.value),
    set: (v: string) => {
      editIntervalSeconds.value = parseInt(v, 10) || 60
    },
  })

  const actionForm = ref<ActionCreate>({
    action_type: 'echo',
    config: { message: '' },
  })
  const echoMessage = ref('')
  const sleepSeconds = ref<number>(5)
  const sleepSecondsStr = computed({
    get: () => String(sleepSeconds.value),
    set: (v: string) => {
      sleepSeconds.value = parseInt(v, 10) || 5
    },
  })
  const addingAction = computed(() => createActionMutation.isPending.value)
  const actionError = ref<string | null>(null)
  const actionConfigError = ref<string | null>(null)
  const runNowLoading = computed(() => runMutation.isPending.value)

  const sortedActions = computed<Action[]>(() => {
    if (!routine.value) return []
    return [...routine.value.actions].sort((a, b) => a.position - b.position)
  })

  const scheduleConfigSummary = computed<string | null>(() => {
    if (!routine.value?.schedule_config) return null
    const cfg = routine.value.schedule_config
    if ('cron' in cfg) return `(${cfg.cron})`
    if ('seconds' in cfg) return `(every ${cfg.seconds}s)`
    return null
  })

  function actionConfigSummary(action: Action): string {
    const cfg = action.config
    if ('message' in cfg) return `echo: ${cfg.message}`
    if ('seconds' in cfg) return `sleep ${cfg.seconds}s`
    return ''
  }

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

  function onActionTypeChange(): void {
    actionConfigError.value = null
    if (actionForm.value.action_type === 'echo') {
      actionForm.value.config = { message: '' }
      echoMessage.value = ''
    } else {
      actionForm.value.config = { seconds: 5 }
      sleepSeconds.value = 5
    }
  }

  function startEdit(): void {
    if (!routine.value) return
    form.value = {
      name: routine.value.name,
      description: routine.value.description,
      schedule_type: routine.value.schedule_type,
      schedule_config: routine.value.schedule_config,
      is_active: routine.value.is_active,
    }
    if (
      routine.value.schedule_type === 'cron' &&
      routine.value.schedule_config &&
      'cron' in routine.value.schedule_config
    ) {
      editCronExpression.value = routine.value.schedule_config.cron
    } else {
      editCronExpression.value = ''
    }
    if (
      routine.value.schedule_type === 'interval' &&
      routine.value.schedule_config &&
      'seconds' in routine.value.schedule_config
    ) {
      editIntervalSeconds.value = routine.value.schedule_config.seconds
    } else {
      editIntervalSeconds.value = 60
    }
    saveError.value = null
    saveValidationErrors.value = {}
    editing.value = true
  }

  function validateEditForm(): boolean {
    const errors: typeof saveValidationErrors.value = {}

    if (!form.value.name?.trim()) {
      errors.name = 'Name is required'
    }

    if (
      form.value.schedule_type === 'cron' &&
      !editCronExpression.value.trim()
    ) {
      errors.cronExpression = 'Cron expression is required'
    }

    if (
      form.value.schedule_type === 'interval' &&
      editIntervalSeconds.value <= 0
    ) {
      errors.intervalSeconds = 'Interval must be greater than 0'
    }

    saveValidationErrors.value = errors
    return Object.keys(errors).length === 0
  }

  async function saveEdit(): Promise<void> {
    if (!routine.value) return
    saveError.value = null
    if (!validateEditForm()) {
      return
    }
    let scheduleConfig: RoutineUpdate['schedule_config'] = null
    if (form.value.schedule_type === 'cron') {
      scheduleConfig = editCronExpression.value
        ? { cron: editCronExpression.value }
        : null
    } else if (form.value.schedule_type === 'interval') {
      scheduleConfig =
        editIntervalSeconds.value > 0
          ? { seconds: editIntervalSeconds.value }
          : null
    }
    try {
      await updateMutation.mutateAsync({
        id: routine.value.id,
        payload: {
          ...form.value,
          name: form.value.name?.trim(),
          schedule_config: scheduleConfig,
        },
      })
      editing.value = false
    } catch (e) {
      saveError.value = e instanceof Error ? e.message : 'Save failed'
    }
  }

  async function moveAction(
    action: Action,
    direction: 'up' | 'down',
  ): Promise<void> {
    actionError.value = null
    const newPos =
      direction === 'up' ? action.position - 1 : action.position + 1
    try {
      await reorderActionMutation.mutateAsync({
        actionId: action.id,
        position: newPos,
      })
    } catch (e) {
      actionError.value = e instanceof Error ? e.message : 'Reorder failed'
    }
  }

  async function removeAction(action: Action): Promise<void> {
    actionError.value = null
    try {
      await deleteActionMutation.mutateAsync(action.id)
    } catch (e) {
      actionError.value = e instanceof Error ? e.message : 'Delete failed'
    }
  }

  async function addAction(): Promise<void> {
    actionError.value = null
    actionConfigError.value = null
    if (
      actionForm.value.action_type === 'echo' &&
      !echoMessage.value.trim()
    ) {
      actionConfigError.value = 'Message is required'
      return
    }
    if (
      actionForm.value.action_type === 'sleep' &&
      sleepSeconds.value <= 0
    ) {
      actionConfigError.value = 'Seconds must be greater than 0'
      return
    }
    const config: ActionCreate['config'] =
      actionForm.value.action_type === 'echo'
        ? { message: echoMessage.value.trim() }
        : { seconds: sleepSeconds.value }

    try {
      await createActionMutation.mutateAsync({
        action_type: actionForm.value.action_type,
        config,
      })
      actionForm.value = { action_type: 'echo', config: { message: '' } }
      echoMessage.value = ''
      sleepSeconds.value = 5
    } catch (e) {
      actionError.value = e instanceof Error ? e.message : 'Add failed'
    }
  }

  async function runNow(): Promise<void> {
    if (!routine.value) return
    try {
      await runMutation.mutateAsync(routine.value.id)
      toast.add({
        severity: 'success',
        summary: 'Started',
        detail: `${routine.value.name} is running`,
        life: 3000,
      })
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to start'
      toast.add({
        severity: 'error',
        summary: 'Run Now failed',
        detail: msg,
        life: 4000,
      })
    }
  }

  return {
    isAuthenticated,
    routine,
    loading,
    pageError,
    editing,
    form,
    saveError,
    saveValidationErrors,
    saving,
    editCronExpression,
    editIntervalSecondsStr,
    actionForm,
    echoMessage,
    sleepSecondsStr,
    addingAction,
    actionError,
    actionConfigError,
    runNowLoading,
    sortedActions,
    metadataItems,
    scheduleConfigSummary,
    actionConfigSummary,
    onActionTypeChange,
    startEdit,
    saveEdit,
    moveAction,
    removeAction,
    addAction,
    runNow,
  }
}
