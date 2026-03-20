<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const route = useRoute()
const router = useRouter()
const { setToken } = useAuth()

onMounted(() => {
  const token = route.query.token
  if (typeof token === 'string' && token.length > 0) {
    setToken(token)
  }
  void router.push('/')
})
</script>

<template>
  <div class="callback-page">
    <p>Signing you in…</p>
  </div>
</template>

<style scoped>
.callback-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  color: #94a3b8;
}
</style>
