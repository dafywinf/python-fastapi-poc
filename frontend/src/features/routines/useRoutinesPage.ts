import { computed, ref, watch } from 'vue'
import { useQueryClient } from '@tanstack/vue-query'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useAuth } from '../../composables/useAuth'
import type { Routine } from '../../types/routine'
import { useRoutinesQuery } from './queries/useRoutineQueries'
import { routineKeys } from './queries/keys'
import {
  useDeleteRoutineMutation,
  useRunRoutineMutation,
} from './mutations/useRoutineMutations'

export function useRoutinesPage() {
  const router = useRouter()
  const toast = useToast()
  const queryClient = useQueryClient()
  const { isAuthenticated } = useAuth()

  const searchQuery = ref('')
  const debouncedSearch = ref('')
  const limit = ref(25)
  const page = ref(1)
  const offset = computed(() => (page.value - 1) * limit.value)

  let debounceTimer: ReturnType<typeof setTimeout> | null = null
  watch(searchQuery, (val) => {
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => {
      debouncedSearch.value = val
    }, 300)
  })

  watch([searchQuery, limit], () => {
    page.value = 1
  })

  const routinesQuery = useRoutinesQuery(debouncedSearch, limit, offset)

  const deleteMutation = useDeleteRoutineMutation()
  const runMutation = useRunRoutineMutation()

  const routines = computed(() => routinesQuery.data.value?.items ?? [])
  const routinesTotal = computed(() => routinesQuery.data.value?.total ?? 0)
  const loadingRoutines = computed(() => routinesQuery.isPending.value)
  const routinesError = computed(() =>
    routinesQuery.error.value instanceof Error
      ? routinesQuery.error.value.message
      : null,
  )

  function goToEdit(routine: Routine): void {
    void router.push({ name: 'routine-edit', params: { id: routine.id } })
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
        summary: 'Queued',
        detail: `${routine.name} added to the execution queue`,
        life: 3000,
      })
      await queryClient.invalidateQueries({ queryKey: routineKeys.activeExecutions() })
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to queue run'
      toast.add({
        severity: 'error',
        summary: 'Run Now',
        detail: msg,
        life: 4000,
      })
    } finally {
      delete runNowLoading.value[routine.id]
    }
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
    routinesTotal,
    loadingRoutines,
    routinesError,
    searchQuery,
    limit,
    page,
    durationSeconds,
    goToEdit,
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
