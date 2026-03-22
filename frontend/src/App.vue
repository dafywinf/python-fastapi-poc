<template>
  <div class="flex flex-col h-screen overflow-hidden">
    <AppNavbar />
    <div class="flex flex-1 overflow-hidden">
      <AppSidebar />
      <main class="flex-1 overflow-y-auto p-7 bg-white">
        <RouterView />
      </main>
    </div>
    <Toast />
  </div>
</template>

<script setup lang="ts">
import Toast from 'primevue/toast'
import AppNavbar from './components/layout/AppNavbar.vue'
import AppSidebar from './components/layout/AppSidebar.vue'
</script>
