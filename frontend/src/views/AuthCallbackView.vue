<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

onMounted(() => {
  void router.push('/')
})
</script>

<template>
  <div class="flex items-center justify-center min-h-[70vh]">
    <p class="text-sm text-slate-500">Signing you in…</p>
  </div>
</template>
