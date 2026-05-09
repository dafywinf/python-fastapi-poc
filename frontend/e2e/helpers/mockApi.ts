import type { Page, Route } from '@playwright/test'

/**
 * mockApi — fluent wrapper around page.route for intercepting proxied API calls.
 *
 * All API requests in the app use relative paths (e.g. /users/) which the Vite
 * dev server proxies to http://127.0.0.1:8000. page.route intercepts at the
 * browser level before the request leaves the browser, so the correct origin to
 * match against is the Vite origin, not the FastAPI origin.
 *
 * URL matching: many API calls include query parameters (e.g. /routines/?limit=25).
 * The route is registered with a `**` suffix glob so it matches both bare paths
 * and paths with query strings. The pathname is then verified inside the handler
 * so that e.g. a mock for /routines/ does not intercept /routines/1.
 *
 * Each method uses route.fallback() (not route.continue()) when the HTTP method
 * or pathname does not match. route.fallback() passes the request to the next
 * matching page.route() handler; route.continue() would bypass all other
 * handlers and go directly to the network.
 *
 * Usage:
 *   await mockApi(page).get('/users/', mockUsers)
 *   await mockApi(page).post('/users/', createdUser, 201)
 *   await mockApi(page).error('/users/', 500, 'Server error')
 *   await mockApi(page).pending('/users/')
 */

const VITE_ORIGIN = 'http://127.0.0.1:5173'

interface MockApiHandle {
  get<T>(path: string, body: T, status?: number): Promise<void>
  post<T>(path: string, body: T, status?: number): Promise<void>
  patch<T>(path: string, body: T, status?: number): Promise<void>
  delete(path: string, status?: number): Promise<void>
  error(path: string, status: number, detail?: string, method?: string): Promise<void>
  pending(path: string, method?: string): Promise<void>
}

function fulfillJson<T>(route: Route, body: T, status: number): Promise<void> {
  return route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  })
}

function routePattern(path: string): string {
  // Append ** so the glob matches both /path/ and /path/?query=params.
  // The handler verifies the exact pathname to avoid matching sub-paths.
  return `${VITE_ORIGIN}${path}**`
}

function pathMatches(route: Route, path: string): boolean {
  // Exclude page navigation requests — only intercept fetch/xhr API calls.
  if (route.request().resourceType() === 'document') return false
  return new URL(route.request().url()).pathname === path
}

export function mockApi(page: Page): MockApiHandle {
  return {
    async get<T>(path: string, body: T, status = 200): Promise<void> {
      await page.route(routePattern(path), (route) => {
        if (!pathMatches(route, path) || route.request().method() !== 'GET') return route.fallback()
        return fulfillJson(route, body, status)
      })
    },

    async post<T>(path: string, body: T, status = 201): Promise<void> {
      await page.route(routePattern(path), (route) => {
        if (!pathMatches(route, path) || route.request().method() !== 'POST') return route.fallback()
        return fulfillJson(route, body, status)
      })
    },

    async patch<T>(path: string, body: T, status = 200): Promise<void> {
      await page.route(routePattern(path), (route) => {
        if (!pathMatches(route, path) || route.request().method() !== 'PATCH') return route.fallback()
        return fulfillJson(route, body, status)
      })
    },

    async delete(path: string, status = 204): Promise<void> {
      await page.route(routePattern(path), (route) => {
        if (!pathMatches(route, path) || route.request().method() !== 'DELETE') return route.fallback()
        return route.fulfill({ status, body: '' })
      })
    },

    async error(path: string, status: number, detail = 'Internal Server Error', method = 'GET'): Promise<void> {
      await page.route(routePattern(path), (route) => {
        if (!pathMatches(route, path) || route.request().method() !== method) return route.fallback()
        return fulfillJson(route, { detail }, status)
      })
    },

    async pending(path: string, method = 'GET'): Promise<void> {
      await page.route(routePattern(path), (route) => {
        if (!pathMatches(route, path) || route.request().method() !== method) return route.fallback()
        // Never resolves — simulates a permanently pending request (loading state)
        return new Promise<void>(() => {})
      })
    },
  }
}

/**
 * Bypasses the router auth guard by mocking GET /users/me.
 *
 * The guard in src/router/index.ts calls useAuth().checkAuth(), which sends
 * GET /users/me. A 200 response makes the guard treat the session as valid.
 * This must be registered BEFORE page.goto() — the guard fires during navigation.
 */
export async function mockAuthMe(
  page: Page,
  user: { email: string; name: string; picture: string | null } = {
    email: 'admin@example.com',
    name: 'Admin',
    picture: null,
  },
): Promise<void> {
  await page.route(`${VITE_ORIGIN}/users/me`, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(user),
    }),
  )
}
