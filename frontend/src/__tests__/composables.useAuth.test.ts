import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as allure from 'allure-js-commons'
import { applyFrontendAllureLabels } from '../test/allure'

// Mock vue-router before importing useAuth
const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
}))

describe('useAuth', () => {
  beforeEach(() => {
    applyFrontendAllureLabels('Vitest', 'base')
    allure.feature('useAuth')
    mockPush.mockClear()
    vi.resetModules()
  })

  it('isAuthenticated is false before checkAuth is called', async () => {
    const { useAuth } = await import('../composables/useAuth')
    const { isAuthenticated } = useAuth()
    expect(isAuthenticated.value).toBe(false)
  })

  it('user is null before checkAuth is called', async () => {
    const { useAuth } = await import('../composables/useAuth')
    const { user } = useAuth()
    expect(user.value).toBeNull()
  })

  it('isAuthenticated is true after checkAuth succeeds', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            email: 'alice@example.com',
            name: 'Alice',
            picture: null,
          }),
      }),
    )

    const { useAuth } = await import('../composables/useAuth')
    const { isAuthenticated, checkAuth } = useAuth()
    await checkAuth()
    expect(isAuthenticated.value).toBe(true)

    vi.unstubAllGlobals()
  })

  it('user is populated after checkAuth succeeds', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            email: 'alice@example.com',
            name: 'Alice',
            picture: null,
          }),
      }),
    )

    const { useAuth } = await import('../composables/useAuth')
    const { user, checkAuth } = useAuth()
    await checkAuth()
    expect(user.value?.email).toBe('alice@example.com')
    expect(user.value?.name).toBe('Alice')

    vi.unstubAllGlobals()
  })

  it('isAuthenticated is false when /users/me returns 401', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
      }),
    )

    const { useAuth } = await import('../composables/useAuth')
    const { isAuthenticated, checkAuth } = useAuth()
    await checkAuth()
    expect(isAuthenticated.value).toBe(false)

    vi.unstubAllGlobals()
  })

  it('isAuthenticated is false when fetch throws a network error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Network error')))

    const { useAuth } = await import('../composables/useAuth')
    const { isAuthenticated, checkAuth } = useAuth()
    await checkAuth()
    expect(isAuthenticated.value).toBe(false)

    vi.unstubAllGlobals()
  })

  it('logout clears user state and navigates to /', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn()
        .mockResolvedValueOnce({
          ok: true,
          json: () =>
            Promise.resolve({
              email: 'alice@example.com',
              name: 'Alice',
              picture: null,
            }),
        })
        .mockResolvedValueOnce({ ok: true }),
    )

    const { useAuth } = await import('../composables/useAuth')
    const { isAuthenticated, checkAuth, logout } = useAuth()
    await checkAuth()
    expect(isAuthenticated.value).toBe(true)

    await logout()
    expect(isAuthenticated.value).toBe(false)
    expect(mockPush).toHaveBeenCalledWith('/')

    vi.unstubAllGlobals()
  })

  it('login navigates to /login', async () => {
    const { useAuth } = await import('../composables/useAuth')
    const { login } = useAuth()
    login()
    expect(mockPush).toHaveBeenCalledWith('/login')
  })

  it('logout logs console.error and clears state when fetch returns non-2xx status', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)

    vi.stubGlobal(
      'fetch',
      vi.fn()
        .mockResolvedValueOnce({
          ok: true,
          json: () =>
            Promise.resolve({
              email: 'alice@example.com',
              name: 'Alice',
              picture: null,
            }),
        })
        .mockResolvedValueOnce({ ok: false, status: 503 }),
    )

    const { useAuth } = await import('../composables/useAuth')
    const { isAuthenticated, checkAuth, logout } = useAuth()
    await checkAuth()
    expect(isAuthenticated.value).toBe(true)

    await logout()
    expect(consoleError).toHaveBeenCalledWith(
      '[useAuth] Logout request failed with status:',
      503,
    )
    expect(isAuthenticated.value).toBe(false)
    expect(mockPush).toHaveBeenCalledWith('/')

    consoleError.mockRestore()
    vi.unstubAllGlobals()
  })

  it('logout logs console.error and clears state on network error', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)

    vi.stubGlobal(
      'fetch',
      vi.fn()
        .mockResolvedValueOnce({
          ok: true,
          json: () =>
            Promise.resolve({
              email: 'alice@example.com',
              name: 'Alice',
              picture: null,
            }),
        })
        .mockRejectedValueOnce(new Error('Network failure')),
    )

    const { useAuth } = await import('../composables/useAuth')
    const { isAuthenticated, checkAuth, logout } = useAuth()
    await checkAuth()
    expect(isAuthenticated.value).toBe(true)

    await logout()
    expect(consoleError).toHaveBeenCalled()
    expect(isAuthenticated.value).toBe(false)
    expect(mockPush).toHaveBeenCalledWith('/')

    consoleError.mockRestore()
    vi.unstubAllGlobals()
  })

  it('checkAuth resets _checked to false on network error so the next call retries', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)

    vi.stubGlobal(
      'fetch',
      vi.fn()
        .mockRejectedValueOnce(new Error('Network failure'))
        .mockResolvedValueOnce({
          ok: true,
          json: () =>
            Promise.resolve({
              email: 'bob@example.com',
              name: 'Bob',
              picture: null,
            }),
        }),
    )

    const { useAuth } = await import('../composables/useAuth')
    const { isAuthenticated, user, checkAuth } = useAuth()

    // First call — network error, should reset _checked so it retries
    await checkAuth()
    expect(isAuthenticated.value).toBe(false)
    expect(consoleError).toHaveBeenCalled()

    // Second call — should re-fetch and populate user
    await checkAuth()
    expect(isAuthenticated.value).toBe(true)
    expect(user.value?.email).toBe('bob@example.com')

    consoleError.mockRestore()
    vi.unstubAllGlobals()
  })
})
