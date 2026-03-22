<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { usersApi, type User } from '../api/users'
import { formatDate } from '../utils/date'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'

const users = ref<User[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

function copyEmail(email: string): void {
  void navigator.clipboard.writeText(email)
}

onMounted(async () => {
  try {
    users.value = await usersApi.list()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load users'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="p-6 max-w-4xl">
    <h1 class="text-xl font-semibold text-slate-800 mb-5">Users</h1>

    <p v-if="loading" class="text-slate-500 text-sm flex items-center gap-2">
      <span class="inline-block w-4 h-4 border-2 border-slate-300 border-t-slate-600 rounded-full animate-spin"></span>
      Loading…
    </p>

    <p v-else-if="error" class="text-red-400 text-sm">{{ error }}</p>

    <div v-else class="bg-white border border-slate-200 rounded-lg overflow-hidden">
      <DataTable :value="users" :rows="20" stripedRows>
        <Column header="Name">
          <template #body="{ data }: { data: User }">
            <div class="flex items-center gap-2.5">
              <img
                v-if="data.picture"
                :src="data.picture"
                :alt="data.name"
                class="w-7 h-7 rounded-full object-cover flex-shrink-0"
              />
              <span
                v-else
                class="w-7 h-7 rounded-full bg-blue-500 text-white text-xs font-semibold flex items-center justify-center flex-shrink-0"
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
              @click="copyEmail(data.email)"
            />
          </template>
        </Column>

        <template #empty>
          <p class="text-center text-slate-400 italic py-4 text-sm">No users have logged in yet.</p>
        </template>
      </DataTable>
    </div>
  </div>
</template>
