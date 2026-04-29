<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { RouterLink } from 'vue-router'
import Tag from 'primevue/tag'
import { formatDate } from '../../../utils/date'
import type { Action, ActionExecution, ActiveRoutineExecution } from '../../../types/routine'

const props = defineProps<{
  execution: ActiveRoutineExecution
  queuePosition?: number
  detailLoading?: boolean
  detailError?: boolean
  // Routine action definitions — used for queued execution preview
  routineActions?: Action[]
}>()

const emit = defineEmits<{
  expand: [id: number]
}>()

// Running executions auto-expand; others start collapsed
const expanded = ref(props.execution.status === 'running')

// When a queued entry transitions to running, auto-expand it
watch(
  () => props.execution.status,
  (status) => {
    if (status === 'running') {
      expanded.value = true
    }
  },
)

function toggleExpand(): void {
  expanded.value = !expanded.value
  if (expanded.value && props.execution.status !== 'running' && props.execution.action_executions.length === 0) {
    emit('expand', props.execution.id)
  }
}

const headerBorderClass = computed(() => {
  switch (props.execution.status) {
    case 'running': return 'border-l-app-amber bg-app-amber/10'
    case 'completed': return 'border-l-green-500 bg-green-50/20'
    case 'failed': return 'border-l-app-red bg-red-50/10'
    default: return 'border-l-gray-300'
  }
})

function elapsedSeconds(from: string | null): number {
  if (!from) return 0
  return Math.floor((Date.now() - new Date(from).getTime()) / 1000)
}

function durationSeconds(from: string | null, to: string | null): number | null {
  if (!from || !to) return null
  return Math.floor((new Date(to).getTime() - new Date(from).getTime()) / 1000)
}

function actionStatusSeverity(status: string): 'success' | 'warn' | 'danger' | 'secondary' {
  if (status === 'running') return 'warn'
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'danger'
  return 'secondary'
}

function positionBadgeClass(action: ActionExecution): string {
  if (action.status === 'running') return 'bg-app-amber/20 text-yellow-700'
  if (action.status === 'completed') return 'bg-green-100 text-green-700'
  if (action.status === 'failed') return 'bg-red-100 text-app-red'
  return 'bg-gray-100 text-gray-400'
}

function actionRowBg(action: ActionExecution): string {
  if (action.status === 'running') return 'bg-app-amber/5'
  if (action.status === 'completed') return 'bg-green-50/30'
  if (action.status === 'failed') return 'bg-red-50/20'
  return ''
}

function actionConfigSummary(action: { action_type: string; config: Record<string, unknown> }): string {
  if (action.action_type === 'echo') return `"${(action.config as { message: string }).message}"`
  if (action.action_type === 'sleep') return `${(action.config as { seconds: number }).seconds}s`
  return ''
}
</script>

