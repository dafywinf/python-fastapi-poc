<script setup lang="ts">
import Toast from 'primevue/toast'
import AppNavbar from './components/layout/AppNavbar.vue'
import AppSidebar from './components/layout/AppSidebar.vue'
import { useAuth } from './composables/useAuth'

const { isAuthenticated } = useAuth()
</script>

<template>
  <div v-if="isAuthenticated" class="flex flex-col h-screen overflow-hidden">
    <AppNavbar />
    <div class="flex flex-1 overflow-hidden">
      <AppSidebar />
      <main class="flex-1 overflow-y-auto p-6 bg-app-surface">
        <RouterView />
      </main>
    </div>
    <Toast />
  </div>
  <template v-else>
    <RouterView />
    <Toast />
  </template>
</template>
