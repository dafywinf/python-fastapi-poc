<script setup lang="ts">
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Tag from 'primevue/tag'
import type { User } from '../../../api/users'
import { formatDate } from '../../../utils/date'

defineProps<{
  users: User[]
  loading?: boolean
  error?: string | null
}>()

function copyEmail(email: string): void {
  void navigator.clipboard.writeText(email)
}
</script>

<template>
  <div>
    <div
      v-if="error"
      class="px-4 py-2.5 rounded-md text-sm bg-red-50 text-red-600 border border-red-200"
      data-testid="users-error"
    >
      {{ error }}
    </div>

    <div
      class="bg-app-card border border-app-border rounded overflow-hidden shadow-sm"
      data-testid="users-table-container"
    >
      <DataTable
        :value="users"
        :loading="loading ?? false"
        :rows="20"
        striped-rows
        data-testid="users-table"
      >
        <Column header="Name">
          <template #body="{ data }: { data: User }">
            <div
              class="flex items-center gap-2.5"
              :data-testid="`user-name-cell-${data.id}`"
            >
              <img
                v-if="data.picture"
                :src="data.picture"
                :alt="data.name"
                class="w-7 h-7 rounded-full object-cover flex-shrink-0"
              />
              <span
                v-else
                class="w-7 h-7 rounded-full bg-blue-500 text-white text-xs font-semibold flex items-center justify-center flex-shrink-0"
                aria-hidden="true"
              >
                {{ data.name.charAt(0).toUpperCase() }}
              </span>
              <span>{{ data.name }}</span>
            </div>
          </template>
        </Column>

        <Column field="email" header="Email" />

        <Column header="Joined">
          <template #body="{ data }: { data: User }">
            {{ formatDate(data.created_at) }}
          </template>
        </Column>

        <Column header="Status">
          <template #body>
            <Tag value="Active" severity="success" />
          </template>
        </Column>

        <Column header="">
          <template #body="{ data }: { data: User }">
            <Button
              icon="pi pi-copy"
              text
              rounded
              size="small"
              aria-label="Copy email"
              :data-testid="`copy-email-${data.id}`"
              @click="copyEmail(data.email)"
            />
          </template>
        </Column>

        <template #empty>
          <p
            class="text-center text-app-muted italic py-4 text-sm"
            data-testid="users-empty"
          >
            No users have logged in yet.
          </p>
        </template>
      </DataTable>
    </div>
  </div>
</template>
