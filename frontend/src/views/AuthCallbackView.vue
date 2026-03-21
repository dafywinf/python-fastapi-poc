<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const { setToken } = useAuth()

onMounted(() => {
  const hash = window.location.hash.slice(1) // remove leading '#'
  const params = new URLSearchParams(hash)
  const token = params.get('token')
  // Clear the fragment from the current history entry immediately.
  // This prevents the token from persisting in browser history and removes
  // it from the address bar before router.push() adds a new history entry.
  window.history.replaceState(null, '', window.location.pathname)
  if (token) {
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
