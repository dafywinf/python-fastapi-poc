<script setup lang="ts">
import type { Action, ActiveRoutineExecution } from '../../../types/routine'
import ExecutionCard from './ExecutionCard.vue'

const props = defineProps<{
  executions: ActiveRoutineExecution[]
  loading: boolean
  error: string | null
  routineActions: Record<number, Action[]>
  detailLoading: Record<number, boolean>
}>()

const emit = defineEmits<{
  expand: [id: number]
}>()
</script>

<template>
  <div>
    <div
      v-if="props.error"
      data-testid="execution-queue-error"
      class="px-4 py-2 text-sm text-red-600"
    >
      {{ props.error }}
    </div>

    <div
      v-if="props.loading"
      data-testid="execution-queue-loading"
      class="px-4 py-6 text-center text-sm text-app-muted"
    >
      Loading…
    </div>

    <div
      v-else-if="props.executions.length === 0"
      data-testid="execution-queue-empty"
      class="px-4 py-6 text-center text-[13px] text-gray-400"
    >
      Queue is empty
    </div>

    <div v-else class="divide-y divide-app-border/60">
      <ExecutionCard
        v-for="(execution, index) in props.executions"
        :key="execution.id"
        :execution="execution"
        :queue-position="execution.status === 'queued' ? index + 1 : undefined"
        :routine-actions="execution.status === 'queued' ? props.routineActions[execution.routine_id] : undefined"
        :detail-loading="props.detailLoading[execution.id] === true"
        @expand="emit('expand', $event)"
      />
    </div>
  </div>
</template>
