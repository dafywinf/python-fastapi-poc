import { beforeEach, describe, expect, it, vi } from 'vitest'

// Mock vue-router before importing useAuth
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

// Provide a minimal localStorage mock
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} },
  }
})()
Object.defineProperty(global, 'localStorage', { value: localStorageMock })

// A JWT that expires far in the future (exp: year 2099)
// Payload: { sub: "alice@example.com", name: "Alice", exp: 4070908800 }
const VALID_TOKEN =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  btoa(JSON.stringify({ sub: 'alice@example.com', name: 'Alice', exp: 4070908800 }))
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_') +
  '.fake-signature'

// A JWT that expired in the past (exp: year 2000)
const EXPIRED_TOKEN =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  btoa(JSON.stringify({ sub: 'old@example.com', name: 'Old', exp: 946684800 }))
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_') +
  '.fake-signature'

describe('useAuth', () => {
  beforeEach(() => {
    localStorageMock.clear()
    vi.resetModules()
  })

  it('isAuthenticated is false when localStorage is empty', async () => {
    const { useAuth } = await import('../composables/useAuth')
    const { isAuthenticated } = useAuth()
    expect(isAuthenticated.value).toBe(false)
  })

  it('isAuthenticated is true after setToken with valid JWT', async () => {
    const { useAuth } = await import('../composables/useAuth')
    const { isAuthenticated, setToken } = useAuth()
    setToken(VALID_TOKEN)
    expect(isAuthenticated.value).toBe(true)
  })

  it('isAuthenticated is false for an expired JWT', async () => {
    localStorageMock.setItem('access_token', EXPIRED_TOKEN)
    const { useAuth } = await import('../composables/useAuth')
    const { isAuthenticated } = useAuth()
    expect(isAuthenticated.value).toBe(false)
  })

  it('user returns decoded email and name from JWT', async () => {
    const { useAuth } = await import('../composables/useAuth')
    const { user, setToken } = useAuth()
    setToken(VALID_TOKEN)
    expect(user.value?.email).toBe('alice@example.com')
    expect(user.value?.name).toBe('Alice')
  })

  it('user is null when not authenticated', async () => {
    const { useAuth } = await import('../composables/useAuth')
    const { user } = useAuth()
    expect(user.value).toBeNull()
  })

  it('logout clears token and localStorage', async () => {
    localStorageMock.setItem('access_token', VALID_TOKEN)
    const { useAuth } = await import('../composables/useAuth')
    const { isAuthenticated, logout } = useAuth()
    expect(isAuthenticated.value).toBe(true)
    logout()
    expect(isAuthenticated.value).toBe(false)
    expect(localStorageMock.getItem('access_token')).toBeNull()
  })

  it('setToken persists token to localStorage', async () => {
    const { useAuth } = await import('../composables/useAuth')
    const { setToken } = useAuth()
    setToken(VALID_TOKEN)
    expect(localStorageMock.getItem('access_token')).toBe(VALID_TOKEN)
  })

  it('isAuthenticated is false and user is null when localStorage holds a malformed JWT', async () => {
    localStorageMock.setItem('access_token', 'not.a.jwt')
    const { useAuth } = await import('../composables/useAuth')
    const { isAuthenticated, user } = useAuth()
    expect(isAuthenticated.value).toBe(false)
    expect(user.value).toBeNull()
  })
})
