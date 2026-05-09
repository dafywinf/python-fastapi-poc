<script setup lang="ts">
import { RouterLink } from 'vue-router'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Paginator from 'primevue/paginator'
import Tag from 'primevue/tag'
import type { Routine } from '../../../types/routine'

const props = defineProps<{
  routines: Routine[]
  total: number
  limit: number
  page: number
  loading: boolean
  error: string | null
  isAuthenticated: boolean
  runNowLoading: Record<number, boolean>
}>()

const emit = defineEmits<{
  run: [routine: Routine]
  edit: [routine: Routine]
  delete: [routine: Routine]
  pageChange: [page: number]
}>()
</script>

<template>
  <div>
    <div
      v-if="props.error"
      data-testid="routines-error"
      class="px-4 py-2.5 rounded-md text-sm bg-red-50 text-red-600 border border-red-200 mb-4"
    >
      {{ props.error }}
    </div>

    <div data-testid="routines-table" class="bg-app-card border border-app-border rounded overflow-hidden shadow-sm">
      <DataTable :value="props.routines" :loading="props.loading">
        <Column field="name" header="Name">
          <template #body="{ data }">
            <RouterLink
              :to="`/routines/${data.id}`"
              class="text-app-red font-medium no-underline hover:underline"
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
              data-testid="routine-active-indicator"
              :class="data.is_active ? 'text-green-600 font-semibold' : 'text-app-muted'"
            >
              {{ data.is_active ? '✓' : '—' }}
            </span>
          </template>
        </Column>
        <Column header="Actions">
          <template #body="{ data }">
            <div v-if="props.isAuthenticated" class="flex gap-1.5 justify-end">
              <Button
                :data-testid="`run-btn-${data.id}`"
                label="▶ Run"
                size="small"
                :disabled="!!props.runNowLoading[data.id]"
                @click="emit('run', data)"
              />
              <Button
                :data-testid="`edit-btn-${data.id}`"
                label="Edit"
                size="small"
                severity="secondary"
                @click="emit('edit', data)"
              />
              <Button
                :data-testid="`delete-btn-${data.id}`"
                label="Delete"
                size="small"
                severity="danger"
                @click="emit('delete', data)"
              />
            </div>
          </template>
        </Column>
      </DataTable>
      <Paginator
        v-if="props.total > props.limit"
        :rows="props.limit"
        :total-records="props.total"
        :first="(props.page - 1) * props.limit"
        @page="(e) => emit('pageChange', e.page + 1)"
      />
    </div>
  </div>
</template>
