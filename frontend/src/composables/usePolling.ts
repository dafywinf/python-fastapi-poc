/**
 * usePolling — generic polling composable.
 *
 * Calls `fn` immediately on mount, then on a fixed interval. Cleans up the
 * interval on component unmount to prevent memory leaks on navigation.
 */

import { onMounted, onUnmounted, ref } from 'vue'
import type { Ref } from 'vue'

/**
 * Generic polling composable. Calls `fn` immediately on mount, then on a
 * fixed interval. Cleans up the interval on component unmount.
 *
 * @param fn - Async function to call on each poll cycle.
 * @param intervalMs - Polling interval in milliseconds.
 * @returns Reactive `data`, `loading`, `error` refs and a `refresh` function.
 */
export function usePolling<T>(
  fn: () => Promise<T>,
  intervalMs: number,
): {
  data: Ref<T | null>
  loading: Ref<boolean>
  error: Ref<Error | null>
  refresh: () => Promise<void>
} {
  const data = ref<T | null>(null) as Ref<T | null>
  const loading = ref(true) // true only during the initial fetch
  const error = ref<Error | null>(null)
  let timer: ReturnType<typeof setInterval> | null = null

  async function refresh(): Promise<void> {
    try {
      data.value = await fn()
      error.value = null
    } catch (e) {
      error.value = e instanceof Error ? e : new Error(String(e))
      // retain last-good data; continue polling
    }
  }

  onMounted(async () => {
    await refresh()
    loading.value = false
    timer = setInterval(() => void refresh(), intervalMs)
  })

  onUnmounted(() => {
    if (timer !== null) {
      clearInterval(timer)
      timer = null
    }
  })

  return { data, loading, error, refresh }
}
