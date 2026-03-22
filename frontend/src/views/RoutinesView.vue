<template>
  <div class="list-view">
    <!-- ── Panel 1: Configured Routines ───────────────────────────────────── -->
    <div class="list-view__header">
      <h1 class="list-view__title">Routines</h1>
      <button v-if="isAuthenticated" class="btn btn--primary" @click="openCreate">+ New Routine</button>
    </div>

    <div v-if="routinesError" class="alert alert--error">{{ routinesError }}</div>

    <div class="table-wrapper">
      <table class="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Schedule</th>
            <th>Active</th>
            <th class="col-actions">Actions</th>
          </tr>
        </thead>
        <tbody v-if="loadingRoutines">
          <tr>
            <td colspan="4" class="state-cell">
              <span class="spinner" aria-label="Loading" />
            </td>
          </tr>
        </tbody>
        <tbody v-else-if="routines.length === 0">
          <tr>
            <td colspan="4" class="state-cell">No routines configured. Create one to get started.</td>
          </tr>
        </tbody>
        <tbody v-else>
          <tr v-for="routine in routines" :key="routine.id" class="data-row">
            <td>
              <RouterLink :to="`/routines/${routine.id}`" class="row-link">{{ routine.name }}</RouterLink>
            </td>
            <td>
              <span class="badge" :class="scheduleBadgeClass(routine.schedule_type)">
                {{ routine.schedule_type }}
              </span>
            </td>
            <td>
              <span v-if="routine.is_active" class="checkmark" aria-label="Active">✓</span>
              <span v-else class="text-muted">—</span>
            </td>
            <td class="col-actions">
              <div class="action-cell">
                <button
                  v-if="isAuthenticated"
                  class="btn-icon"
                  title="Edit"
                  @click="openEdit(routine)"
                >
                  ✏️
                </button>
                <button
                  v-if="isAuthenticated"
                  class="btn-icon btn-icon--danger"
                  title="Delete"
                  @click="openDelete(routine)"
                >
                  🗑️
                </button>
                <button
                  v-if="isAuthenticated"
                  class="btn btn--ghost btn--sm"
                  title="Run Now"
                  :disabled="runNowLoading[routine.id]"
                  @click="runNow(routine)"
                >
                  {{ runNowLoading[routine.id] ? '…' : '▶ Run' }}
                </button>
                <span v-if="runNowSuccess[routine.id]" class="inline-success">Started!</span>
                <span v-else-if="runNowError[routine.id]" class="inline-error">
                  {{ runNowError[routine.id] }}
                </span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ── Panel 2: Currently Executing ──────────────────────────────────── -->
    <div class="panel">
      <h2 class="panel__title">Currently Executing</h2>

      <div v-if="activeError" class="alert alert--error">{{ activeError.message }}</div>

      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>Routine Name</th>
              <th>Triggered By</th>
              <th>Elapsed</th>
            </tr>
          </thead>
          <tbody v-if="loadingActive">
            <tr>
              <td colspan="3" class="state-cell">
                <span class="spinner" aria-label="Loading" />
              </td>
            </tr>
          </tbody>
          <tbody v-else-if="!activeExecutions || activeExecutions.length === 0">
            <tr>
              <td colspan="3" class="state-cell">No routines currently running.</td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr v-for="exec in activeExecutions" :key="exec.id" class="data-row">
              <td>
                <RouterLink :to="`/routines/${exec.routine_id}`" class="row-link">
                  {{ exec.routine_name }}
                </RouterLink>
              </td>
              <td>
                <span class="badge badge--neutral">{{ exec.triggered_by }}</span>
              </td>
              <td class="text-muted">{{ elapsedSeconds(exec.started_at) }}s</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── Panel 3: Recent History ────────────────────────────────────────── -->
    <div class="panel">
      <h2 class="panel__title">Recent History</h2>

      <div v-if="historyError" class="alert alert--error">{{ historyError.message }}</div>

      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>Routine Name</th>
              <th>Status</th>
              <th>Triggered By</th>
              <th>Duration</th>
            </tr>
          </thead>
          <tbody v-if="loadingHistory">
            <tr>
              <td colspan="4" class="state-cell">
                <span class="spinner" aria-label="Loading" />
              </td>
            </tr>
          </tbody>
          <tbody v-else-if="!historyExecutions || historyExecutions.length === 0">
            <tr>
              <td colspan="4" class="state-cell">No execution history.</td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr v-for="exec in historyExecutions" :key="exec.id" class="data-row">
              <td>
                <RouterLink :to="`/routines/${exec.routine_id}`" class="row-link">
                  {{ exec.routine_name }}
                </RouterLink>
              </td>
              <td>
                <span class="badge" :class="statusBadgeClass(exec.status)">{{ exec.status }}</span>
              </td>
              <td>
                <span class="badge badge--neutral">{{ exec.triggered_by }}</span>
              </td>
              <td class="text-muted">
                {{ durationSeconds(exec.started_at, exec.completed_at) !== null ? `${durationSeconds(exec.started_at, exec.completed_at)}s` : '—' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── Create / Edit dialog ───────────────────────────────────────────── -->
    <dialog ref="formDialog" class="modal" @click.self="formDialog?.close()">
      <div class="modal__box">
        <h2 class="modal__title">{{ editingRoutine ? 'Edit Routine' : 'New Routine' }}</h2>
        <form @submit.prevent="submitForm">
          <div class="form-field">
            <label class="form-label" for="routine-name">Name *</label>
            <input
              id="routine-name"
              v-model="form.name"
              class="form-input"
              type="text"
              required
              placeholder="Enter name"
            />
          </div>
          <div class="form-field">
            <label class="form-label" for="routine-desc">Description</label>
            <textarea
              id="routine-desc"
              v-model="form.description"
              class="form-input form-textarea"
              placeholder="Optional description"
              rows="3"
            />
          </div>
          <div class="form-field">
            <label class="form-label" for="routine-schedule-type">Schedule Type</label>
            <select id="routine-schedule-type" v-model="form.schedule_type" class="form-input">
              <option value="manual">manual</option>
              <option value="cron">cron</option>
              <option value="interval">interval</option>
            </select>
          </div>
          <div v-if="form.schedule_type === 'cron'" class="form-field">
            <label class="form-label" for="routine-cron">Cron Expression</label>
            <input
              id="routine-cron"
              v-model="cronExpression"
              class="form-input"
              type="text"
              placeholder="e.g. 0 * * * *"
            />
          </div>
          <div v-if="form.schedule_type === 'interval'" class="form-field">
            <label class="form-label" for="routine-interval">Interval (seconds)</label>
            <input
              id="routine-interval"
              v-model.number="intervalSeconds"
              class="form-input"
              type="number"
              min="1"
              placeholder="e.g. 60"
            />
          </div>
          <div class="form-field form-field--inline">
            <input
              id="routine-active"
              v-model="form.is_active"
              class="form-checkbox"
              type="checkbox"
            />
            <label class="form-label" for="routine-active">Active</label>
          </div>
          <div v-if="formError" class="alert alert--error">{{ formError }}</div>
          <div class="modal__actions">
            <button type="button" class="btn btn--ghost" @click="formDialog?.close()">Cancel</button>
            <button type="submit" class="btn btn--primary" :disabled="submitting">
              {{ submitting ? 'Saving…' : 'Save' }}
            </button>
          </div>
        </form>
      </div>
    </dialog>

    <!-- ── Delete confirmation dialog ────────────────────────────────────── -->
    <dialog ref="deleteDialog" class="modal" @click.self="deleteDialog?.close()">
      <div class="modal__box modal__box--sm">
        <h2 class="modal__title">Delete Routine</h2>
        <p class="modal__body">
          Delete routine <strong>{{ deletingRoutine?.name }}</strong>? This cannot be undone.
        </p>
        <div v-if="deleteError" class="alert alert--error">{{ deleteError }}</div>
        <div class="modal__actions">
          <button class="btn btn--ghost" @click="deleteDialog?.close()">Cancel</button>
          <button class="btn btn--danger" :disabled="deleting" @click="confirmDelete">
            {{ deleting ? 'Deleting…' : 'Delete' }}
          </button>
        </div>
      </div>
    </dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { routinesApi } from '../api/routines'
import { usePolling } from '../composables/usePolling'
import { useAuth } from '../composables/useAuth'
import type { Routine, RoutineCreate, RoutineUpdate } from '../types/routine'

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
const {
  data: historyExecutions,
  loading: loadingHistory,
  error: historyError,
} = usePolling(() => routinesApi.executionHistory(10), 5000)

// ── Helpers ────────────────────────────────────────────────────────────────
function elapsedSeconds(startedAt: string): number {
  return Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000)
}

function durationSeconds(startedAt: string, completedAt: string | null): number | null {
  if (!completedAt) return null
  return Math.floor((new Date(completedAt).getTime() - new Date(startedAt).getTime()) / 1000)
}

function scheduleBadgeClass(scheduleType: Routine['schedule_type']): string {
  if (scheduleType === 'cron') return 'badge--cron'
  if (scheduleType === 'interval') return 'badge--interval'
  return 'badge--manual'
}

function statusBadgeClass(status: 'running' | 'completed' | 'failed'): string {
  if (status === 'completed') return 'badge--success'
  if (status === 'failed') return 'badge--error'
  return 'badge--running'
}

// ── CREATE / EDIT dialog ───────────────────────────────────────────────────
const formDialog = ref<HTMLDialogElement | null>(null)
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
  formDialog.value?.showModal()
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
  formDialog.value?.showModal()
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
    formDialog.value?.close()
  } catch (e) {
    formError.value = e instanceof Error ? e.message : 'Save failed'
  } finally {
    submitting.value = false
  }
}

