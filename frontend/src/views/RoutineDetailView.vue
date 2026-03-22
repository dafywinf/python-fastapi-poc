<template>
  <div class="detail-view">
    <div class="detail-view__back">
      <RouterLink to="/routines" class="back-link">← Back to Routines</RouterLink>
    </div>

    <div v-if="loading" class="state-message">
      <span class="spinner" aria-label="Loading" />
    </div>
    <div v-else-if="pageError" class="alert alert--error">{{ pageError }}</div>

    <template v-else-if="routine">
      <!-- Header -->
      <div class="detail-view__header">
        <h1 class="detail-view__title">{{ routine.name }}</h1>
        <div class="detail-view__actions">
          <button v-if="!editing" class="btn btn--ghost" @click="startEdit">Edit</button>
          <button
            v-if="isAuthenticated"
            class="btn btn--primary btn--sm"
            :disabled="runNowLoading"
            @click="runNow"
          >
            {{ runNowLoading ? '…' : '▶ Run Now' }}
          </button>
        </div>
      </div>

      <div v-if="runNowSuccess" class="alert alert--success">Routine started successfully.</div>
      <div v-else-if="runNowError" class="alert alert--error">{{ runNowError }}</div>

      <!-- Metadata: read-only -->
      <template v-if="!editing">
        <dl class="detail-list">
          <div class="detail-list__row">
            <dt class="detail-list__label">Name</dt>
            <dd class="detail-list__value">{{ routine.name }}</dd>
          </div>
          <div class="detail-list__row">
            <dt class="detail-list__label">Description</dt>
            <dd class="detail-list__value text-muted">{{ routine.description ?? '—' }}</dd>
          </div>
          <div class="detail-list__row">
            <dt class="detail-list__label">Schedule</dt>
            <dd class="detail-list__value">
              <span class="badge" :class="scheduleBadgeClass(routine.schedule_type)">
                {{ routine.schedule_type }}
              </span>
              <span v-if="scheduleConfigSummary" class="text-muted schedule-config-summary">
                {{ scheduleConfigSummary }}
              </span>
            </dd>
          </div>
          <div class="detail-list__row">
            <dt class="detail-list__label">Active</dt>
            <dd class="detail-list__value">
              <span v-if="routine.is_active" class="checkmark">✓ Active</span>
              <span v-else class="text-muted">Inactive</span>
            </dd>
          </div>
        </dl>
      </template>

      <!-- Metadata: edit form -->
      <template v-else>
        <div class="edit-card">
          <h2 class="edit-card__title">Edit Routine</h2>
          <div class="form-field">
            <label class="form-label" for="edit-name">Name *</label>
            <input
              id="edit-name"
              v-model="form.name"
              class="form-input"
              type="text"
              required
              placeholder="Enter name"
            />
          </div>
          <div class="form-field">
            <label class="form-label" for="edit-desc">Description</label>
            <textarea
              id="edit-desc"
              v-model="form.description"
              class="form-input form-textarea"
              placeholder="Optional description"
              rows="3"
            />
          </div>
          <div class="form-field">
            <label class="form-label" for="edit-schedule-type">Schedule Type</label>
            <select id="edit-schedule-type" v-model="form.schedule_type" class="form-input">
              <option value="manual">manual</option>
              <option value="cron">cron</option>
              <option value="interval">interval</option>
            </select>
          </div>
          <div v-if="form.schedule_type === 'cron'" class="form-field">
            <label class="form-label" for="edit-cron">Cron Expression</label>
            <input
              id="edit-cron"
              v-model="editCronExpression"
              class="form-input"
              type="text"
              placeholder="e.g. 0 * * * *"
            />
          </div>
          <div v-if="form.schedule_type === 'interval'" class="form-field">
            <label class="form-label" for="edit-interval">Interval (seconds)</label>
            <input
              id="edit-interval"
              v-model.number="editIntervalSeconds"
              class="form-input"
              type="number"
              min="1"
              placeholder="e.g. 60"
            />
          </div>
          <div class="form-field form-field--inline">
            <input
              id="edit-active"
              v-model="form.is_active"
              class="form-checkbox"
              type="checkbox"
            />
            <label class="form-label" for="edit-active">Active</label>
          </div>
          <div v-if="saveError" class="alert alert--error">{{ saveError }}</div>
          <div class="edit-card__actions">
            <button class="btn btn--ghost" @click="editing = false">Cancel</button>
            <button class="btn btn--primary" :disabled="saving" @click="saveEdit">
              {{ saving ? 'Saving…' : 'Save' }}
            </button>
          </div>
        </div>
      </template>

      <!-- Actions section -->
      <div class="panel">
        <h2 class="panel__title">Actions</h2>

        <div v-if="actionError" class="alert alert--error">{{ actionError }}</div>

        <div v-if="routine.actions.length === 0" class="state-message">
          No actions yet. Add one below.
        </div>

        <div v-else class="actions-list">
          <div
            v-for="action in sortedActions"
            :key="action.id"
            class="action-item"
          >
            <span class="action-item__pos badge badge--neutral">{{ action.position }}</span>
            <span class="badge" :class="actionTypeBadgeClass(action.action_type)">
              {{ action.action_type }}
            </span>
            <span class="action-item__summary text-muted">{{ actionConfigSummary(action) }}</span>
            <div class="action-item__controls">
              <button
                class="btn btn--ghost btn--sm"
                :disabled="action.position === 1"
                title="Move up"
                @click="moveAction(action, 'up')"
              >
                ▲
              </button>
              <button
                class="btn btn--ghost btn--sm"
                :disabled="action.position === routine.actions.length"
                title="Move down"
                @click="moveAction(action, 'down')"
              >
                ▼
              </button>
              <button
                class="btn btn--danger-outline btn--sm"
                title="Delete action"
                @click="removeAction(action)"
              >
                Delete
              </button>
            </div>
          </div>
        </div>

        <!-- Add action form -->
        <div class="add-action-form">
          <h3 class="add-action-form__title">Add Action</h3>
          <div class="add-action-form__row">
            <div class="form-field">
              <label class="form-label" for="action-type">Type</label>
              <select id="action-type" v-model="actionForm.action_type" class="form-input" @change="onActionTypeChange">
                <option value="echo">echo</option>
                <option value="sleep">sleep</option>
              </select>
            </div>
            <div class="form-field">
              <label class="form-label" for="action-config">
                {{ actionForm.action_type === 'echo' ? 'Message' : 'Seconds' }}
              </label>
              <input
                v-if="actionForm.action_type === 'echo'"
                id="action-config"
                v-model="echoMessage"
                class="form-input"
                type="text"
                placeholder="Enter message"
              />
              <input
                v-else
                id="action-config"
                v-model.number="sleepSeconds"
                class="form-input"
                type="number"
                min="1"
                placeholder="e.g. 5"
              />
            </div>
            <button
              class="btn btn--primary add-action-form__btn"
              :disabled="addingAction"
              @click="addAction"
            >
              {{ addingAction ? 'Adding…' : 'Add' }}
            </button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { routinesApi } from '../api/routines'
