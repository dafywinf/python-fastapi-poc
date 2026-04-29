import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { HttpError } from '../../api/client'
import { routinesApi } from '../../api/routines'
import { useAuth } from '../../composables/useAuth'
import type { ActionCreate, RoutineCreate, RoutineUpdate, StagedAction } from '../../types/routine'
import {
  useCreateRoutineMutation,
  useUpdateRoutineMutation,
  useDeleteRoutineMutation,
  useCreateActionMutation,
  useBulkReorderActionsMutation,
  useDeleteActionMutation,
} from './mutations/useRoutineMutations'
import { useRoutineQuery } from './queries/useRoutineQueries'

export function useRoutineFormPage(routineId?: number) {
  const router = useRouter()
  const toast = useToast()
  const { isAuthenticated } = useAuth()

  const isEditMode = routineId !== undefined

  // ── Data fetching (edit mode only) ───────────────────────────────────────
  const routineQuery = useRoutineQuery(routineId ?? 0, { enabled: isEditMode })
  const routine = computed(() => (isEditMode ? (routineQuery.data.value ?? null) : null))
  const loading = computed(() => isEditMode && routineQuery.isPending.value)
  const pageError = computed(() => {
    if (!isEditMode) return null
    const error = routineQuery.error.value
    if (!error) return null
    if (error instanceof HttpError && error.status === 404) return 'Routine not found'
    return error instanceof Error ? error.message : 'Failed to load routine'
  })

  // ── Mutations ────────────────────────────────────────────────────────────
  const createMutation = useCreateRoutineMutation()
  const updateMutation = useUpdateRoutineMutation(routineId ?? 0)
  const deleteRoutineMutation = useDeleteRoutineMutation()
  const createActionMutation = useCreateActionMutation(routineId ?? 0)
  const bulkReorderMutation = useBulkReorderActionsMutation(routineId ?? 0)
  const deleteActionMutation = useDeleteActionMutation(routineId ?? 0)

  // ── Form state ───────────────────────────────────────────────────────────
  const form = ref<RoutineCreate & RoutineUpdate>({
    name: '',
    description: null,
    schedule_type: 'manual',
    schedule_config: null,
    is_active: true,
  })
  const saveError = ref<string | null>(null)
  const saveValidationErrors = ref<{
    name?: string
    cronExpression?: string
    intervalSeconds?: string
  }>({})
  const saving = ref(false)

  const cronExpression = ref('')
  const intervalSeconds = ref<number>(60)
  const intervalSecondsStr = computed({
    get: () => String(intervalSeconds.value),
    set: (v: string) => {
      intervalSeconds.value = parseInt(v, 10) || 60
    },
  })

  // ── Staged actions ───────────────────────────────────────────────────────
  const localActions = ref<StagedAction[]>([])
  const removedActionIds = ref<number[]>([])
  const initialized = ref(false)
  let keyCounter = 0

  // Populate form from fetched data in edit mode
  watch(
    () => routineQuery.data.value,
    (data) => {
      if (!isEditMode || !data || initialized.value) return
      initialized.value = true

      form.value = {
        name: data.name,
        description: data.description,
        schedule_type: data.schedule_type,
        schedule_config: data.schedule_config,
        is_active: data.is_active,
      }

      if (data.schedule_type === 'cron' && data.schedule_config && 'cron' in data.schedule_config) {
        cronExpression.value = data.schedule_config.cron
      }
      if (
        data.schedule_type === 'interval' &&
        data.schedule_config &&
        'seconds' in data.schedule_config
      ) {
        intervalSeconds.value = data.schedule_config.seconds
      }

      localActions.value = [...data.actions]
        .sort((a, b) => a.position - b.position)
        .map((a) => ({
          id: a.id,
          action_type: a.action_type,
          config: a.config,
          position: a.position,
          _key: `e-${a.id}`,
        }))
    },
    { immediate: true },
  )

  // ── Add-action form ──────────────────────────────────────────────────────
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
  const actionError = ref<string | null>(null)
  const actionConfigError = ref<string | null>(null)

  // ── Delete dialog (edit mode only) ───────────────────────────────────────
  const deleteDialogOpen = ref(false)
  const deleteError = ref<string | null>(null)
  const deleting = computed(() => deleteRoutineMutation.isPending.value)

  function openDeleteDialog(): void {
    deleteError.value = null
    deleteDialogOpen.value = true
  }

  async function confirmDelete(): Promise<void> {
    if (!routineId) return
    deleteError.value = null
    try {
      await deleteRoutineMutation.mutateAsync(routineId)
      deleteDialogOpen.value = false
      await router.push({ name: 'routines' })
    } catch (e) {
      deleteError.value = e instanceof Error ? e.message : 'Delete failed'
    }
  }

  // ── Helpers ──────────────────────────────────────────────────────────────
  function actionConfigSummary(action: StagedAction): string {
    const cfg = action.config
    if ('message' in cfg) return `echo: ${cfg.message}`
    if ('seconds' in cfg) return `sleep ${cfg.seconds}s`
    return ''
  }

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

  function reorderActions(actions: StagedAction[]): void {
    localActions.value = actions.map((a, i) => ({ ...a, position: i + 1 }))
  }

  function removeAction(action: StagedAction): void {
    if (action.id !== null) {
      removedActionIds.value.push(action.id)
    }
    localActions.value = localActions.value.filter((a) => a._key !== action._key)
  }

  function addAction(): void {
    actionError.value = null
    actionConfigError.value = null

    if (actionForm.value.action_type === 'echo' && !echoMessage.value.trim()) {
      actionConfigError.value = 'Message is required'
      return
    }
    if (actionForm.value.action_type === 'sleep' && sleepSeconds.value <= 0) {
      actionConfigError.value = 'Seconds must be greater than 0'
      return
    }

    const config: ActionCreate['config'] =
      actionForm.value.action_type === 'echo'
        ? { message: echoMessage.value.trim() }
        : { seconds: sleepSeconds.value }

    localActions.value = [
      ...localActions.value,
      {
        id: null,
        action_type: actionForm.value.action_type,
        config,
        position: localActions.value.length + 1,
        _key: `n-${++keyCounter}`,
      },
    ]

    actionForm.value = { action_type: 'echo', config: { message: '' } }
    echoMessage.value = ''
    sleepSeconds.value = 5
  }

  // ── Validation ───────────────────────────────────────────────────────────
  function validateForm(): boolean {
    const errors: typeof saveValidationErrors.value = {}

    if (!form.value.name?.trim()) {
      errors.name = 'Name is required'
    }
    if (form.value.schedule_type === 'cron' && !cronExpression.value.trim()) {
      errors.cronExpression = 'Cron expression is required'
    }
    if (form.value.schedule_type === 'interval' && intervalSeconds.value <= 0) {
      errors.intervalSeconds = 'Interval must be greater than 0'
    }

    saveValidationErrors.value = errors
    return Object.keys(errors).length === 0
  }

  // ── Save ─────────────────────────────────────────────────────────────────
  async function save(): Promise<void> {
    saveError.value = null
    if (!validateForm()) return

    saving.value = true
    try {
      let scheduleConfig: RoutineCreate['schedule_config'] = null
      if (form.value.schedule_type === 'cron') {
        scheduleConfig = cronExpression.value ? { cron: cronExpression.value } : null
      } else if (form.value.schedule_type === 'interval') {
        scheduleConfig = intervalSeconds.value > 0 ? { seconds: intervalSeconds.value } : null
      }

      if (isEditMode) {
        // ── Edit path ──────────────────────────────────────────────────────
        await updateMutation.mutateAsync({
          id: routineId,
          payload: { ...form.value, name: form.value.name?.trim(), schedule_config: scheduleConfig },
        })

        await Promise.all(removedActionIds.value.map((id) => deleteActionMutation.mutateAsync(id)))

        const keyToNewId = new Map<string, number>()
        for (const action of localActions.value.filter((a) => a.id === null)) {
          const created = await createActionMutation.mutateAsync({
            action_type: action.action_type,
            config: action.config,
          })
          keyToNewId.set(action._key, created.id)
        }

        const finalIds = localActions.value
          .map((a) => (a.id !== null ? a.id : keyToNewId.get(a._key)))
          .filter((id): id is number => id !== undefined)

        if (finalIds.length > 0) {
          await bulkReorderMutation.mutateAsync(finalIds)
        }

        toast.add({ severity: 'success', summary: 'Saved', detail: 'Routine updated', life: 3000 })
      } else {
        // ── Create path ────────────────────────────────────────────────────
        const created = await createMutation.mutateAsync({
          ...form.value,
          name: form.value.name.trim(),
          schedule_config: scheduleConfig,
        })

        if (localActions.value.length > 0) {
          const newIds: number[] = []
          for (const action of localActions.value) {
            const newAction = await routinesApi.createAction(created.id, {
              action_type: action.action_type,
              config: action.config,
            })
            newIds.push(newAction.id)
          }
          await routinesApi.reorderActions(created.id, newIds)
        }

        toast.add({
          severity: 'success',
          summary: 'Created',
          detail: `Routine '${created.name}' created`,
          life: 3000,
        })
      }

      await router.push({ name: 'routines' })
    } catch (e) {
      if (e instanceof HttpError && e.status === 409) {
        saveValidationErrors.value = { name: 'A routine with this name already exists' }
      } else {
        saveError.value = e instanceof Error ? e.message : 'Save failed'
      }
    } finally {
      saving.value = false
    }
  }

  async function cancel(): Promise<void> {
    await router.push({ name: 'routines' })
  }

  return {
    isEditMode,
    isAuthenticated,
    routine,
    loading,
    pageError,
    form,
    saveError,
    saveValidationErrors,
    saving,
    cronExpression,
    intervalSecondsStr,
    actionForm,
    echoMessage,
    sleepSecondsStr,
    actionError,
    actionConfigError,
    localActions,
    deleteDialogOpen,
    deleteError,
    deleting,
    actionConfigSummary,
    onActionTypeChange,
    save,
    cancel,
    reorderActions,
    removeAction,
    addAction,
    openDeleteDialog,
    confirmDelete,
  }
}
