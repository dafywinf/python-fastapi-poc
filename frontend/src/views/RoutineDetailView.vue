<template>
  <div class="flex flex-col gap-5 max-w-3xl">
    <!-- Back link -->
    <button
      class="text-sm text-indigo-600 hover:underline font-medium text-left bg-transparent border-none p-0 cursor-pointer"
      @click="router.back()"
    >
      ← Back
    </button>

    <div v-if="loading" class="text-slate-400 py-8 flex items-center gap-2">
      <span
        class="inline-block w-5 h-5 border-2 border-slate-200 border-t-indigo-500 rounded-full animate-spin"
        aria-label="Loading"
      />
    </div>
    <div
      v-else-if="pageError"
      class="px-4 py-2.5 rounded-md text-sm bg-red-50 text-red-600 border border-red-200"
    >
      {{ pageError }}
    </div>

    <template v-else-if="routine">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <h1 class="text-2xl font-semibold text-slate-900 m-0">
          {{ routine.name }}
        </h1>
        <div class="flex items-center gap-2 shrink-0">
          <Button
            v-if="isAuthenticated && !editing"
            label="Edit"
            severity="secondary"
            @click="startEdit"
          />
          <Button
            v-if="isAuthenticated"
            :label="runNowLoading ? '…' : '▶ Run Now'"
            :disabled="runNowLoading"
            @click="runNow"
          />
        </div>
      </div>

      <!-- Metadata: read-only -->
      <template v-if="!editing">
        <RoutineMetadataView :items="metadataItems" />
      </template>

      <!-- Metadata: edit form -->
      <template v-else>
        <div class="border border-slate-200 rounded-lg p-5 flex flex-col gap-4">
          <h2 class="text-base font-semibold text-slate-900 m-0">
            Edit Routine
          </h2>
          <RoutineFormFields
            v-model:name="form.name"
            v-model:description="form.description"
            v-model:schedule-type="form.schedule_type"
            v-model:cron-expression="editCronExpression"
            v-model:interval-seconds="editIntervalSecondsStr"
            v-model:is-active="form.is_active"
            id-prefix="routine-detail"
            :errors="saveValidationErrors"
          />
          <div
            v-if="saveError"
            class="px-4 py-2.5 rounded-md text-sm bg-red-50 text-red-600 border border-red-200"
          >
            {{ saveError }}
          </div>
          <div class="flex justify-end gap-3 mt-1">
            <Button
              label="Cancel"
              severity="secondary"
              @click="editing = false"
            />
            <Button
              :label="saving ? 'Saving…' : 'Save'"
              :disabled="saving"
              @click="saveEdit"
            />
          </div>
        </div>
      </template>

      <!-- Actions section -->
      <div class="flex flex-col gap-3">
        <h2 class="text-lg font-semibold text-slate-900 m-0">Actions</h2>

        <div
          v-if="actionError"
          class="px-4 py-2.5 rounded-md text-sm bg-red-50 text-red-600 border border-red-200"
        >
          {{ actionError }}
        </div>

        <div v-if="routine.actions.length === 0" class="text-slate-400 py-4">
          No actions yet. Add one below.
        </div>

        <RoutineActionsList
          v-else
          :actions="sortedActions"
          :editable="isAuthenticated"
          :summarize-config="actionConfigSummary"
          @move="moveAction"
          @remove="removeAction"
        />

        <!-- Add action form -->
        <RoutineActionCreateForm
          v-if="isAuthenticated"
          v-model:action-type="actionForm.action_type"
          v-model:echo-message="echoMessage"
          v-model:sleep-seconds="sleepSecondsStr"
          id-prefix="routine-action"
          :config-error="actionConfigError"
          :submitting="addingAction"
          @type-change="onActionTypeChange"
          @submit="addAction"
        />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import RoutineActionCreateForm from '../features/routines/components/RoutineActionCreateForm.vue'
import RoutineActionsList from '../features/routines/components/RoutineActionsList.vue'
import RoutineFormFields from '../features/routines/components/RoutineFormFields.vue'
import RoutineMetadataView from '../features/routines/components/RoutineMetadataView.vue'
import { useRoutineDetailPage } from '../features/routines/useRoutineDetailPage'

const props = defineProps<{ id: number }>()
const router = useRouter()
const {
  isAuthenticated,
  routine,
  loading,
  pageError,
  editing,
  form,
  saveError,
  saveValidationErrors,
  saving,
  editCronExpression,
  editIntervalSecondsStr,
  actionForm,
  echoMessage,
  sleepSecondsStr,
  addingAction,
  actionError,
  actionConfigError,
  runNowLoading,
  sortedActions,
  metadataItems,
  actionConfigSummary,
  onActionTypeChange,
  startEdit,
  saveEdit,
  moveAction,
  removeAction,
  addAction,
  runNow,
} = useRoutineDetailPage(props.id)
</script>
