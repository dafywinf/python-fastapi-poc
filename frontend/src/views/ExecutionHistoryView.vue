<script setup lang="ts">
import { reactive } from 'vue'
import InputText from 'primevue/inputtext'
import Paginator from 'primevue/paginator'
import Select from 'primevue/select'
import { useToast } from 'primevue/usetoast'
import ExecutionCard from '../features/routines/components/ExecutionCard.vue'
import { useExecutionHistoryPage } from '../features/routines/useExecutionHistoryPage'
import { routinesApi } from '../api/routines'
import type { ActiveRoutineExecution, RoutineExecution } from '../types/routine'

const toast = useToast()
const {
  routines,
  routinesError,
  executions,
  executionsTotal,
  loading,
  error,
  searchQuery,
  selectedRoutineId,
  limit,
  page,
} = useExecutionHistoryPage()

// Lazily-fetched full execution data (action rows) keyed by execution id
const expandedData = reactive<Record<number, ActiveRoutineExecution>>({})
const expandLoading = reactive<Record<number, boolean>>({})
const expandError = reactive<Record<number, boolean>>({})

async function onExpand(id: number): Promise<void> {
  if (expandedData[id] || expandLoading[id]) return
  delete expandError[id]
  expandLoading[id] = true
  try {
    const full = await routinesApi.getExecution(id)
    expandedData[id] = full
  } catch (e) {
    expandError[id] = true
    toast.add({
      severity: 'error',
      summary: 'Failed to load execution details',
      detail: e instanceof Error ? e.message : String(e),
      life: 5000,
    })
  } finally {
    delete expandLoading[id]
  }
}

function toCardExecution(e: RoutineExecution): ActiveRoutineExecution {
  return expandedData[e.id] ?? { ...(e as unknown as ActiveRoutineExecution), action_executions: [] }
}
</script>

<template>
  <div class="flex flex-col gap-5">
    <!-- Header + filters -->
    <div class="flex items-center justify-between flex-wrap gap-3">
      <h1 class="text-2xl font-semibold text-app-text m-0">
        Execution History
      </h1>
      <div class="flex items-end gap-3 flex-wrap">
        <div class="flex flex-col gap-1">
          <label class="text-xs font-medium text-app-muted">Search</label>
          <InputText
            v-model="searchQuery"
            placeholder="Filter by routine name…"
            class="w-48"
          />
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-xs font-medium text-app-muted">Routine</label>
          <Select
            v-model="selectedRoutineId"
            :options="[
              { label: 'All Routines', value: null },
              ...routines.map((r) => ({ label: r.name, value: r.id })),
            ]"
            option-label="label"
            option-value="value"
            class="w-48"
            placeholder="All Routines"
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
    </div>

    <!-- Error banners -->
    <div v-if="routinesError" data-testid="history-routines-error" class="bg-red-50 border border-red-200 text-red-600 text-sm px-4 py-2 rounded-md">
      {{ routinesError }}
    </div>
    <div v-if="error" data-testid="history-error" class="bg-red-50 border border-red-200 text-red-600 text-sm px-4 py-2 rounded-md">
      {{ error }}
    </div>

    <!-- Execution list -->
    <div data-testid="history-list" class="border border-app-border rounded-lg overflow-hidden">
      <div v-if="loading" data-testid="history-loading" class="px-4 py-6 text-center text-sm text-app-muted">Loading…</div>

      <div v-else-if="executions.length === 0" data-testid="history-empty" class="px-4 py-6 text-center text-sm text-app-muted">
        No executions found
      </div>

      <div v-else class="divide-y divide-app-border/60">
        <ExecutionCard
          v-for="execution in executions"
          :key="execution.id"
          :execution="toCardExecution(execution)"
          :detail-loading="expandLoading[execution.id] === true"
          :detail-error="expandError[execution.id] === true"
          @expand="onExpand"
        />
      </div>
      <Paginator
        v-if="executionsTotal > limit"
        :rows="limit"
        :total-records="executionsTotal"
        :first="(page - 1) * limit"
        @page="(e) => { page = e.page + 1 }"
      />
    </div>
  </div>
</template>
