/**
 * Authenticated API helpers for Playwright e2e tests.
 *
 * Obtains a JWT token from the backend once per call and passes it as a
 * Bearer token on all write operations (POST / PATCH / DELETE).
 */
import { request as pwRequest, type Page } from '@playwright/test'

const BASE_API = 'http://localhost:8000'
const ADMIN_USERNAME = 'admin'
const ADMIN_PASSWORD = process.env['E2E_ADMIN_PASSWORD'] ?? 'admin'

async function getToken(): Promise<string> {
  const ctx = await pwRequest.newContext({ baseURL: BASE_API })
  const res = await ctx.post('/auth/token', {
    form: { username: ADMIN_USERNAME, password: ADMIN_PASSWORD },
  })
  const body = (await res.json()) as { access_token: string }
  await ctx.dispose()
  return body.access_token
}

/**
 * Obtain a JWT token and store it in the browser's localStorage so that
 * the frontend API client includes it on write requests.
 * Call this in a `beforeEach` for any test that interacts with the UI.
 */
export async function injectAuthToken(page: Page): Promise<void> {
  const token = await getToken()
  await page.goto('http://localhost:5173')
  await page.evaluate((t) => localStorage.setItem('access_token', t), token)
}
