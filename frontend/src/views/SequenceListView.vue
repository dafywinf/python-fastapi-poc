<template>
  <div class="list-view">
    <div class="list-view__header">
      <h1 class="list-view__title">Sequences</h1>
      <button v-if="isAuthenticated" class="btn btn--primary" @click="openCreate">+ New Sequence</button>
    </div>

    <!-- Error banner -->
    <div v-if="error" class="alert alert--error">{{ error }}</div>

    <!-- Table -->
    <div class="table-wrapper">
      <table class="data-table">
        <thead>
          <tr>
            <th class="col-id" @click="sortBy('id')">
              ID <SortIcon :field="'id'" :active="sort.field" :dir="sort.dir" />
            </th>
            <th @click="sortBy('name')">
              Name <SortIcon :field="'name'" :active="sort.field" :dir="sort.dir" />
            </th>
            <th class="col-desc">Description</th>
            <th @click="sortBy('created_at')">
              Created <SortIcon :field="'created_at'" :active="sort.field" :dir="sort.dir" />
            </th>
            <th class="col-actions">Actions</th>
          </tr>
        </thead>
        <tbody v-if="loading">
          <tr>
            <td colspan="5" class="state-cell">Loading…</td>
          </tr>
        </tbody>
        <tbody v-else-if="sortedRows.length === 0">
          <tr>
            <td colspan="5" class="state-cell">No sequences found. Create one to get started.</td>
          </tr>
        </tbody>
        <tbody v-else>
          <tr v-for="seq in sortedRows" :key="seq.id" class="data-row">
            <td class="col-id">{{ seq.id }}</td>
            <td>
              <RouterLink :to="`/sequences/${seq.id}`" class="row-link">{{ seq.name }}</RouterLink>
            </td>
            <td class="col-desc text-muted">{{ seq.description ?? '—' }}</td>
            <td class="text-muted">{{ formatDate(seq.created_at) }}</td>
            <td class="col-actions">
              <button v-if="isAuthenticated" class="btn-icon" title="Edit" @click="openEdit(seq)">✏️</button>
              <button v-if="isAuthenticated" class="btn-icon btn-icon--danger" title="Delete" @click="openDelete(seq)">🗑️</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create / Edit dialog -->
    <dialog ref="formDialog" class="modal" @click.self="closeForm">
      <div class="modal__box">
        <h2 class="modal__title">{{ editing ? 'Edit Sequence' : 'New Sequence' }}</h2>
        <form @submit.prevent="submitForm">
          <div class="form-field">
            <label class="form-label" for="seq-name">Name *</label>
            <input
              id="seq-name"
              v-model="form.name"
              class="form-input"
              type="text"
              required
              placeholder="Enter name"
            />
          </div>
          <div class="form-field">
            <label class="form-label" for="seq-desc">Description</label>
            <textarea
              id="seq-desc"
              v-model="form.description"
              class="form-input form-textarea"
              placeholder="Optional description"
              rows="3"
            />
          </div>
          <div v-if="formError" class="alert alert--error">{{ formError }}</div>
          <div class="modal__actions">
            <button type="button" class="btn btn--ghost" @click="closeForm">Cancel</button>
            <button type="submit" class="btn btn--primary" :disabled="submitting">
              {{ submitting ? 'Saving…' : 'Save' }}
            </button>
          </div>
        </form>
      </div>
    </dialog>

    <!-- Delete confirmation dialog -->
    <dialog ref="deleteDialog" class="modal" @click.self="closeDelete">
      <div class="modal__box modal__box--sm">
        <h2 class="modal__title">Delete Sequence</h2>
        <p class="modal__body">
          Are you sure you want to delete <strong>{{ deleting?.name }}</strong>? This cannot be undone.
        </p>
        <div v-if="deleteError" class="alert alert--error">{{ deleteError }}</div>
        <div class="modal__actions">
          <button class="btn btn--ghost" @click="closeDelete">Cancel</button>
          <button class="btn btn--danger" :disabled="submitting" @click="confirmDelete">
            {{ submitting ? 'Deleting…' : 'Delete' }}
          </button>
        </div>
      </div>
    </dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { sequencesApi } from '../api/sequences'
import type { Sequence } from '../types/sequence'
import { formatDate } from '../utils/date'
import { useAuth } from '../composables/useAuth'
const { isAuthenticated } = useAuth()