import { useAuth } from '../composables/useAuth'
import type { Action, ActionCreate, Routine, RoutineUpdate } from '../types/routine'

const props = defineProps<{ id: number }>()
const router = useRouter()
const { isAuthenticated } = useAuth()

// ── Page state ─────────────────────────────────────────────────────────────
const routine = ref<Routine | null>(null)
const loading = ref(true)
const pageError = ref<string | null>(null)

// ── Edit form state ─────────────────────────────────────────────────────────
const editing = ref(false)
const form = ref<RoutineUpdate & { description?: string | null; schedule_type?: 'cron' | 'interval' | 'manual' }>({})
const saving = ref(false)
const saveError = ref<string | null>(null)

// Local schedule config helpers for edit form
const editCronExpression = ref('')
const editIntervalSeconds = ref<number>(60)

// ── Action management ───────────────────────────────────────────────────────
const actionForm = ref<ActionCreate>({ action_type: 'echo', config: { message: '' } })
const echoMessage = ref('')
const sleepSeconds = ref<number>(5)
const addingAction = ref(false)
const actionError = ref<string | null>(null)

// ── Run Now ─────────────────────────────────────────────────────────────────
const runNowError = ref<string | null>(null)
const runNowLoading = ref(false)
const runNowSuccess = ref(false)

