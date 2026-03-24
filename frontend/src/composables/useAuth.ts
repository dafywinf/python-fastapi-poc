/**
 * useAuth — authentication state backed by the HttpOnly access_token cookie.
 *
 * Since the cookie is HttpOnly, JS cannot read it directly. Auth state is
 * determined by calling GET /users/me — a 200 means authenticated, 401 means not.
 * User info (email, name, picture) is populated from the /users/me response body.
 */

import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

interface AuthUser {
  email: string
  name: string
  picture: string | null
}

// Module-level refs — shared across all useAuth() calls.
const _user = ref<AuthUser | null>(null)
const _checked = ref(false)

export function useAuth() {
  const router = useRouter()

  const isAuthenticated = computed<boolean>(() => _user.value !== null)
  const user = computed<AuthUser | null>(() => _user.value)

  async function checkAuth(): Promise<void> {
    if (_checked.value) return
    _checked.value = true
    try {
      const response = await fetch('/users/me', { credentials: 'include' })
      if (response.ok) {
        const data = (await response.json()) as AuthUser
        _user.value = data
      } else {
        _user.value = null
      }
    } catch (err) {
      console.error('[useAuth] Failed to check auth status:', err)
      _checked.value = false
      _user.value = null
    }
  }

  function login(): void {
    void router.push('/login')
  }

  async function logout(): Promise<void> {
    try {
      const response = await fetch('/auth/logout', { method: 'POST', credentials: 'include' })
      if (!response.ok) {
        console.error('[useAuth] Logout request failed with status:', response.status)
      }
    } catch (err) {
      console.error('[useAuth] Logout network error:', err)
    }
    _user.value = null
    _checked.value = false
    void router.push('/')
  }

  return { isAuthenticated, user, checkAuth, login, logout }
}
