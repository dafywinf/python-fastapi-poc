<template>
  <div class="flex flex-col gap-5">
    <!-- ── Header ─────────────────────────────────────────────────────────── -->
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-slate-900 m-0">Routines</h1>
      <Button
        v-if="isAuthenticated"
        label="+ New Routine"
        @click="openCreate"
      />
    </div>

    <div
      v-if="routinesError"
      class="px-4 py-2.5 rounded-md text-sm bg-red-50 text-red-600 border border-red-200"
    >
      {{ routinesError }}
    </div>

    <!-- ── Panel 1: Configured Routines ───────────────────────────────────── -->
    <div class="border border-slate-200 rounded-lg overflow-hidden">
      <DataTable :value="routines" :loading="loadingRoutines">
        <Column field="name" header="Name">
          <template #body="{ data }">
            <RouterLink
              :to="`/routines/${data.id}`"
              class="text-indigo-700 font-medium no-underline hover:underline"
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
            />
          </template>
        </Column>
        <Column field="is_active" header="Active">
          <template #body="{ data }">
            <span
              :class="
                data.is_active
                  ? 'text-green-600 font-semibold'
                  : 'text-slate-400'
              "
            >
              {{ data.is_active ? '✓' : '—' }}
            </span>
          </template>
        </Column>
        <Column header="Actions">
          <template #body="{ data }">
            <div v-if="isAuthenticated" class="flex gap-1.5 justify-end">
              <Button
                label="Edit"
                size="small"
                severity="secondary"
                @click="openEdit(data)"
              />
              <Button
                label="Delete"
                size="small"
                severity="danger"
                @click="openDelete(data)"
              />
              <Button
                label="▶ Run"
                size="small"
                :disabled="!!runNowLoading[data.id]"
                @click="runNow(data)"
              />
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
          <h2 class="text-sm font-semibold text-slate-900 m-0">
            Currently Executing
          </h2>
        </div>
        <div v-if="activeError" class="px-4 py-2 text-sm text-red-600">
          {{ activeError }}
        </div>
        <div
          v-if="loadingActive"
          class="px-4 py-6 text-center text-sm text-slate-400"
        >
          Loading…
        </div>
        <div
          v-else-if="!activeExecutions || !activeExecutions.length"
          class="px-4 py-6 text-center text-sm text-slate-400"
        >
          None running
        </div>
        <DataTable
          v-else
          :value="activeExecutions"
          size="small"
          striped-rows
          class="text-sm"
        >
          <Column field="routine_name" header="Routine">
            <template #body="{ data }">
              <RouterLink
                :to="`/routines/${data.routine_id}`"
                class="text-indigo-700 font-medium no-underline hover:underline"
              >
                {{ data.routine_name }}
              </RouterLink>
            </template>
          </Column>
          <Column field="status" header="Status">
            <template #body>
              <Tag value="running" severity="warn" />
            </template>
          </Column>
          <Column field="triggered_by" header="Trigger">
            <template #body="{ data }">
              <span class="text-slate-400 text-xs">
                {{ data.triggered_by }}
              </span>
            </template>
          </Column>
          <Column header="Elapsed">
            <template #body="{ data }">
              <span class="text-slate-400 text-xs">
                {{ elapsedSeconds(data.started_at) }}s
              </span>
            </template>
          </Column>
        </DataTable>
      </div>

      <!-- Recent History -->
      <div class="border border-slate-200 rounded-lg overflow-hidden">
        <div
          class="px-4 py-3 border-b border-slate-200 flex items-center justify-between"
        >
          <h2 class="text-sm font-semibold text-slate-900 m-0">
            Recent History
          </h2>
          <div class="flex items-center gap-3">
            <Select
              v-model="historyLimit"
              :options="historyLimitOptions"
              option-label="label"
              option-value="value"
              class="w-20 text-xs"
            />
            <RouterLink
              to="/history"
              class="text-xs text-indigo-600 hover:underline font-medium no-underline"
              >View all →</RouterLink
            >
          </div>
        </div>
        <div v-if="historyError" class="px-4 py-2 text-sm text-red-600">
          {{ historyError }}
        </div>
        <div
          v-if="loadingHistory"
          class="px-4 py-6 text-center text-sm text-slate-400"
        >
          Loading…
        </div>
        <div
          v-else-if="!historyExecutions || !historyExecutions.length"
          class="px-4 py-6 text-center text-sm text-slate-400"
        >
          No history
        </div>
        <DataTable
          v-else
          :value="historyExecutions"
          size="small"
          striped-rows
          class="text-sm"
        >
          <Column field="routine_name" header="Routine">
            <template #body="{ data }">
              <RouterLink
                :to="`/routines/${data.routine_id}`"
                class="text-indigo-700 font-medium no-underline hover:underline"
              >
                {{ data.routine_name }}
              </RouterLink>
            </template>
          </Column>
          <Column field="status" header="Status">
            <template #body="{ data }">
              <Tag
                :value="data.status"
                :severity="
                  data.status === 'completed'
                    ? 'success'
                    : data.status === 'failed'
                      ? 'danger'
                      : 'warn'
                "
              />
            </template>
          </Column>
          <Column field="triggered_by" header="Trigger">
            <template #body="{ data }">
              <span class="text-slate-400 text-xs">
                {{ data.triggered_by }}
              </span>
            </template>
          </Column>
          <Column header="Duration">
            <template #body="{ data }">
              <span class="text-slate-400 text-xs">
                {{
                  durationSeconds(data.started_at, data.completed_at) !== null
                    ? `${durationSeconds(data.started_at, data.completed_at)}s`
                    : '—'
                }}
              </span>
            </template>
          </Column>
        </DataTable>
      </div>
    </div>

    <!-- ── Create / Edit Dialog ───────────────────────────────────────────── -->
    <Dialog
      :visible="formDialogOpen"
      :modal="true"
      :header="editingRoutine ? 'Edit Routine' : 'New Routine'"
      @update:visible="formDialogOpen = false"
    >
      <form class="flex flex-col gap-4" @submit.prevent="submitForm">
        <RoutineFormFields
          v-model:name="form.name"
          v-model:description="form.description"
          v-model:schedule-type="form.schedule_type"
          v-model:cron-expression="cronExpression"
          v-model:interval-seconds="intervalSecondsStr"
          v-model:is-active="form.is_active"
          id-prefix="routine-dialog"
          :errors="formValidationErrors"
        />
        <div
          v-if="formError"
          class="px-4 py-2.5 rounded-md text-sm bg-red-50 text-red-600 border border-red-200"
        >
          {{ formError }}
        </div>
      </form>
      <template #footer>
        <Button
          label="Cancel"
          severity="secondary"
          @click="formDialogOpen = false"
        />
        <Button
          :label="submitting ? 'Saving…' : editingRoutine ? 'Update' : 'Create'"
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
        Delete routine <strong>{{ deletingRoutine?.name }}</strong
        >? This cannot be undone.
      </p>
      <div
        v-if="deleteError"
        class="px-4 py-2.5 rounded-md text-sm bg-red-50 text-red-600 border border-red-200"
      >
        {{ deleteError }}
      </div>
      <template #footer>
        <Button
          label="Cancel"
          severity="secondary"
          @click="deleteDialogOpen = false"
        />
        <Button
          label="Delete"
          severity="danger"
          :disabled="deleting"
          @click="confirmDelete"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import RoutineFormFields from '../features/routines/components/RoutineFormFields.vue'
import { useRoutinesPage } from '../features/routines/useRoutinesPage'

const historyLimitOptions = [
  { label: '5', value: 5 },
  { label: '10', value: 10 },
  { label: '20', value: 20 },
]

const {
  isAuthenticated,
  routines,
  loadingRoutines,
  routinesError,
  activeExecutions,
  loadingActive,
  activeError,
  historyLimit,
  historyExecutions,
  loadingHistory,
  historyError,
  elapsedSeconds,
  durationSeconds,
  formDialogOpen,
  editingRoutine,
  form,
  formError,
  formValidationErrors,
  submitting,
  cronExpression,
  intervalSecondsStr,
  openCreate,
  openEdit,
  submitForm,
  deleteDialogOpen,
  deletingRoutine,
  deleteError,
  deleting,
  openDelete,
  confirmDelete,
  runNowLoading,
  runNow,
} = useRoutinesPage()
</script>
