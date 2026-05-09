<script setup lang="ts">
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import RoutineTable from '../features/routines/components/RoutineTable.vue'
import { useRoutinesPage } from '../features/routines/useRoutinesPage'

const router = useRouter()
const {
  isAuthenticated,
  routines,
  routinesTotal,
  loadingRoutines,
  routinesError,
  searchQuery,
  limit,
  page,
  goToEdit,
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

<template>
  <div class="flex flex-col gap-4">
    <!-- ── Header ─────────────────────────────────────────────────────────── -->
    <div class="flex items-end justify-between mb-1 gap-3 flex-wrap">
      <div>
        <div class="text-[11px] font-light uppercase tracking-[0.18em] text-gray-400 mb-0.5">Management</div>
        <h1 class="text-[26px] font-bold tracking-tight text-app-text m-0 leading-tight">Routines</h1>
      </div>
      <div class="flex items-end gap-3 flex-wrap">
        <div class="flex flex-col gap-1">
          <label class="text-xs font-medium text-app-muted">Search</label>
          <InputText
            v-model="searchQuery"
            placeholder="Filter by name…"
            class="w-48"
          />
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-xs font-medium text-app-muted">Show</label>
          <Select
            v-model="limit"
            :options="[
              { label: '10', value: 10 },
              { label: '25', value: 25 },
              { label: '50', value: 50 },
            ]"
            option-label="label"
            option-value="value"
            class="w-24"
          />
        </div>
      </div>
      <Button
        v-if="isAuthenticated"
        label="+ New Routine"
        @click="() => router.push({ name: 'routine-create' })"
      />
    </div>

    <!-- ── Routines Table ─────────────────────────────────────────────────── -->
    <RoutineTable
      :routines="routines"
      :total="routinesTotal"
      :limit="limit"
      :page="page"
      :loading="loadingRoutines"
      :error="routinesError"
      :is-authenticated="isAuthenticated"
      :run-now-loading="runNowLoading"
      @run="runNow"
      @edit="goToEdit"
      @delete="openDelete"
      @page-change="(p) => { page = p }"
    />

    <!-- ── Delete Confirmation Dialog ────────────────────────────────────── -->
    <Dialog
      :visible="deleteDialogOpen"
      :modal="true"
      header="Delete Routine"
      @update:visible="deleteDialogOpen = false"
    >
      <p class="text-sm text-app-muted">
        Delete routine <strong>{{ deletingRoutine?.name }}</strong>? This cannot be undone.
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
