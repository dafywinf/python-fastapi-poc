<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'
import ProgressSpinner from 'primevue/progressspinner'

const router = useRouter()
const { setToken } = useAuth()
const authError = ref<string | null>(null)

const statusMessage = computed(() =>
  authError.value ? authError.value : 'Signing you in…',
)

onMounted(() => {
  const hash = window.location.hash.slice(1) // remove leading '#'
  const params = new URLSearchParams(hash)
  const token = params.get('token')
  const providerError = params.get('error')
  const providerErrorDescription = params.get('error_description')
  // Clear the fragment from the current history entry immediately.
  // This prevents the token from persisting in browser history and removes
  // it from the address bar before router.push() adds a new history entry.
  window.history.replaceState(null, '', window.location.pathname)
  if (token) {
    setToken(token)
    void router.push('/')
    return
  }
  authError.value =
    providerErrorDescription ??
    providerError ??
    'Authentication failed. Please try signing in again.'
})
</script>

<template>
  <div
    class="flex items-center justify-center min-h-[70vh]"
  >
    <div class="flex flex-col items-center gap-3 text-center max-w-md">
      <ProgressSpinner v-if="!authError" class="w-8 h-8" />
      <p
        :class="
          authError ? 'text-sm text-red-600' : 'text-sm text-slate-500'
        "
      >
        {{ statusMessage }}
      </p>
      <RouterLink
        v-if="authError"
        to="/login"
        class="inline-flex items-center justify-center rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 no-underline hover:bg-slate-50"
      >
        Back to sign in
      </RouterLink>
    </div>
  </div>
</template>