// ── Computed ────────────────────────────────────────────────────────────────
const sortedActions = computed<Action[]>(() => {
  if (!routine.value) return []
  return [...routine.value.actions].sort((a, b) => a.position - b.position)
})

const scheduleConfigSummary = computed<string | null>(() => {
  if (!routine.value) return null
  const cfg = routine.value.schedule_config
  if (!cfg) return null
  if ('cron' in cfg) return `(${cfg.cron})`
  if ('seconds' in cfg) return `(every ${cfg.seconds}s)`
  return null
})

// ── Helpers ─────────────────────────────────────────────────────────────────
function scheduleBadgeClass(scheduleType: Routine['schedule_type']): string {
  if (scheduleType === 'cron') return 'badge--cron'
  if (scheduleType === 'interval') return 'badge--interval'
  return 'badge--manual'
}

function actionTypeBadgeClass(actionType: Action['action_type']): string {
  return actionType === 'sleep' ? 'badge--interval' : 'badge--cron'
}

function actionConfigSummary(action: Action): string {
  const cfg = action.config
  if ('message' in cfg) return `echo: ${cfg.message}`
  if ('seconds' in cfg) return `sleep ${cfg.seconds}s`
  return ''
}

function onActionTypeChange(): void {
  if (actionForm.value.action_type === 'echo') {
    actionForm.value.config = { message: '' }
    echoMessage.value = ''
  } else {
    actionForm.value.config = { seconds: 5 }
    sleepSeconds.value = 5
  }
}

// ── Data loading ─────────────────────────────────────────────────────────────
async function load(): Promise<void> {
  loading.value = true
  pageError.value = null
  try {
    routine.value = await routinesApi.get(props.id)
  } catch {
    pageError.value = 'Routine not found'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
})

// ── Edit ─────────────────────────────────────────────────────────────────────
function startEdit(): void {
  if (!routine.value) return
  form.value = {
    name: routine.value.name,
    description: routine.value.description,
    schedule_type: routine.value.schedule_type,
    schedule_config: routine.value.schedule_config,
    is_active: routine.value.is_active,
  }
  // Pre-populate schedule config helpers
  if (routine.value.schedule_type === 'cron' && routine.value.schedule_config && 'cron' in routine.value.schedule_config) {
    editCronExpression.value = routine.value.schedule_config.cron
  } else {
    editCronExpression.value = ''
  }
  if (routine.value.schedule_type === 'interval' && routine.value.schedule_config && 'seconds' in routine.value.schedule_config) {
    editIntervalSeconds.value = routine.value.schedule_config.seconds
  } else {
    editIntervalSeconds.value = 60
  }
  saveError.value = null
  editing.value = true
}

async function saveEdit(): Promise<void> {
  if (!routine.value) return
  saving.value = true
  saveError.value = null
  // Build schedule_config from helpers
  let scheduleConfig: RoutineUpdate['schedule_config'] = null
  if (form.value.schedule_type === 'cron') {
    scheduleConfig = editCronExpression.value ? { cron: editCronExpression.value } : null
  } else if (form.value.schedule_type === 'interval') {
    scheduleConfig = editIntervalSeconds.value > 0 ? { seconds: editIntervalSeconds.value } : null
  }
  try {
    routine.value = await routinesApi.update(routine.value.id, {
      ...form.value,
      schedule_config: scheduleConfig,
    })
    editing.value = false
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : 'Save failed'
  } finally {
    saving.value = false
  }
}

// ── Actions ──────────────────────────────────────────────────────────────────
async function moveAction(action: Action, direction: 'up' | 'down'): Promise<void> {
  if (!routine.value) return
  const newPos = direction === 'up' ? action.position - 1 : action.position + 1
  actionError.value = null
  try {
    await routinesApi.updateAction(action.id, { position: newPos })
    await load()
  } catch (e) {
    actionError.value = e instanceof Error ? e.message : 'Reorder failed'
  }
}

async function removeAction(action: Action): Promise<void> {
  actionError.value = null
  try {
    await routinesApi.deleteAction(action.id)
    if (routine.value) {
      const remaining = routine.value.actions.filter((a) => a.id !== action.id)
      routine.value = {
        ...routine.value,
        actions: remaining.map((a, i) => ({ ...a, position: i + 1 })),
      }
    }
  } catch (e) {
    actionError.value = e instanceof Error ? e.message : 'Delete failed'
  }
}

