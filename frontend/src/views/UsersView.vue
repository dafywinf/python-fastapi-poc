<script setup lang="ts">
import { computed } from 'vue'
import UserTable from '../features/users/components/UserTable.vue'
import { useUsersQuery } from '../features/users/queries/useUsersQuery'

const usersQuery = useUsersQuery()

const errorMessage = computed<string | null>(() =>
  usersQuery.error.value instanceof Error ? usersQuery.error.value.message : null,
)
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-end justify-between mb-1">
      <div>
        <div class="text-[11px] font-light uppercase tracking-[0.18em] text-gray-400 mb-0.5">Management</div>
        <h1 class="text-[26px] font-bold tracking-tight text-app-text m-0 leading-tight">Users</h1>
      </div>
    </div>

    <UserTable
      :users="usersQuery.data.value ?? []"
      :loading="usersQuery.isPending.value"
      :error="errorMessage"
    />
  </div>
</template>
