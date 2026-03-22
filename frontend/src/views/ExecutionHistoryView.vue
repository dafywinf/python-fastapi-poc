<template>
  <div class="flex flex-col gap-5">
    <!-- Header + filters -->
    <div class="flex items-center justify-between flex-wrap gap-3">
      <h1 class="text-2xl font-semibold text-slate-800 m-0">Execution History</h1>
      <div class="flex items-end gap-3 flex-wrap">
        <div class="flex flex-col gap-1">
          <label class="text-xs font-medium text-slate-600">Routine</label>
          <Select
            v-model="selectedRoutineId"
            :options="[{ label: 'All Routines', value: null }, ...routines.map(r => ({ label: r.name, value: r.id }))]"
            option-label="label"
            option-value="value"
            class="w-48"
            placeholder="All Routines"
          />
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-xs font-medium text-slate-600">Show</label>
          <Select
            v-model="limit"
            :options="[{ label: '10', value: 10 }, { label: '20', value: 20 }, { label: '50', value: 50 }]"
            option-label="label"
            option-value="value"
            class="w-24"
          />
        </div>
      </div>
    </div>

    <!-- Error banner -->
    <div v-if="error" class="bg-red-50 border border-red-200 text-red-600 text-sm px-4 py-2 rounded-md">
      {{ error }}
    </div>

    <!-- Table -->
    <div class="border border-slate-200 rounded-lg overflow-hidden">
      <DataTable :value="executions" :loading="loading">
        <Column field="routine_name" header="Routine Name">
          <template #body="{ data }">
            <RouterLink :to="`/routines/${data.routine_id}`" class="text-indigo-700 font-medium no-underline hover:underline">
              {{ data.routine_name }}
            </RouterLink>
          </template>
        </Column>
        <Column field="status" header="Status">
          <template #body="{ data }">
            <Tag
              :value="data.status"
              :severity="data.status === 'completed' ? 'success' : data.status === 'failed' ? 'danger' : 'warn'"
            />
          </template>
        </Column>
        <Column field="triggered_by" header="Triggered By">
          <template #body="{ data }">
            <Tag :value="data.triggered_by" severity="secondary" />
          </template>
        </Column>
        <Column field="started_at" header="Started At">
          <template #body="{ data }">
            <span class="text-slate-500">{{ formatDate(data.started_at) }}</span>
          </template>
        </Column>
        <Column header="Duration">
          <template #body="{ data }">
            <span class="text-slate-500">{{ durationLabel(data.started_at, data.completed_at) }}</span>
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
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