async function addAction(): Promise<void> {
  if (!routine.value) return
  addingAction.value = true
  actionError.value = null
  // Build config from local helpers
  const config: ActionCreate['config'] =
    actionForm.value.action_type === 'echo'
      ? { message: echoMessage.value }
      : { seconds: sleepSeconds.value }
  try {
    const created = await routinesApi.createAction(routine.value.id, {
      action_type: actionForm.value.action_type,
      config,
    })
    routine.value = { ...routine.value, actions: [...routine.value.actions, created] }
    // Reset form
    actionForm.value = { action_type: 'echo', config: { message: '' } }
    echoMessage.value = ''
    sleepSeconds.value = 5
  } catch (e) {
    actionError.value = e instanceof Error ? e.message : 'Add failed'
  } finally {
    addingAction.value = false
  }
}

// ── Run Now ───────────────────────────────────────────────────────────────────
async function runNow(): Promise<void> {
  if (!routine.value) return
  runNowError.value = null
  runNowSuccess.value = false
  runNowLoading.value = true
  try {
    await routinesApi.runNow(routine.value.id)
    runNowSuccess.value = true
    setTimeout(() => {
      runNowSuccess.value = false
    }, 3000)
  } catch (e) {
    runNowError.value = e instanceof Error ? e.message : 'Failed to start'
  } finally {
    runNowLoading.value = false
  }
}

// Satisfy vue-router usage (router imported for potential future navigation)
void router
</script>

<style scoped>
.detail-view {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  max-width: 760px;
}

.back-link {
  color: #6366f1;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
}

.back-link:hover {
  text-decoration: underline;
}

.detail-view__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.detail-view__title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.detail-view__actions {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

/* Metadata detail list */
.detail-list {
  display: flex;
  flex-direction: column;
  border: 1px solid #e2e8f0;
  border-radius: 0.5rem;
  overflow: hidden;
  margin: 0;
}

.detail-list__row {
  display: grid;
  grid-template-columns: 140px 1fr;
  border-bottom: 1px solid #f1f5f9;
  padding: 0.875rem 1.25rem;
}

.detail-list__row:last-child {
  border-bottom: none;
}

.detail-list__label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.detail-list__value {
  font-size: 0.9375rem;
  color: #1e293b;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.schedule-config-summary {
  font-size: 0.8125rem;
}

/* Edit card */
.edit-card {
  border: 1px solid #e2e8f0;
  border-radius: 0.5rem;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.edit-card__title {
  font-size: 1rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 1rem;
}

.edit-card__actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 0.5rem;
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

/* Actions list */
.actions-list {
  display: flex;
  flex-direction: column;
  border: 1px solid #e2e8f0;
  border-radius: 0.5rem;
  overflow: hidden;
}

.action-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #f1f5f9;
}

.action-item:last-child {
  border-bottom: none;
}

.action-item:hover {
  background: #f8fafc;
}

.action-item__pos {
  min-width: 1.75rem;
  text-align: center;
}

.action-item__summary {
  flex: 1;
  font-size: 0.875rem;
}

.action-item__controls {
  display: flex;
  gap: 0.375rem;
  flex-shrink: 0;
}

/* Add action form */
.add-action-form {
  border: 1px solid #e2e8f0;
  border-radius: 0.5rem;
  padding: 1rem;
}

.add-action-form__title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 0.75rem;
}

.add-action-form__row {
  display: flex;
  align-items: flex-end;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.add-action-form__row .form-field {
  flex: 1;
  min-width: 140px;
}

.add-action-form__btn {
  flex-shrink: 0;
  align-self: flex-end;
  margin-bottom: 1rem;
}

/* State */
.state-message {
  color: #94a3b8;
  padding: 2rem 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.text-muted {
  color: #64748b;
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

/* Active checkmark */
.checkmark {
  color: #16a34a;
  font-weight: 600;
  font-size: 0.9375rem;
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

.btn--danger-outline {
  background: transparent;
  color: #dc2626;
  border-color: #fca5a5;
}

.btn--danger-outline:hover:not(:disabled) {
  background: #fef2f2;
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

.alert--success {
  background: #f0fdf4;
  color: #15803d;
  border: 1px solid #bbf7d0;
}
</style>
