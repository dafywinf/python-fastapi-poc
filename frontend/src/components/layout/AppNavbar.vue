<script setup lang="ts">
import Button from 'primevue/button'
import { useAuth } from '../../composables/useAuth'

const { isAuthenticated, user, login, logout } = useAuth()
</script>

<template>
  <header class="flex items-center justify-between px-6 h-14 bg-slate-800 text-slate-100 flex-shrink-0 border-b border-slate-700">
    <div class="flex items-center gap-6">
      <RouterLink to="/routines" class="text-base font-semibold text-white tracking-tight no-underline">
        Home Auto
      </RouterLink>
      <nav class="flex gap-4">
        <RouterLink to="/routines" class="text-sm text-slate-400 no-underline hover:text-white transition-colors [&.router-link-active]:text-white">Routines</RouterLink>
        <RouterLink to="/history" class="text-sm text-slate-400 no-underline hover:text-white transition-colors [&.router-link-active]:text-white">History</RouterLink>
        <RouterLink to="/users" class="text-sm text-slate-400 no-underline hover:text-white transition-colors [&.router-link-active]:text-white">Users</RouterLink>
      </nav>
    </div>
    <div class="flex items-center gap-3">
      <template v-if="isAuthenticated && user">
        <span class="text-xs text-slate-400" data-testid="user-email">{{ user.email }}</span>
        <Button label="Logout" size="small" severity="secondary" @click="logout" />
      </template>
      <Button v-else label="Sign in with Google" size="small" @click="login" />
    </div>
  </header>
</template>
