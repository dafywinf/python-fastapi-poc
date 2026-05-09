/**
 * Authenticated API helpers for Playwright e2e tests.
 *
 * Obtains a JWT token from the backend once per call and passes it as a
 * Bearer token on all write operations (POST / PATCH / DELETE).
 */
import { request as pwRequest, type Page } from '@playwright/test'

const BASE_API = 'http://127.0.0.1:8000'
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

async function withAuthedContext<T>(
  callback: (context: Awaited<ReturnType<typeof pwRequest.newContext>>) => Promise<T>,
  token?: string,
): Promise<T> {
  const resolvedToken = token ?? (await getToken())
  const context = await pwRequest.newContext({
    baseURL: BASE_API,
    extraHTTPHeaders: {
      Authorization: `Bearer ${resolvedToken}`,
    },
  })

  try {
    return await callback(context)
  } finally {
    await context.dispose()
  }
}

/**
 * Obtain a JWT token and set it as the browser cookie used by the app.
 * Returns the token so callers can reuse it (e.g. for API cleanup calls).
 * Call this in a `beforeEach` for any test that interacts with the UI.
 */
export async function injectAuthToken(page: Page): Promise<string> {
  const token = await getToken()
  await page.context().addCookies([
    {
      name: 'access_token',
      value: token,
      url: 'http://127.0.0.1:5173',
      httpOnly: true,
      sameSite: 'Lax',
    },
  ])
  return token
}

export async function createRoutine(name: string, token?: string): Promise<{ id: number }> {
  return withAuthedContext(async (context) => {
    const response = await context.post('/routines/', {
      data: {
        name,
        schedule_type: 'manual',
        schedule_config: null,
        is_active: true,
      },
    })
    return (await response.json()) as { id: number }
  }, token)
}

export async function deleteRoutinesByName(name: string, token?: string): Promise<void> {
  await withAuthedContext(async (context) => {
    const res = await context.get('/routines/')
    const body = (await res.json()) as { items: { id: number; name: string }[] }
    for (const r of body.items.filter((r) => r.name === name)) {
      await context.delete(`/routines/${r.id}`)
    }
  }, token)
}

export async function createAction(
  routineId: number,
  payload: { action_type: 'echo' | 'sleep'; config: Record<string, unknown> },
  token?: string,
): Promise<void> {
  await withAuthedContext(async (context) => {
    await context.post(`/routines/${routineId}/actions`, {
      data: payload,
    })
  }, token)
}
