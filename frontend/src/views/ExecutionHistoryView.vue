<template>
  <div class="list-view">
    <div class="list-view__header">
      <h1 class="list-view__title">Execution History</h1>
    </div>

    <!-- Filter row -->
    <div class="filter-row">
      <div class="form-field">
        <label class="form-label" for="filter-routine">Routine</label>
        <select id="filter-routine" v-model="selectedRoutineId" class="form-input">
          <option :value="null">All Routines</option>
          <option v-for="r in routines" :key="r.id" :value="r.id">{{ r.name }}</option>
        </select>
      </div>
      <div class="form-field">
        <label class="form-label" for="filter-limit">Show</label>
        <select id="filter-limit" v-model.number="limit" class="form-input">
          <option :value="10">10</option>
          <option :value="20">20</option>
          <option :value="50">50</option>
        </select>
      </div>
    </div>

    <!-- Error banner -->
    <div v-if="error" class="alert alert--error">{{ error }}</div>

    <!-- Table -->
    <div class="table-wrapper">
      <table class="data-table">
        <thead>
          <tr>
            <th>Routine Name</th>
            <th>Status</th>
            <th>Triggered By</th>
            <th>Started At</th>
            <th>Duration</th>
          </tr>
        </thead>
        <tbody v-if="loading">
          <tr>
            <td colspan="5" class="state-cell">
              <span class="spinner" aria-label="Loading" />
            </td>
          </tr>
        </tbody>
        <tbody v-else-if="executions.length === 0">
          <tr>
            <td colspan="5" class="state-cell">No execution history found.</td>
          </tr>
        </tbody>
        <tbody v-else>
          <tr v-for="exec in executions" :key="exec.id" class="data-row">
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
            <td class="text-muted">{{ formatDate(exec.started_at) }}</td>
            <td class="text-muted">
              {{ durationLabel(exec.started_at, exec.completed_at) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { routinesApi } from '../api/routines'
import { formatDate } from '../utils/date'
import type { Routine, RoutineExecution } from '../types/routine'

// ── State ──────────────────────────────────────────────────────────────────
const routines = ref<Routine[]>([])
const executions = ref<RoutineExecution[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

const selectedRoutineId = ref<number | null>(null)
const limit = ref(20)

// ── Helpers ─────────────────────────────────────────────────────────────────
function statusBadgeClass(status: RoutineExecution['status']): string {
  if (status === 'completed') return 'badge--success'
  if (status === 'failed') return 'badge--error'
  return 'badge--running'
}

function durationLabel(startedAt: string, completedAt: string | null): string {
  if (!completedAt) return '—'
  const ms = new Date(completedAt).getTime() - new Date(startedAt).getTime()
  return `${Math.floor(ms / 1000)}s`
}

// ── Data loading ─────────────────────────────────────────────────────────────
async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    executions.value = await routinesApi.executionHistory(
      limit.value,
      selectedRoutineId.value ?? undefined,
    )
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load history'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  routines.value = await routinesApi.list()
  await load()
})

watch([selectedRoutineId, limit], () => {
  void load()
})
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

/* Filter row */
.filter-row {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
  flex-wrap: wrap;
}

.filter-row .form-field {
  margin-bottom: 0;
  min-width: 160px;
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

/* Form */
.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  margin-bottom: 1rem;
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