// ── Sort icon sub-component ────────────────────────────────────────────────
const SortIcon = {
  props: ['field', 'active', 'dir'],
  setup(props: { field: string; active: keyof Sequence; dir: 'asc' | 'desc' }) {
    return () =>
      props.field === props.active
        ? h('span', { class: 'sort-icon' }, props.dir === 'asc' ? '▲' : '▼')
        : null
  },
}

// ── State ──────────────────────────────────────────────────────────────────
const rows = ref<Sequence[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

const sort = ref<{ field: keyof Sequence; dir: 'asc' | 'desc' }>({ field: 'id', dir: 'asc' })

// ── Form dialog ────────────────────────────────────────────────────────────
const formDialog = ref<HTMLDialogElement | null>(null)
const editing = ref<Sequence | null>(null)
const form = ref({ name: '', description: '' })
const formError = ref<string | null>(null)
const submitting = ref(false)

// ── Delete dialog ──────────────────────────────────────────────────────────
const deleteDialog = ref<HTMLDialogElement | null>(null)
const deleting = ref<Sequence | null>(null)
const deleteError = ref<string | null>(null)

// ── Computed sorted rows ───────────────────────────────────────────────────
const sortedRows = computed(() => {
  const field = sort.value.field
  const dir = sort.value.dir === 'asc' ? 1 : -1
  return [...rows.value].sort((a, b) => {
    const av = a[field] ?? ''
    const bv = b[field] ?? ''
    return av < bv ? -dir : av > bv ? dir : 0
  })
})

// ── Helpers ────────────────────────────────────────────────────────────────
function sortBy(field: keyof Sequence) {
  if (sort.value.field === field) {
    sort.value.dir = sort.value.dir === 'asc' ? 'desc' : 'asc'
  } else {
    sort.value = { field, dir: 'asc' }
  }
}

// ── Data loading ───────────────────────────────────────────────────────────
async function loadSequences() {
  loading.value = true
  error.value = null
  try {
    rows.value = [...(await sequencesApi.list())]
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load sequences'
  } finally {
    loading.value = false
  }
}

onMounted(loadSequences)

// ── Create ─────────────────────────────────────────────────────────────────
function openCreate() {
  editing.value = null
  form.value = { name: '', description: '' }
  formError.value = null
  formDialog.value?.showModal()
}

// ── Edit ───────────────────────────────────────────────────────────────────
function openEdit(seq: Sequence) {
  editing.value = seq
  form.value = { name: seq.name, description: seq.description ?? '' }
  formError.value = null
  formDialog.value?.showModal()
}

function closeForm() {
  formDialog.value?.close()
}

async function submitForm() {
  submitting.value = true
  formError.value = null
  try {
    const payload = {
      name: form.value.name.trim(),
      description: form.value.description.trim() || null,
    }
    if (editing.value) {
      const updated = await sequencesApi.update(editing.value.id, payload)
      const idx = rows.value.findIndex((r) => r.id === updated.id)
      if (idx !== -1) rows.value[idx] = updated
    } else {
      const created = await sequencesApi.create(payload)
      rows.value.unshift(created)
    }
    closeForm()
  } catch (e) {
    formError.value = e instanceof Error ? e.message : 'An error occurred'
  } finally {
    submitting.value = false
  }
}

// ── Delete ─────────────────────────────────────────────────────────────────
function openDelete(seq: Sequence) {
  deleting.value = seq
  deleteError.value = null
  deleteDialog.value?.showModal()
}

function closeDelete() {
  deleteDialog.value?.close()
}

async function confirmDelete() {
  if (!deleting.value) return
  submitting.value = true
  deleteError.value = null
  try {
    await sequencesApi.delete(deleting.value.id)
    rows.value = rows.value.filter((r) => r.id !== deleting.value!.id)
    closeDelete()
  } catch (e) {
    deleteError.value = e instanceof Error ? e.message : 'An error occurred'
  } finally {
    submitting.value = false
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
  cursor: pointer;
  white-space: nowrap;
}

.data-table th:hover {
  background: #f1f5f9;
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

.col-id {
  width: 60px;
}

.col-desc {
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.col-actions {
  width: 80px;
  text-align: right;
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

.sort-icon {
  font-size: 0.65rem;
  margin-left: 0.25rem;
  color: #6366f1;
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
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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
  transition: border-color 0.15s, box-shadow 0.15s;
  font-family: inherit;
}

.form-input:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15);
}

.form-textarea {
  resize: vertical;
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
