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

export async function createSequence(name: string, description?: string): Promise<number> {
  const token = await getToken()
  const ctx = await pwRequest.newContext({
    baseURL: BASE_API,
    extraHTTPHeaders: { Authorization: `Bearer ${token}` },
  })
  const res = await ctx.post('/sequences/', {
    data: { name, description: description ?? null },
  })
  const body = (await res.json()) as { id: number }
  await ctx.dispose()
  return body.id
}

/**
 * Obtain a JWT token and store it in the browser's localStorage so that
 * the frontend API client (`sequences.ts`) includes it on write requests.
 * Call this in a `beforeEach` for any test that interacts with the UI.
 */
export async function injectAuthToken(page: Page): Promise<void> {
  const token = await getToken()
  await page.goto('http://localhost:5173')
  await page.evaluate((t) => localStorage.setItem('access_token', t), token)
}

export async function listSequences(): Promise<Array<{ id: number }>> {
  const ctx = await pwRequest.newContext({ baseURL: BASE_API })
  const res = await ctx.get('/sequences/')
  const body = (await res.json()) as Array<{ id: number }>
  await ctx.dispose()
  return body
}

export async function deleteSequence(id: number): Promise<void> {
  const token = await getToken()
  const ctx = await pwRequest.newContext({
    baseURL: BASE_API,
    extraHTTPHeaders: { Authorization: `Bearer ${token}` },
  })
  await ctx.delete(`/sequences/${id}`)
  await ctx.dispose()
}
