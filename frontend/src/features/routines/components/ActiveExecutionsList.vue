<script setup lang="ts">
import { reactive } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useActiveExecutionsPage } from '../useActiveExecutionsPage'
import { routinesApi } from '../../../api/routines'
import type { Action } from '../../../types/routine'
import ExecutionQueue from './ExecutionQueue.vue'

const toast = useToast()
const { executions, loading, error } = useActiveExecutionsPage()

// Routine action definitions for queued execution previews, keyed by routine_id
const routineActions = reactive<Record<number, Action[]>>({})
const routineActionsLoading = reactive<Record<number, boolean>>({})

async function onExpand(executionId: number): Promise<void> {
  const execution = executions.value.find((e) => e.id === executionId)
  if (!execution || execution.status !== 'queued') return
  const routineId = execution.routine_id
  if (routineActions[routineId] !== undefined || routineActionsLoading[executionId]) return
  routineActionsLoading[executionId] = true
  try {
    const routine = await routinesApi.get(routineId)
    routineActions[routineId] = routine.actions
  } catch (e) {
    toast.add({
      severity: 'error',
      summary: 'Failed to load action preview',
      detail: e instanceof Error ? e.message : String(e),
      life: 5000,
    })
  } finally {
    delete routineActionsLoading[executionId]
  }
}
</script>

<template>
  <ExecutionQueue
    :executions="executions"
    :loading="loading"
    :error="error"
    :routine-actions="routineActions"
    :detail-loading="routineActionsLoading"
    @expand="onExpand"
  />
</template>
