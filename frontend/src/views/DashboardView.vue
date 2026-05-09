<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { RouterLink } from 'vue-router'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import ActiveExecutionsList from '../features/routines/components/ActiveExecutionsList.vue'
import ExecutionCard from '../features/routines/components/ExecutionCard.vue'
import { useRoutinesQuery, useExecutionHistoryQuery } from '../features/routines/queries/useRoutineQueries'
import { routineKeys } from '../features/routines/queries/keys'
import { useAuth } from '../composables/useAuth'
import { usePersistedRef } from '../composables/usePersistedRef'
import { routinesApi } from '../api/routines'
import { useQueryClient } from '@tanstack/vue-query'
import type { ActiveRoutineExecution, Routine, RoutineExecution } from '../types/routine'

const toast = useToast()
const queryClient = useQueryClient()
const { isAuthenticated } = useAuth()

// ── Routines ──────────────────────────────────────────────────────────────────
const routinesSearchQuery = ref('')
const routinesDebouncedSearch = ref('')
let routinesDebounceTimer: ReturnType<typeof setTimeout> | null = null
watch(routinesSearchQuery, (val) => {
  if (routinesDebounceTimer) clearTimeout(routinesDebounceTimer)
  routinesDebounceTimer = setTimeout(() => { routinesDebouncedSearch.value = val }, 300)
})

const runNowLoading = ref<Record<number, boolean>>({})

async function runNow(routine: Routine): Promise<void> {
  runNowLoading.value[routine.id] = true
  try {
    await routinesApi.runNow(routine.id)
    toast.add({
      severity: 'success',
      summary: 'Queued',
      detail: `${routine.name} added to the execution queue`,
      life: 3000,
    })
    await queryClient.invalidateQueries({ queryKey: routineKeys.activeExecutions() })
  } catch (e) {
    toast.add({
      severity: 'error',
      summary: 'Run failed',
      detail: e instanceof Error ? e.message : 'Failed to queue run',
      life: 4000,
    })
  } finally {
    delete runNowLoading.value[routine.id]
  }
}

// ── Schedule ──────────────────────────────────────────────────────────────────
const scheduleDialogOpen = ref(false)
const schedulingRoutine = ref<Routine | null>(null)
const scheduledFor = ref<Date | null>(null)
const scheduleLoading = ref(false)
const scheduleError = ref<string | null>(null)

function openScheduleDialog(routine: Routine): void {
  schedulingRoutine.value = routine
  scheduledFor.value = null
  scheduleError.value = null
  scheduleDialogOpen.value = true
}

async function confirmSchedule(): Promise<void> {
  if (!schedulingRoutine.value || !scheduledFor.value) {
    scheduleError.value = 'Please pick a date and time'
    return
  }
  scheduleError.value = null
  scheduleLoading.value = true
  try {
    await routinesApi.runNow(schedulingRoutine.value.id, scheduledFor.value)
    toast.add({
      severity: 'success',
      summary: 'Scheduled',
      detail: `${schedulingRoutine.value.name} scheduled for ${scheduledFor.value.toLocaleString()}`,
      life: 4000,
    })
    scheduleDialogOpen.value = false
    await queryClient.invalidateQueries({ queryKey: routineKeys.activeExecutions() })
  } catch (e) {
    scheduleError.value = e instanceof Error ? e.message : 'Failed to schedule'
  } finally {
    scheduleLoading.value = false
  }
}

// ── Recent History ────────────────────────────────────────────────────────────
const rowLimitOptions = [
  { label: '5', value: 5 },
  { label: '10', value: 10 },
  { label: '20', value: 20 },
  { label: '50', value: 50 },
]

const historyWindowOptions = [
  { label: 'Last 1 min', value: 1 },
  { label: 'Last 5 min', value: 5 },
  { label: 'Last 10 min', value: 10 },
  { label: 'Last 20 min', value: 20 },
]
const historyWindow = usePersistedRef<number>('dashboard.historyWindow', 5)
const historyQuery = useExecutionHistoryQuery(100, 0, undefined, undefined, historyWindow, 2000)

