/**
 * useAuth — single source of truth for authentication state.
 *
 * Backed by a Vue ref so that setToken() and logout() trigger reactive updates
 * immediately without needing to re-mount components or re-read localStorage.
 *
 * The localStorage key 'access_token' matches the existing api/sequences.ts client.
 */

import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

const STORAGE_KEY = 'access_token'

interface JwtPayload {
  sub: string
  name?: string
  exp: number
}

function decodePayload(token: string): JwtPayload | null {
  try {
    const payloadB64 = token.split('.')[1]
    if (!payloadB64) return null
    // Real JWTs use base64url encoding (- and _ instead of + and /).
    // atob() requires standard base64 — normalise before decoding.
    const standardB64 = payloadB64.replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(atob(standardB64)) as JwtPayload
  } catch {
    return null
  }
}

// Module-level ref — shared across all useAuth() calls in a component tree.
const _token = ref<string | null>(localStorage.getItem(STORAGE_KEY))

export function useAuth() {
  const router = useRouter()

  const token = computed(() => _token.value)

  const isAuthenticated = computed<boolean>(() => {
    if (!_token.value) return false
    const payload = decodePayload(_token.value)
    if (!payload) return false
    return payload.exp * 1000 > Date.now()
  })

  const user = computed<{ email: string; name: string } | null>(() => {
    if (!_token.value) return null
    const payload = decodePayload(_token.value)
    if (!payload) return null
    return {
      email: payload.sub,
      name: payload.name ?? payload.sub,
    }
  })

  function setToken(t: string): void {
    localStorage.setItem(STORAGE_KEY, t)
    _token.value = t
  }

  function login(): void {
    void router.push('/login')
  }

  function logout(): void {
    localStorage.removeItem(STORAGE_KEY)
    _token.value = null
    void router.push('/')
  }

  return { token, isAuthenticated, user, setToken, login, logout }
}
