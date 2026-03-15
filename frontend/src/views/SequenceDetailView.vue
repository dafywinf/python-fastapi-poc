<template>
  <div class="detail-view">
    <div class="detail-view__back">
      <RouterLink to="/sequences" class="back-link">← Back to Sequences</RouterLink>
    </div>

    <div v-if="loading" class="state-message">Loading…</div>
    <div v-else-if="error" class="alert alert--error">{{ error }}</div>

    <template v-else-if="sequence">
      <div class="detail-view__header">
        <h1 class="detail-view__title">{{ sequence.name }}</h1>
        <div class="detail-view__actions">
          <button class="btn btn--ghost" @click="openEdit">Edit</button>
          <button class="btn btn--danger-outline" @click="openDelete">Delete</button>
        </div>
      </div>

      <dl class="detail-list">
        <div class="detail-list__row">
          <dt class="detail-list__label">ID</dt>
          <dd class="detail-list__value">{{ sequence.id }}</dd>
        </div>
        <div class="detail-list__row">
          <dt class="detail-list__label">Name</dt>
          <dd class="detail-list__value">{{ sequence.name }}</dd>
        </div>
        <div class="detail-list__row">
          <dt class="detail-list__label">Description</dt>
          <dd class="detail-list__value text-muted">
            {{ sequence.description ?? 'No description provided.' }}
          </dd>
        </div>
        <div class="detail-list__row">
          <dt class="detail-list__label">Created</dt>
          <dd class="detail-list__value text-muted">{{ formatDate(sequence.created_at) }}</dd>
        </div>
      </dl>
    </template>

    <!-- Edit dialog -->
    <dialog ref="formDialog" class="modal" @click.self="closeForm">
      <div class="modal__box">
        <h2 class="modal__title">Edit Sequence</h2>
        <form @submit.prevent="submitEdit">
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
          Are you sure you want to delete <strong>{{ sequence?.name }}</strong>? This cannot be undone.
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { sequencesApi } from '../api/sequences'
import type { Sequence } from '../types/sequence'

const props = defineProps<{ id: number }>()
const router = useRouter()

// ── State ──────────────────────────────────────────────────────────────────
const sequence = ref<Sequence | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

// ── Form ───────────────────────────────────────────────────────────────────
const formDialog = ref<HTMLDialogElement | null>(null)
const form = ref({ name: '', description: '' })
const formError = ref<string | null>(null)
const submitting = ref(false)

// ── Delete ─────────────────────────────────────────────────────────────────
const deleteDialog = ref<HTMLDialogElement | null>(null)
const deleteError = ref<string | null>(null)

// ── Helpers ────────────────────────────────────────────────────────────────
function formatDate(iso: string): string {
  return new Date(iso).toLocaleString()
}

// ── Load ───────────────────────────────────────────────────────────────────
async function loadSequence() {
  loading.value = true
  error.value = null
  try {
    sequence.value = await sequencesApi.get(props.id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load sequence'
  } finally {
    loading.value = false
  }
}

onMounted(loadSequence)

// ── Edit ───────────────────────────────────────────────────────────────────
function openEdit() {
  if (!sequence.value) return
  form.value = { name: sequence.value.name, description: sequence.value.description ?? '' }
  formError.value = null
  formDialog.value?.showModal()
}

function closeForm() {
  formDialog.value?.close()
}

async function submitEdit() {
  submitting.value = true
  formError.value = null
  try {
    const payload = {
      name: form.value.name.trim(),
      description: form.value.description.trim() || null,
    }
    sequence.value = await sequencesApi.update(props.id, payload)
    closeForm()
  } catch (e) {
    formError.value = e instanceof Error ? e.message : 'An error occurred'
  } finally {
    submitting.value = false
  }
}

// ── Delete ─────────────────────────────────────────────────────────────────
function openDelete() {
  deleteError.value = null
  deleteDialog.value?.showModal()
}

function closeDelete() {
  deleteDialog.value?.close()
}

async function confirmDelete() {
  submitting.value = true
  deleteError.value = null
  try {
    await sequencesApi.delete(props.id)
    router.push('/sequences')
  } catch (e) {
    deleteError.value = e instanceof Error ? e.message : 'An error occurred'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.detail-view {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  max-width: 640px;
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
}

.text-muted {
  color: #64748b;
}

.state-message {
  color: #94a3b8;
  padding: 2rem 0;
}

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
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

.btn--danger-outline {
  background: transparent;
  color: #dc2626;
  border-color: #fca5a5;
}

.btn--danger-outline:hover:not(:disabled) {
  background: #fef2f2;
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
