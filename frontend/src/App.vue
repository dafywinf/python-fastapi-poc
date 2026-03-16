<template>
  <div class="app-shell">
    <AppNavbar />
    <div class="app-shell__body">
      <AppSidebar />
      <main class="app-shell__main">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppNavbar from './components/layout/AppNavbar.vue'
import AppSidebar from './components/layout/AppSidebar.vue'
</script>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.app-shell__body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.app-shell__main {
  flex: 1;
  overflow-y: auto;
  padding: 1.75rem 2rem;
  background: #ffffff;
}
</style>
