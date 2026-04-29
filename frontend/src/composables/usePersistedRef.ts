import { ref, watch, type Ref } from 'vue'

/**
 * A ref whose value is synced to localStorage under the given key.
 * Falls back to `defaultValue` if no stored value exists or if it
 * cannot be parsed.
 */
export function usePersistedRef<T>(key: string, defaultValue: T): Ref<T> {
  const stored = localStorage.getItem(key)
  let initial: T = defaultValue
  if (stored !== null) {
    try {
      initial = JSON.parse(stored) as T
    } catch {
      // ignore – use default
    }
  }

  const value = ref<T>(initial) as Ref<T>

  watch(value, (v) => {
    localStorage.setItem(key, JSON.stringify(v))
  })

  return value
}