<template>
  <div>
    <!-- ── Running header ────────────────────────────────────────────────── -->
    <div
      v-if="props.execution.status === 'running'"
      data-testid="execution-card-header"
      class="flex items-center justify-between px-4 py-2.5 border-l-2 cursor-pointer select-none"
      :class="headerBorderClass"
      @click="toggleExpand"
    >
      <div class="flex items-center gap-2 min-w-0">
        <span class="w-2 h-2 rounded-full bg-app-amber animate-pulse shrink-0" />
        <RouterLink
          :to="`/routines/${props.execution.routine_id}`"
          class="font-semibold text-app-text text-sm no-underline hover:underline truncate"
          @click.stop
        >
          {{ props.execution.routine_name }}
        </RouterLink>
        <Tag value="running" severity="warn" class="shrink-0 !text-[10px] !px-1.5 !py-0" />
        <Tag :value="props.execution.triggered_by" severity="secondary" class="shrink-0 !text-[10px] !px-1.5 !py-0" />
      </div>
      <div class="flex items-center gap-2 shrink-0 ml-2">
        <span class="text-[11px] font-mono text-yellow-700 font-bold">
          {{ elapsedSeconds(props.execution.started_at) }}s
        </span>
        <span class="text-gray-400 text-[10px] transition-transform duration-150" :class="expanded ? 'rotate-90' : ''">▶</span>
      </div>
    </div>

    <!-- ── Queued header ─────────────────────────────────────────────────── -->
    <div
      v-else-if="props.execution.status === 'queued'"
      data-testid="execution-card-header"
      class="flex items-center justify-between px-4 py-2.5 border-l-2 cursor-pointer select-none"
      :class="headerBorderClass"
      @click="toggleExpand"
    >
      <div class="flex items-center gap-2 min-w-0">
        <span v-if="props.queuePosition !== undefined" class="text-gray-400 text-[11px] font-mono font-bold shrink-0">
          #{{ props.queuePosition }}
        </span>
        <RouterLink
          :to="`/routines/${props.execution.routine_id}`"
          class="font-medium text-slate-700 text-sm no-underline hover:underline truncate"
          @click.stop
        >
          {{ props.execution.routine_name }}
        </RouterLink>
        <Tag value="queued" severity="secondary" class="shrink-0 !text-[10px] !px-1.5 !py-0" />
        <Tag :value="props.execution.triggered_by" severity="secondary" class="shrink-0 !text-[10px] !px-1.5 !py-0" />
      </div>
      <div class="flex items-center gap-2 shrink-0 ml-2">
        <div class="text-right">
          <div class="text-[11px] text-gray-400 font-mono">Scheduled {{ formatDate(props.execution.scheduled_for) }}</div>
          <div class="text-[10px] text-gray-400">queued {{ elapsedSeconds(props.execution.queued_at) }}s ago</div>
        </div>
        <span class="text-gray-400 text-[10px] transition-transform duration-150" :class="expanded ? 'rotate-90' : ''">▶</span>
      </div>
    </div>

    <!-- ── Completed / Failed header ─────────────────────────────────────── -->
    <div
      v-else
      data-testid="execution-card-header"
      class="flex items-center justify-between px-4 py-2.5 border-l-2 cursor-pointer select-none"
      :class="headerBorderClass"
      @click="toggleExpand"
    >
      <div class="flex items-center gap-2 min-w-0">
        <RouterLink
          :to="`/routines/${props.execution.routine_id}`"
          class="font-medium text-app-text text-sm no-underline hover:underline truncate"
          @click.stop
        >
          {{ props.execution.routine_name }}
        </RouterLink>
        <Tag
          :value="props.execution.status"
          :severity="props.execution.status === 'completed' ? 'success' : 'danger'"
          class="shrink-0 !text-[10px] !px-1.5 !py-0"
        />
        <Tag :value="props.execution.triggered_by" severity="secondary" class="shrink-0 !text-[10px] !px-1.5 !py-0" />
      </div>
      <div class="flex items-center gap-2 shrink-0 ml-2">
        <div class="text-right font-mono text-[11px] text-app-muted">
          <div v-if="props.execution.started_at">{{ formatDate(props.execution.started_at) }}</div>
          <div v-if="durationSeconds(props.execution.started_at, props.execution.completed_at) !== null">
            {{ durationSeconds(props.execution.started_at, props.execution.completed_at) }}s
          </div>
        </div>
        <span class="text-gray-400 text-[10px] transition-transform duration-150" :class="expanded ? 'rotate-90' : ''">▶</span>
      </div>
    </div>

    <!-- ── Expanded body ─────────────────────────────────────────────────── -->
    <template v-if="expanded">
      <div
        v-if="props.detailLoading"
        class="px-4 py-3 text-xs text-app-muted italic border-t border-app-border/60"
      >
        Loading…
      </div>

      <div
        v-else-if="props.detailError"
        class="px-4 py-3 text-xs text-app-red italic border-t border-app-border/60"
      >
        Failed to load action details
      </div>

      <!-- Queued: show routine action previews -->
      <template v-else-if="props.execution.status === 'queued'">
        <template v-if="props.routineActions && props.routineActions.length > 0">
          <div
            v-for="action in props.routineActions"
            :key="action.id"
            class="flex items-center gap-3 px-4 py-2 border-t border-app-border/60"
          >
            <span class="w-5 h-5 rounded-sm text-[10px] flex items-center justify-center font-bold shrink-0 bg-gray-100 text-gray-400">
              {{ action.position }}
            </span>
            <Tag value="pending" severity="secondary" class="shrink-0 !text-[10px] !px-1.5 !py-0" />
            <span class="text-xs text-slate-500 truncate flex-1">
              <span class="font-mono text-app-muted mr-1">{{ action.action_type }}</span>
              {{ actionConfigSummary(action) }}
            </span>
            <span class="text-xs text-app-muted font-mono">—</span>
          </div>
        </template>
        <div v-else class="px-4 py-3 text-xs text-app-muted italic border-t border-app-border/60">
          No actions configured
        </div>
      </template>

      <!-- Running / Completed / Failed: show action execution rows -->
      <template v-else-if="props.execution.action_executions.length > 0">
        <div
          v-for="action in props.execution.action_executions"
          :key="action.id"
          class="flex items-center gap-3 px-4 py-2 border-t border-app-border/60"
          :class="actionRowBg(action)"
        >
          <span
            class="w-5 h-5 rounded-sm text-[10px] flex items-center justify-center font-bold shrink-0"
            :class="positionBadgeClass(action)"
          >
            {{ action.position }}
          </span>
          <Tag
            :value="action.status"
            :severity="actionStatusSeverity(action.status)"
            class="shrink-0 !text-[10px] !px-1.5 !py-0"
          />
          <span class="text-xs text-slate-500 truncate flex-1">
            <span class="font-mono text-app-muted mr-1">{{ action.action_type }}</span>
            {{ actionConfigSummary(action) }}
          </span>
          <div class="ml-auto text-right text-app-muted shrink-0 font-mono">
            <template v-if="action.status === 'running' && action.started_at">
              <div class="text-xs text-yellow-700 font-bold">{{ elapsedSeconds(action.started_at) }}s</div>
              <div class="text-[10px]">{{ formatDate(action.started_at) }}</div>
            </template>
            <template v-else-if="action.status !== 'pending' && action.started_at">
              <div class="text-xs">{{ durationSeconds(action.started_at, action.completed_at) ?? '—' }}s</div>
              <div class="text-[10px]">{{ formatDate(action.started_at) }}</div>
            </template>
            <template v-else>
              <span class="text-xs">—</span>
            </template>
          </div>
        </div>
      </template>

      <!-- Running but no action rows yet -->
      <div
        v-else-if="props.execution.status === 'running'"
        class="px-4 py-2 text-xs text-app-muted italic border-t border-app-border/60"
      >
        Started {{ formatDate(props.execution.started_at ?? '') }}
      </div>

      <!-- Completed/failed with no action data (loading failed or no actions) -->
      <div
        v-else
        class="px-4 py-2 text-xs text-app-muted italic border-t border-app-border/60"
      >
        No action details available
      </div>
    </template>
  </div>
</template>