// ── DELETE dialog ──────────────────────────────────────────────────────────
const deleteDialog = ref<HTMLDialogElement | null>(null)
const deletingRoutine = ref<Routine | null>(null)
const deleteError = ref<string | null>(null)
const deleting = ref(false)

function openDelete(routine: Routine): void {
  deletingRoutine.value = routine
  deleteError.value = null
  deleteDialog.value?.showModal()
}

async function confirmDelete(): Promise<void> {
  if (!deletingRoutine.value) return
  deleting.value = true
  deleteError.value = null
  try {
    await routinesApi.delete(deletingRoutine.value.id)
    routines.value = routines.value.filter((r) => r.id !== deletingRoutine.value!.id)
    deleteDialog.value?.close()
  } catch (e) {
    deleteError.value = e instanceof Error ? e.message : 'Delete failed'
  } finally {
    deleting.value = false
  }
}

// ── RUN NOW ────────────────────────────────────────────────────────────────
const runNowError = ref<Record<number, string>>({})
const runNowLoading = ref<Record<number, boolean>>({})
const runNowSuccess = ref<Record<number, boolean>>({})

async function runNow(routine: Routine): Promise<void> {
  delete runNowError.value[routine.id]
  delete runNowSuccess.value[routine.id]
  runNowLoading.value[routine.id] = true
  try {
    await routinesApi.runNow(routine.id)
    runNowSuccess.value[routine.id] = true
    await refreshActive()
    // Clear success indicator after 3 seconds
    setTimeout(() => {
      delete runNowSuccess.value[routine.id]
    }, 3000)
  } catch (e) {
    runNowError.value[routine.id] = e instanceof Error ? e.message : 'Failed to start'
  } finally {
    delete runNowLoading.value[routine.id]
  }
}

