<script setup lang="ts">
import ActiveExecutionsList from '../features/routines/components/ActiveExecutionsList.vue'
</script>

<template>
  <div class="flex flex-col gap-5">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-app-text m-0">
        Currently Executing
      </h1>
      <span class="text-xs text-app-muted">Refreshes every 2s</span>
    </div>

    <div class="border border-app-border rounded-lg overflow-hidden">
      <ActiveExecutionsList />
    </div>
  </div>
</template>