// ── Routines row limit + query ────────────────────────────────────────────────
const routinesLimit = usePersistedRef<number>('dashboard.routinesLimit', 10)
const routinesQuery = useRoutinesQuery(routinesDebouncedSearch, routinesLimit, 0)
const routines = computed(() => routinesQuery.data.value?.items ?? [])

// ── Recent history expand (lazy-load action details per card) ─────────────────
const historyExpandedData = reactive<Record<number, ActiveRoutineExecution>>({})
const historyExpandLoading = reactive<Record<number, boolean>>({})

async function onHistoryExpand(id: number): Promise<void> {
  if (historyExpandedData[id] || historyExpandLoading[id]) return
  historyExpandLoading[id] = true
  try {
    const full = await routinesApi.getExecution(id)
    historyExpandedData[id] = full
  } catch (e) {
    toast.add({
      severity: 'error',
      summary: 'Failed to load execution details',
      detail: e instanceof Error ? e.message : String(e),
      life: 5000,
    })
  } finally {
    delete historyExpandLoading[id]
  }
}

function toHistoryCardExecution(e: RoutineExecution): ActiveRoutineExecution {
  return historyExpandedData[e.id] ?? { ...(e as unknown as ActiveRoutineExecution), action_executions: [] }
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <!-- Page header -->
    <div class="flex items-end justify-between mb-1">
      <div>
        <div class="text-[11px] font-light uppercase tracking-[0.18em] text-gray-400 mb-0.5">Overview</div>
        <h1 class="text-[26px] font-bold tracking-tight text-app-text m-0 leading-tight">Execution Dashboard</h1>
      </div>
    </div>

    <!-- ── Execution Queue ─────────────────────────────────────────────────── -->
    <div data-testid="dashboard-queue-panel" class="bg-app-card border border-app-border rounded overflow-hidden shadow-sm">
      <div class="px-4 py-2.5 border-b border-app-border/60 bg-app-border/20 flex items-center gap-2">
        <span class="w-1.5 h-4 bg-app-red rounded-full shrink-0"></span>
        <h2 class="text-[11px] font-bold uppercase tracking-[0.05em] text-gray-500 m-0">Execution Queue</h2>
      </div>

      <ActiveExecutionsList />
    </div>

    <!-- ── Recent History ─────────────────────────────────────────────────── -->
    <div data-testid="dashboard-history-panel" class="bg-app-card border border-app-border rounded overflow-hidden shadow-sm">
      <div class="px-4 py-2.5 border-b border-app-border/60 bg-app-border/20 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="w-1.5 h-4 bg-app-amber rounded-full shrink-0"></span>
          <h2 class="text-[11px] font-bold uppercase tracking-[0.05em] text-gray-500 m-0">Recent History</h2>
        </div>
        <div class="flex items-center gap-3">
          <Select
            v-model="historyWindow"
            :options="historyWindowOptions"
            option-label="label"
            option-value="value"
            class="w-28 text-xs"
          />
          <RouterLink
            to="/history"
            class="text-[10px] font-bold uppercase tracking-widest text-app-red hover:underline no-underline"
          >
            View all →
          </RouterLink>
        </div>
      </div>

      <div v-if="historyQuery.isPending.value" class="px-4 py-6 text-center text-sm text-app-muted">
        Loading…
      </div>
      <div v-else-if="!historyQuery.data.value?.items.length" class="px-4 py-6 text-center text-sm text-app-muted">
        No executions in the last {{ historyWindow }} minute{{ historyWindow === 1 ? '' : 's' }}
      </div>
      <div v-else class="divide-y divide-app-border/60">
        <ExecutionCard
          v-for="execution in historyQuery.data.value?.items"
          :key="execution.id"
          :execution="toHistoryCardExecution(execution)"
          :detail-loading="historyExpandLoading[execution.id] === true"
          @expand="onHistoryExpand"
        />
      </div>
    </div>

    <!-- ── Routines ───────────────────────────────────────────────────────── -->
    <div data-testid="dashboard-routines-panel" class="bg-app-card border border-app-border rounded overflow-hidden shadow-sm">
      <div class="px-4 py-2.5 border-b border-app-border/60 bg-app-border/20 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="w-1.5 h-4 bg-app-teal rounded-full shrink-0"></span>
          <h2 class="text-[11px] font-bold uppercase tracking-[0.05em] text-gray-500 m-0">Routines</h2>
        </div>
        <div class="flex items-center gap-2">
          <InputText
            v-model="routinesSearchQuery"
            placeholder="Search…"
            class="!py-1 !text-[12px] w-36"
          />
          <Select
            v-model="routinesLimit"
            :options="rowLimitOptions"
            option-label="label"
            option-value="value"
            class="w-20 text-xs"
          />
          <RouterLink
            to="/routines"
            class="text-[10px] font-bold uppercase tracking-widest text-app-red hover:underline no-underline"
          >
            Manage →
          </RouterLink>
        </div>
      </div>

      <div v-if="routinesQuery.isPending.value" class="px-4 py-6 text-center text-sm text-app-muted">
        Loading…
      </div>
      <div v-else-if="routines.length === 0" class="px-4 py-6 text-center text-sm text-app-muted">
        No routines configured
      </div>
      <DataTable v-else :value="routines" size="small" striped-rows>
        <Column field="name" header="Name">
          <template #body="{ data }">
            <RouterLink
              :to="`/routines/${data.id}`"
              class="text-sm font-medium text-app-text no-underline hover:underline"
            >
              {{ data.name }}
            </RouterLink>
          </template>
        </Column>
        <Column field="schedule_type" header="Schedule">
          <template #body="{ data }">
            <Tag
              :value="data.schedule_type"
              :severity="
                data.schedule_type === 'cron'
                  ? 'primary'
                  : data.schedule_type === 'interval'
                    ? 'info'
                    : 'secondary'
              "
              class="!text-[10px] !px-1.5 !py-0"
            />
          </template>
        </Column>
        <Column field="is_active" header="Active">
          <template #body="{ data }">
            <span :class="data.is_active ? 'text-green-600 font-semibold' : 'text-app-muted'">
              {{ data.is_active ? '✓' : '—' }}
            </span>
          </template>
        </Column>
        <Column field="description" header="Description">
          <template #body="{ data }">
            <span class="text-xs text-app-muted truncate">{{ data.description ?? '—' }}</span>
          </template>
        </Column>
        <Column header="Actions">
          <template #body="{ data }">
            <div v-if="isAuthenticated" class="flex gap-1.5 justify-end">
              <Button
                label="▶ Run"
                size="small"
                :disabled="!!runNowLoading[data.id]"
                @click="runNow(data)"
              />
              <Button
                label="⏰ Schedule"
                size="small"
                severity="secondary"
                @click="openScheduleDialog(data)"
              />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- ── Schedule Dialog ────────────────────────────────────────────────── -->
    <Dialog
      :visible="scheduleDialogOpen"
      :modal="true"
      :header="`Schedule: ${schedulingRoutine?.name ?? ''}`"
      @update:visible="scheduleDialogOpen = false"
    >
      <div class="flex flex-col gap-4 py-1">
        <p class="text-sm text-app-muted m-0">
          Pick a date and time. The routine will be added to the queue and will
          start executing once that time arrives.
        </p>
        <DatePicker
          v-model="scheduledFor"
          show-time
          hour-format="24"
          :min-date="new Date()"
          inline
        />
        <div
          v-if="scheduleError"
          class="px-4 py-2.5 rounded-md text-sm bg-red-50 text-red-600 border border-red-200"
        >
          {{ scheduleError }}
        </div>
      </div>
      <template #footer>
        <Button
          label="Cancel"
          severity="secondary"
          @click="scheduleDialogOpen = false"
        />
        <Button
          :label="scheduleLoading ? 'Scheduling…' : 'Schedule'"
          :disabled="scheduleLoading || !scheduledFor"
          @click="confirmSchedule"
        />
      </template>
    </Dialog>
  </div>
</template>
