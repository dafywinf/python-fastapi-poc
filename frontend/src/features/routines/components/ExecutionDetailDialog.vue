<script setup lang="ts">
import { ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import type { ActiveRoutineExecution } from '../../../types/routine'
import { routinesApi } from '../../../api/routines'
import { formatDate } from '../../../utils/date'

const props = defineProps<{
  visible: boolean
  executionId: number | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const execution = ref<ActiveRoutineExecution | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

watch(
  () => props.executionId,
  async (id) => {
    if (id === null) {
      execution.value = null
      return
    }
    loading.value = true
    error.value = null
    try {
      execution.value = await routinesApi.getExecution(id)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load execution'
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)

function durationLabel(startedAt: string | null, completedAt: string | null): string {
  if (!startedAt || !completedAt) return '—'
  const secs = Math.floor(
    (new Date(completedAt).getTime() - new Date(startedAt).getTime()) / 1000,
  )
  return `${secs}s`
}

function actionStatusSeverity(status: string): 'success' | 'warn' | 'danger' | 'secondary' {
  if (status === 'running') return 'warn'
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'danger'
  return 'secondary'
}
</script>

<template>
  <Dialog
    :visible="visible"
    :modal="true"
    :header="execution?.routine_name ?? 'Execution Detail'"
    :style="{ width: '36rem' }"
    @update:visible="emit('update:visible', $event)"
  >
    <div v-if="loading" class="py-6 text-center text-sm text-app-muted">Loading…</div>

    <div v-else-if="error" class="py-4 text-sm text-red-600">{{ error }}</div>

    <div v-else-if="execution" class="flex flex-col gap-4">
      <!-- Execution summary -->
      <div class="flex flex-wrap gap-2 items-center">
        <Tag
          :value="execution.status"
          :severity="
            execution.status === 'completed'
              ? 'success'
              : execution.status === 'failed'
                ? 'danger'
                : execution.status === 'running'
                  ? 'warn'
                  : 'secondary'
          "
        />
        <Tag :value="execution.triggered_by" severity="secondary" />
        <span class="text-xs text-app-muted ml-auto">
          {{ durationLabel(execution.started_at, execution.completed_at) }}
        </span>
      </div>

      <!-- Timing row -->
      <div class="grid grid-cols-2 gap-2 text-xs text-app-muted">
        <div>
          <div class="font-medium text-app-text mb-0.5">Started</div>
          <div>{{ execution.started_at ? formatDate(execution.started_at) : '—' }}</div>
        </div>
        <div>
          <div class="font-medium text-app-text mb-0.5">Completed</div>
          <div>{{ execution.completed_at ? formatDate(execution.completed_at) : '—' }}</div>
        </div>
      </div>

      <!-- Actions -->
      <div v-if="execution.action_executions.length > 0">
        <div class="text-[11px] font-bold uppercase tracking-widest text-gray-400 mb-2">Actions</div>
        <div class="divide-y divide-app-border/60 border border-app-border rounded overflow-hidden">
          <div
            v-for="action in execution.action_executions"
            :key="action.id"
            class="flex items-center gap-3 px-3 py-2 text-xs"
          >
            <!-- Position badge -->
            <span
              class="w-5 h-5 rounded-sm text-[10px] flex items-center justify-center font-bold shrink-0"
              :class="{
                'bg-app-amber/20 text-yellow-700': action.status === 'running',
                'bg-green-100 text-green-700': action.status === 'completed',
                'bg-red-100 text-app-red': action.status === 'failed',
                'bg-gray-100 text-gray-400': action.status === 'pending',
              }"
            >
              {{ action.position }}
            </span>

            <!-- Status -->
            <Tag
              :value="action.status"
              :severity="actionStatusSeverity(action.status)"
              class="shrink-0 !text-[10px] !px-1.5 !py-0"
            />

            <!-- Type + config -->
            <span class="text-slate-500 truncate flex-1">
              <span class="font-mono text-app-muted mr-1">{{ action.action_type }}</span>
              <template v-if="action.action_type === 'echo'">
                &ldquo;{{ (action.config as { message: string }).message }}&rdquo;
              </template>
              <template v-else-if="action.action_type === 'sleep'">
                {{ (action.config as { seconds: number }).seconds }}s
              </template>
            </span>

            <!-- Start time + duration -->
            <div class="shrink-0 text-right text-app-muted font-mono">
              <div v-if="action.started_at">{{ formatDate(action.started_at) }}</div>
              <div v-if="action.started_at" class="text-[10px]">
                {{ durationLabel(action.started_at, action.completed_at) }}
              </div>
              <div v-else>—</div>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="text-xs text-app-muted italic">No action details recorded</div>
    </div>
  </Dialog>
</template>
