import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../stores/auth'

export function useAuth() {
  const router = useRouter()
  const authStore = useAuthStore()

  const { accessToken: token, isAuthenticated, user } = storeToRefs(authStore)

  function setToken(t: string): void {
    authStore.setToken(t)
  }

  function login(): void {
    void router.push('/login')
  }

  function logout(): void {
    authStore.clearToken()
    void router.push('/')
  }

  return { token, isAuthenticated, user, setToken, login, logout }
}
