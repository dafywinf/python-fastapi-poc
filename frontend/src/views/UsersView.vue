<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { usersApi, type User } from '../api/users'
import { formatDate } from '../utils/date'

const users = ref<User[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

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
  <div class="users-page">
    <h1 class="page-title">Users</h1>

    <p v-if="loading" class="state-message">Loading…</p>
    <p v-else-if="error" class="state-message state-message--error">{{ error }}</p>

    <table v-else class="users-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Email</th>
          <th>Joined</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="user in users" :key="user.id">
          <td class="user-name">
            <img
              v-if="user.picture"
              :src="user.picture"
              :alt="user.name"
              class="user-avatar"
            />
            <span v-else class="user-avatar user-avatar--placeholder">
              {{ user.name.charAt(0).toUpperCase() }}
            </span>
            {{ user.name }}
          </td>
          <td>{{ user.email }}</td>
          <td>{{ formatDate(user.created_at) }}</td>
        </tr>
        <tr v-if="users.length === 0">
          <td colspan="3" class="empty-state">No users have logged in yet.</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.users-page {
  padding: 1.5rem;
  max-width: 800px;
}

.page-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #f8fafc;
  margin-bottom: 1.25rem;
}

.state-message {
  color: #94a3b8;
  font-size: 0.875rem;
}

.state-message--error {
  color: #f87171;
}

.users-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.users-table th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  color: #94a3b8;
  border-bottom: 1px solid #334155;
  font-weight: 500;
}

.users-table td {
  padding: 0.625rem 0.75rem;
  border-bottom: 1px solid #1e293b;
  color: #e2e8f0;
  vertical-align: middle;
}

.user-name {
  display: flex;
  align-items: center;
  gap: 0.625rem;
}

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.user-avatar--placeholder {
  background: #3b82f6;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-state {
  color: #64748b;
  font-style: italic;
  text-align: center;
}
</style>
