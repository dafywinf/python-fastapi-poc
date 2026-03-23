import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as allure from 'allure-js-commons'
import { loginWithPassword } from '../api/auth'
import { applyFrontendAllureLabels } from '../test/allure'
import { authHandlers } from '../test/msw/handlers'
import { server } from '../test/msw/server'

describe('authApi', () => {
  beforeEach(() => {
    applyFrontendAllureLabels('Vitest', 'base')
    allure.feature('authApi')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('posts form-urlencoded credentials to /auth/token', async () => {
    const fetchSpy = vi.spyOn(global, 'fetch')
    server.use(
      authHandlers.login({
        access_token: 'test-token',
        token_type: 'bearer',
      }),
    )

    const result = await loginWithPassword('admin', 'secret')

    expect(result.access_token).toBe('test-token')
    expect(fetchSpy).toHaveBeenCalledWith(
      '/auth/token',
      expect.objectContaining({ method: 'POST' }),
    )

    const [, options] = fetchSpy.mock.calls[0] ?? []
    expect(options).toBeDefined()
    expect((options as RequestInit).headers).toBeInstanceOf(Headers)
    expect(String((options as RequestInit).body)).toContain('username=admin')
    expect(String((options as RequestInit).body)).toContain('password=secret')
  })
})
