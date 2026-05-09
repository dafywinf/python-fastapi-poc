<script setup lang="ts">
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import RoutineActionCreateForm from '../features/routines/components/RoutineActionCreateForm.vue'
import RoutineActionsList from '../features/routines/components/RoutineActionsList.vue'
import RoutineFormFields from '../features/routines/components/RoutineFormFields.vue'
import { useRoutineFormPage } from '../features/routines/useRoutineFormPage'

const props = defineProps<{ id?: number }>()

const {
  isEditMode,
  isAuthenticated,
  routine,
  loading,
  pageError,
  form,
  saveError,
  saveValidationErrors,
  saving,
  cronExpression,
  intervalSecondsStr,
  actionForm,
  echoMessage,
  sleepSecondsStr,
  actionError,
  actionConfigError,
  localActions,
  deleteDialogOpen,
  deleteError,
  deleting,
  actionConfigSummary,
  onActionTypeChange,
  save,
  cancel,
  reorderActions,
  removeAction,
  addAction,
  openDeleteDialog,
  confirmDelete,
} = useRoutineFormPage(props.id)
</script>

<template>
  <div class="flex flex-col gap-5 max-w-3xl">
    <!-- Loading / error (edit mode only) -->
    <div v-if="loading" data-testid="routine-form-loading" class="text-app-muted py-8 flex items-center gap-2">
      <span
        class="inline-block w-5 h-5 border-2 border-app-border border-t-indigo-500 rounded-full animate-spin"
        aria-label="Loading"
      />
    </div>
    <div
      v-else-if="pageError"
      data-testid="routine-form-page-error"
      class="px-4 py-2.5 rounded-md text-sm bg-red-50 text-red-600 border border-red-200"
    >
      {{ pageError }}
    </div>

    <template v-else>
      <!-- Header -->
      <div class="flex items-center justify-between">
        <h1 class="text-2xl font-semibold text-app-text m-0">
          {{ isEditMode ? routine?.name : 'New Routine' }}
        </h1>
        <div v-if="isAuthenticated" class="flex items-center gap-2 shrink-0">
          <Button label="Cancel" severity="secondary" @click="cancel" />
          <Button
            :label="saving ? 'Saving…' : (isEditMode ? 'Save' : 'Create')"
            :disabled="saving"
            @click="save"
          />
          <Button
            v-if="isEditMode"
            label="Delete"
            severity="danger"
            @click="openDeleteDialog"
          />
        </div>
      </div>

      <!-- Routine form -->
      <div class="border border-app-border rounded-lg p-5 flex flex-col gap-4">
        <RoutineFormFields
          v-model:name="form.name"
          v-model:description="form.description"
          v-model:schedule-type="form.schedule_type"
          v-model:cron-expression="cronExpression"
          v-model:interval-seconds="intervalSecondsStr"
          v-model:is-active="form.is_active"
          id-prefix="routine-form"
          :errors="saveValidationErrors"
        />
        <div
          v-if="saveError"
          class="px-4 py-2.5 rounded-md text-sm bg-red-50 text-red-600 border border-red-200"
        >
          {{ saveError }}
        </div>
      </div>

      <!-- Actions section -->
      <div class="flex flex-col gap-3">
        <h2 class="text-lg font-semibold text-app-text m-0">Actions</h2>

        <div
          v-if="actionError"
          class="px-4 py-2.5 rounded-md text-sm bg-red-50 text-red-600 border border-red-200"
        >
          {{ actionError }}
        </div>

        <div v-if="localActions.length === 0" class="text-app-muted py-4">
          No actions yet. Add one below.
        </div>

        <RoutineActionsList
          v-else
          :actions="localActions"
          :editable="true"
          :summarize-config="actionConfigSummary"
          @reorder="reorderActions"
          @remove="removeAction"
        />

        <RoutineActionCreateForm
          v-model:action-type="actionForm.action_type"
          v-model:echo-message="echoMessage"
          v-model:sleep-seconds="sleepSecondsStr"
          id-prefix="routine-action"
          :config-error="actionConfigError"
          :submitting="false"
          @type-change="onActionTypeChange"
          @submit="addAction"
        />
      </div>

      <!-- Repeated save/cancel at bottom for long pages -->
      <div v-if="isAuthenticated" class="flex justify-end gap-3 pt-2">
        <Button label="Cancel" severity="secondary" @click="cancel" />
        <Button
          :label="saving ? 'Saving…' : (isEditMode ? 'Save' : 'Create')"
          :disabled="saving"
          @click="save"
        />
      </div>
    </template>

    <!-- Delete Confirmation Dialog (edit mode only) -->
    <Dialog
      v-if="isEditMode"
      :visible="deleteDialogOpen"
      :modal="true"
      header="Delete Routine"
      @update:visible="deleteDialogOpen = false"
    >
      <p class="text-sm text-app-muted">
        Delete routine <strong>{{ routine?.name }}</strong>? This cannot be undone.
      </p>
      <div
        v-if="deleteError"
        class="px-4 py-2.5 rounded-md text-sm bg-red-50 text-red-600 border border-red-200"
      >
        {{ deleteError }}
      </div>
      <template #footer>
        <Button label="Cancel" severity="secondary" @click="deleteDialogOpen = false" />
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
