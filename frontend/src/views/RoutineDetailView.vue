<script setup lang="ts">
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import RoutineActionsList from '../features/routines/components/RoutineActionsList.vue'
import RoutineMetadataView from '../features/routines/components/RoutineMetadataView.vue'
import { useRoutineViewPage } from '../features/routines/useRoutineViewPage'

const props = defineProps<{ id: number }>()
const router = useRouter()
const {
  isAuthenticated,
  routine,
  loading,
  pageError,
  runNowLoading,
  deleteDialogOpen,
  deleteError,
  deleting,
  viewActions,
  metadataItems,
  actionConfigSummary,
  openDeleteDialog,
  confirmDelete,
  runNow,
  goToEdit,
} = useRoutineViewPage(props.id)
</script>

<template>
  <div class="flex flex-col gap-5 max-w-3xl">
    <!-- Back link -->
    <button
      class="text-sm text-indigo-600 hover:underline font-medium text-left bg-transparent border-none p-0 cursor-pointer"
      @click="router.back()"
    >
      ← Back
    </button>

    <div v-if="loading" data-testid="routine-detail-loading" class="text-app-muted py-8 flex items-center gap-2">
      <span
        class="inline-block w-5 h-5 border-2 border-app-border border-t-indigo-500 rounded-full animate-spin"
        aria-label="Loading"
      />
    </div>
    <div
      v-else-if="pageError"
      data-testid="routine-detail-error"
      class="px-4 py-2.5 rounded-md text-sm bg-red-50 text-red-600 border border-red-200"
    >
      {{ pageError }}
    </div>

    <template v-else-if="routine">
      <!-- Header -->
      <div data-testid="routine-detail-header" class="flex items-center justify-between">
        <h1 class="text-2xl font-semibold text-app-text m-0">
          {{ routine.name }}
        </h1>
        <div v-if="isAuthenticated" class="flex items-center gap-2 shrink-0">
          <Button
            :label="runNowLoading ? '…' : '▶ Run Now'"
            :disabled="runNowLoading"
            @click="runNow"
          />
          <Button
            label="Edit"
            severity="secondary"
            @click="goToEdit"
          />
          <Button
            label="Delete"
            severity="danger"
            @click="openDeleteDialog"
          />
        </div>
      </div>

      <!-- Metadata (read-only) -->
      <RoutineMetadataView :items="metadataItems" />

      <!-- Actions (read-only) -->
      <div class="flex flex-col gap-3">
        <h2 class="text-lg font-semibold text-app-text m-0">Actions</h2>
        <div v-if="viewActions.length === 0" class="text-app-muted py-4">
          No actions configured.
        </div>
        <RoutineActionsList
          v-else
          :actions="viewActions"
          :editable="false"
          :summarize-config="actionConfigSummary"
          @reorder="() => {}"
          @remove="() => {}"
        />
      </div>
    </template>

    <!-- Delete Confirmation Dialog -->
    <Dialog
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
