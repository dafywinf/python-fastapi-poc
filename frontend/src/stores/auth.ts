import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

const TOKEN_KEY = 'access_token'

interface JwtPayload {
  sub: string
  name?: string
  exp: number
}

function decodePayload(token: string): JwtPayload | null {
  try {
    const payload = token.split('.')[1]
    if (!payload) {
      return null
    }

    const standardB64 = payload.replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(atob(standardB64)) as JwtPayload
  } catch (e) {
    console.warn('Failed to decode JWT payload', e)
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(null)

  const claims = computed<JwtPayload | null>(() => {
    if (!accessToken.value) {
      return null
    }
    return decodePayload(accessToken.value)
  })

  const isAuthenticated = computed(() => {
    if (!claims.value) {
      return false
    }
    return claims.value.exp * 1000 > Date.now()
  })

  const user = computed<{ email: string; name: string } | null>(() => {
    if (!claims.value) {
      return null
    }
    return {
      email: claims.value.sub,
      name: claims.value.name ?? claims.value.sub,
    }
  })

  function setToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token)
    accessToken.value = token
  }

  function clearToken(): void {
    localStorage.removeItem(TOKEN_KEY)
    accessToken.value = null
  }

  function hydrate(): void {
    accessToken.value = localStorage.getItem(TOKEN_KEY)
  }

  function attachStorageSync(): void {
    window.addEventListener('storage', (event) => {
      if (event.key === TOKEN_KEY) {
        accessToken.value = event.newValue
      }
    })
  }

  return {
    accessToken,
    claims,
    isAuthenticated,
    user,
    setToken,
    clearToken,
    hydrate,
    attachStorageSync,
  }
})
