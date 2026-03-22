<template>
  <div class="flex flex-col gap-5">
    <!-- ── Header ─────────────────────────────────────────────────────────── -->
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-slate-900 m-0">Routines</h1>
      <Button v-if="isAuthenticated" label="+ New Routine" @click="openCreate" />
    </div>

    <div v-if="routinesError" class="px-4 py-2.5 rounded-md text-sm bg-red-50 text-red-600 border border-red-200">
      {{ routinesError }}
    </div>

    <!-- ── Panel 1: Configured Routines ───────────────────────────────────── -->
    <div class="border border-slate-200 rounded-lg overflow-hidden">
      <DataTable :value="routines" :loading="loadingRoutines">
        <Column field="name" header="Name">
          <template #body="{ data }">
            <RouterLink :to="`/routines/${data.id}`" class="text-indigo-700 font-medium no-underline hover:underline">
              {{ data.name }}
            </RouterLink>
          </template>
        </Column>
        <Column field="schedule_type" header="Schedule">
          <template #body="{ data }">
            <Tag
              :value="data.schedule_type"
              :severity="data.schedule_type === 'cron' ? 'primary' : data.schedule_type === 'interval' ? 'info' : 'secondary'"
            />
          </template>
        </Column>
        <Column field="is_active" header="Active">
          <template #body="{ data }">
            <span :class="data.is_active ? 'text-green-600 font-semibold' : 'text-slate-400'">
              {{ data.is_active ? '✓' : '—' }}
            </span>
          </template>
        </Column>
        <Column header="Actions">
          <template #body="{ data }">
            <div v-if="isAuthenticated" class="flex gap-1.5 justify-end">
              <Button label="Edit" size="small" severity="secondary" @click="openEdit(data)" />
              <Button label="Delete" size="small" severity="danger" @click="openDelete(data)" />
              <Button label="▶ Run" size="small" :disabled="!!runNowLoading[data.id]" @click="runNow(data)" />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- ── Panels 2 & 3: Executing + History ──────────────────────────────── -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- Currently Executing -->
      <div class="border border-slate-200 rounded-lg overflow-hidden">
        <div class="px-4 py-3 border-b border-slate-200">
          <h2 class="text-sm font-semibold text-slate-900 m-0">Currently Executing</h2>
        </div>
        <div v-if="activeError" class="px-4 py-2 text-sm text-red-600">{{ activeError.message }}</div>
        <div v-if="loadingActive" class="px-4 py-6 text-center text-sm text-slate-400">Loading…</div>
        <div v-else-if="!activeExecutions || !activeExecutions.length" class="px-4 py-6 text-center text-sm text-slate-400">
          None running
        </div>
        <table v-else class="w-full text-sm border-collapse">
          <tbody>
            <tr v-for="exec in activeExecutions" :key="exec.id" class="border-t border-slate-100">
              <td class="px-4 py-2.5 font-medium text-slate-800">
                <RouterLink :to="`/routines/${exec.routine_id}`" class="text-indigo-700 font-medium no-underline hover:underline">
                  {{ exec.routine_name }}
                </RouterLink>
              </td>
              <td class="px-4 py-2.5"><Tag value="running" severity="warn" /></td>
              <td class="px-4 py-2.5 text-slate-400 text-xs">{{ exec.triggered_by }}</td>
              <td class="px-4 py-2.5 text-slate-400 text-xs">{{ elapsedSeconds(exec.started_at) }}s</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Recent History -->
      <div class="border border-slate-200 rounded-lg overflow-hidden">
        <div class="px-4 py-3 border-b border-slate-200 flex items-center justify-between">
          <h2 class="text-sm font-semibold text-slate-900 m-0">Recent History</h2>
          <div class="flex items-center gap-3">
            <select v-model="historyLimit" class="text-xs border border-slate-200 rounded px-1.5 py-0.5 text-slate-600 bg-white">
              <option :value="5">5</option>
              <option :value="10">10</option>
              <option :value="20">20</option>
            </select>
            <RouterLink to="/history" class="text-xs text-indigo-600 hover:underline font-medium no-underline">View all →</RouterLink>
          </div>
        </div>
        <div v-if="historyError" class="px-4 py-2 text-sm text-red-600">{{ historyError.message }}</div>
        <div v-if="loadingHistory" class="px-4 py-6 text-center text-sm text-slate-400">Loading…</div>
        <div v-else-if="!historyExecutions || !historyExecutions.length" class="px-4 py-6 text-center text-sm text-slate-400">
          No history
        </div>
        <table v-else class="w-full text-sm border-collapse">
          <tbody>
            <tr v-for="exec in historyExecutions" :key="exec.id" class="border-t border-slate-100">
              <td class="px-4 py-2.5 font-medium text-slate-800">
                <RouterLink :to="`/routines/${exec.routine_id}`" class="text-indigo-700 font-medium no-underline hover:underline">
                  {{ exec.routine_name }}
                </RouterLink>
              </td>
              <td class="px-4 py-2.5">
                <Tag
                  :value="exec.status"
                  :severity="exec.status === 'completed' ? 'success' : exec.status === 'failed' ? 'danger' : 'warn'"
                />
              </td>
              <td class="px-4 py-2.5 text-slate-400 text-xs">{{ exec.triggered_by }}</td>
              <td class="px-4 py-2.5 text-slate-400 text-xs">
                {{ durationSeconds(exec.started_at, exec.completed_at) !== null ? `${durationSeconds(exec.started_at, exec.completed_at)}s` : '—' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── Create / Edit Dialog ───────────────────────────────────────────── -->
    <Dialog
      :visible="formDialogOpen"
      :modal="true"
      :header="editingRoutine ? 'Edit Routine' : 'New Routine'"
      @update:visible="formDialogOpen = false"
    >
      <form @submit.prevent="submitForm" class="flex flex-col gap-4">
        <div class="flex flex-col gap-1">
          <label for="routineName" class="text-sm font-medium text-slate-700">Name</label>
          <InputText inputId="routineName" v-model="form.name" placeholder="Enter name" required />
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-sm font-medium text-slate-700">Description</label>
          <Textarea v-model="form.description" rows="3" placeholder="Optional description" />
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-sm font-medium text-slate-700">Schedule Type</label>
          <Select
            v-model="form.schedule_type"
            :options="[{ label: 'manual', value: 'manual' }, { label: 'cron', value: 'cron' }, { label: 'interval', value: 'interval' }]"
            option-label="label"
            option-value="value"
            class="w-full"
          />
        </div>
        <div v-if="form.schedule_type === 'cron'" class="flex flex-col gap-1">
          <label class="text-sm font-medium text-slate-700">Cron Expression</label>
          <InputText v-model="cronExpression" placeholder="e.g. 0 * * * *" />
        </div>
        <div v-if="form.schedule_type === 'interval'" class="flex flex-col gap-1">
          <label class="text-sm font-medium text-slate-700">Interval (seconds)</label>
          <InputText v-model="intervalSecondsStr" type="number" min="1" placeholder="e.g. 60" />
        </div>
        <div class="flex items-center gap-2">
          <Checkbox v-model="form.is_active" :binary="true" inputId="isActive" />
          <label for="isActive" class="text-sm text-slate-700">Active</label>
        </div>
        <div v-if="formError" class="px-4 py-2.5 rounded-md text-sm bg-red-50 text-red-600 border border-red-200">
          {{ formError }}
        </div>
      </form>
      <template #footer>
        <Button label="Cancel" severity="secondary" @click="formDialogOpen = false" />
        <Button
          :label="submitting ? 'Saving…' : (editingRoutine ? 'Update' : 'Create')"
          :disabled="submitting"
          @click="submitForm"
        />
      </template>
    </Dialog>

    <!-- ── Delete Confirmation Dialog ────────────────────────────────────── -->
    <Dialog
      :visible="deleteDialogOpen"
      :modal="true"
      header="Delete Routine"
      @update:visible="deleteDialogOpen = false"
    >
      <p class="text-sm text-slate-600">
        Delete routine <strong>{{ deletingRoutine?.name }}</strong>? This cannot be undone.
      </p>
      <div v-if="deleteError" class="px-4 py-2.5 rounded-md text-sm bg-red-50 text-red-600 border border-red-200">
        {{ deleteError }}
      </div>
      <template #footer>
        <Button label="Cancel" severity="secondary" @click="deleteDialogOpen = false" />
        <Button label="Delete" severity="danger" :disabled="deleting" @click="confirmDelete" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import Checkbox from 'primevue/checkbox'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { routinesApi } from '../api/routines'
import { usePolling } from '../composables/usePolling'
import { useAuth } from '../composables/useAuth'
import type { Routine, RoutineCreate, RoutineUpdate } from '../types/routine'

const toast = useToast()
const { isAuthenticated } = useAuth()

// ── Panel 1: Configured Routines (local state, not polled) ─────────────────
const routines = ref<Routine[]>([])
const loadingRoutines = ref(false)
const routinesError = ref<string | null>(null)

async function loadRoutines(): Promise<void> {
  loadingRoutines.value = true
  routinesError.value = null
  try {
    routines.value = await routinesApi.list()
  } catch (e) {
    routinesError.value = e instanceof Error ? e.message : 'Failed to load routines'
  } finally {
    loadingRoutines.value = false
  }
}

onMounted(() => {
  void loadRoutines()
})

// ── Panel 2: Currently Executing (polled every 3s) ─────────────────────────
const {
  data: activeExecutions,
  loading: loadingActive,
  error: activeError,
  refresh: refreshActive,
} = usePolling(() => routinesApi.activeExecutions(), 3000)

// ── Panel 3: Recent History (polled every 5s) ──────────────────────────────
const historyLimit = ref<number>(10)

const {
  data: historyExecutions,
  loading: loadingHistory,
  error: historyError,
  refresh: refreshHistory,
} = usePolling(() => routinesApi.executionHistory(historyLimit.value), 5000)

watch(historyLimit, () => { void refreshHistory() })

// ── Helpers ────────────────────────────────────────────────────────────────
function elapsedSeconds(startedAt: string): number {
  return Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000)
}

function durationSeconds(startedAt: string, completedAt: string | null): number | null {
  if (!completedAt) return null
  return Math.floor((new Date(completedAt).getTime() - new Date(startedAt).getTime()) / 1000)
}

// ── CREATE / EDIT dialog ───────────────────────────────────────────────────
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
const submitting = ref(false)

// Local helpers for cron/interval schedule_config fields
const cronExpression = ref('')
const intervalSeconds = ref<number>(60)
const intervalSecondsStr = computed({
  get: () => String(intervalSeconds.value),
  set: (v: string) => { intervalSeconds.value = parseInt(v, 10) || 60 },
})

// Derive schedule_config from local helpers
const scheduleConfig = computed<RoutineCreate['schedule_config']>(() => {
  if (form.value.schedule_type === 'cron') {
    return cronExpression.value ? { cron: cronExpression.value } : null
  }
  if (form.value.schedule_type === 'interval') {
    return intervalSeconds.value > 0 ? { seconds: intervalSeconds.value } : null
  }
  return null
})

function openCreate(): void {
  editingRoutine.value = null
  form.value = { name: '', description: null, schedule_type: 'manual', schedule_config: null, is_active: true }
  cronExpression.value = ''
  intervalSeconds.value = 60
  formError.value = null
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
  // Pre-populate schedule config helpers
  if (routine.schedule_type === 'cron' && routine.schedule_config && 'cron' in routine.schedule_config) {
    cronExpression.value = routine.schedule_config.cron
  } else {
    cronExpression.value = ''
  }
  if (routine.schedule_type === 'interval' && routine.schedule_config && 'seconds' in routine.schedule_config) {
    intervalSeconds.value = routine.schedule_config.seconds
  } else {
    intervalSeconds.value = 60
  }
  formError.value = null
  formDialogOpen.value = true
}

async function submitForm(): Promise<void> {
  submitting.value = true
  formError.value = null
  try {
    const payload: RoutineCreate = {
      ...form.value,
      schedule_config: scheduleConfig.value,
    }
    if (editingRoutine.value) {
      const updated = await routinesApi.update(editingRoutine.value.id, payload as RoutineUpdate)
      const idx = routines.value.findIndex((r) => r.id === updated.id)
      if (idx !== -1) routines.value[idx] = updated
    } else {
      const created = await routinesApi.create(payload)
      routines.value.unshift(created)
    }
    formDialogOpen.value = false
  } catch (e) {
    formError.value = e instanceof Error ? e.message : 'Save failed'
  } finally {
    submitting.value = false
  }
}

// ── DELETE dialog ──────────────────────────────────────────────────────────
const deleteDialogOpen = ref(false)
const deletingRoutine = ref<Routine | null>(null)
const deleteError = ref<string | null>(null)
const deleting = ref(false)

function openDelete(routine: Routine): void {
  deletingRoutine.value = routine
  deleteError.value = null
  deleteDialogOpen.value = true
}

async function confirmDelete(): Promise<void> {
  if (!deletingRoutine.value) return
  deleting.value = true
  deleteError.value = null
  try {
    await routinesApi.delete(deletingRoutine.value.id)
    routines.value = routines.value.filter((r) => r.id !== deletingRoutine.value!.id)
    deleteDialogOpen.value = false
  } catch (e) {
    deleteError.value = e instanceof Error ? e.message : 'Delete failed'
  } finally {
    deleting.value = false
  }
}

// ── RUN NOW ────────────────────────────────────────────────────────────────
const runNowLoading = ref<Record<number, boolean>>({})

async function runNow(routine: Routine): Promise<void> {
  runNowLoading.value[routine.id] = true
  try {
    await routinesApi.runNow(routine.id)
    toast.add({ severity: 'success', summary: 'Started', detail: `${routine.name} is running`, life: 3000 })
    await refreshActive()
  } catch (e) {
    const msg = e instanceof Error ? e.message : 'Failed to start'
    toast.add({ severity: msg.includes('already running') ? 'warn' : 'error', summary: 'Run Now', detail: msg, life: 4000 })
  } finally {
    delete runNowLoading.value[routine.id]
  }
}
</script>