</script>

<style scoped>
.list-view {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.list-view__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.list-view__title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

/* Panel */
.panel {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.panel__title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

/* Table */
.table-wrapper {
  overflow-x: auto;
  border: 1px solid #e2e8f0;
  border-radius: 0.5rem;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.data-table th {
  background: #f8fafc;
  padding: 0.625rem 1rem;
  text-align: left;
  font-weight: 600;
  color: #475569;
  border-bottom: 1px solid #e2e8f0;
  user-select: none;
  white-space: nowrap;
}

.data-table td {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #f1f5f9;
  color: #1e293b;
}

.data-row:last-child td {
  border-bottom: none;
}

.data-row:hover td {
  background: #f8fafc;
}

.col-actions {
  width: 180px;
  text-align: right;
}

.action-cell {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.375rem;
  flex-wrap: wrap;
}

.state-cell {
  text-align: center;
  color: #94a3b8;
  padding: 2.5rem 1rem;
  cursor: default;
}

.text-muted {
  color: #64748b;
}

.row-link {
  color: #3730a3;
  text-decoration: none;
  font-weight: 500;
}

.row-link:hover {
  text-decoration: underline;
}

/* Badge */
.badge {
  display: inline-block;
  padding: 0.2rem 0.55rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: capitalize;
}

.badge--manual {
  background: #f1f5f9;
  color: #475569;
}

.badge--cron {
  background: #ede9fe;
  color: #5b21b6;
}

.badge--interval {
  background: #e0f2fe;
  color: #0369a1;
}

.badge--neutral {
  background: #f1f5f9;
  color: #475569;
}

.badge--running {
  background: #fef9c3;
  color: #92400e;
}

.badge--success {
  background: #dcfce7;
  color: #15803d;
}

.badge--error {
  background: #fef2f2;
  color: #dc2626;
}

/* Active checkmark */
.checkmark {
  color: #16a34a;
  font-weight: 700;
}

/* Inline run-now feedback */
.inline-error {
  font-size: 0.75rem;
  color: #dc2626;
}

.inline-success {
  font-size: 0.75rem;
  color: #16a34a;
  font-weight: 500;
}

/* Spinner */
.spinner {
  display: inline-block;
  width: 1.25rem;
  height: 1.25rem;
  border: 2px solid #e2e8f0;
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition:
    background 0.15s,
    color 0.15s,
    border-color 0.15s;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn--sm {
  padding: 0.25rem 0.625rem;
  font-size: 0.8125rem;
}

.btn--primary {
  background: #4f46e5;
  color: #fff;
}

.btn--primary:hover:not(:disabled) {
  background: #4338ca;
}

.btn--ghost {
  background: transparent;
  color: #475569;
  border-color: #cbd5e1;
}

.btn--ghost:hover:not(:disabled) {
  background: #f1f5f9;
}

.btn--danger {
  background: #dc2626;
  color: #fff;
}

.btn--danger:hover:not(:disabled) {
  background: #b91c1c;
}

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem;
  font-size: 1rem;
  border-radius: 0.25rem;
  line-height: 1;
  transition: background 0.15s;
}

.btn-icon:hover {
  background: #e2e8f0;
}

/* Modal */
.modal {
  padding: 0;
  border: none;
  border-radius: 0.75rem;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.18);
  max-width: 92vw;
}

.modal::backdrop {
  background: rgba(15, 23, 42, 0.45);
}

.modal__box {
  width: 480px;
  padding: 1.75rem;
}

.modal__box--sm {
  width: 400px;
}

.modal__title {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0 0 1.25rem;
  color: #1e293b;
}

.modal__body {
  color: #475569;
  margin: 0 0 1.25rem;
  line-height: 1.5;
}

.modal__actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.5rem;
}

/* Form */
.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  margin-bottom: 1rem;
}

.form-field--inline {
  flex-direction: row;
  align-items: center;
  gap: 0.5rem;
}

.form-label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: #374151;
}

.form-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  color: #1e293b;
  outline: none;
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
  font-family: inherit;
}

.form-input:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15);
}

.form-textarea {
  resize: vertical;
}

.form-checkbox {
  width: 1rem;
  height: 1rem;
  cursor: pointer;
}

/* Alert */
.alert {
  padding: 0.625rem 1rem;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  margin-bottom: 0.75rem;
}

.alert--error {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}
</style>
