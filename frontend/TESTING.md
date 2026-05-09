# Frontend Testing Guide

This project uses three testing layers. Each has a distinct scope, runner, and mocking strategy — they coexist without shared configuration.

---

## Testing Layers at a Glance

| Layer | Runner | Scope | Mock strategy | Script |
|---|---|---|---|---|
| Unit / View (Vitest) | Vitest + jsdom | Composables, views, stores | MSW (in-process) | `npm test` |
| Component (Playwright CT) | Playwright + Chromium | Isolated Vue components | Props / direct data | `npm run test:ct` |
| E2E (Playwright) | Playwright + Chromium | Full-page user flows | `page.route` or live backend | `npm run e2e` |

---

## Testing Philosophy: Why We Stub the Backend

For unit and E2E (mocked) tests, the backend is replaced with in-process stubs. This is a deliberate trade-off:

**Speed.** A test suite that contacts a live server is constrained by network latency, database I/O, and service startup time. Stubbed tests run in milliseconds and can execute on any machine without a running backend, including in CI before the backend image is even built.

**Isolation.** A live backend introduces shared state. Two parallel test runs can corrupt each other's data. Stubs are scoped to a single test and reset automatically on teardown.

**Determinism.** Network failures, rate limits, and transient server errors are impossible to reproduce reliably. Stubs let you test the exact response your component will receive — including errors and edge cases — on every run.

**The trade-off.** Stubs can drift from the real API. This is mitigated by:
- Generating TypeScript types directly from the OpenAPI schema (`npm run api:generate-types`), so mocked responses are type-checked against the real contract.
- Running the live-backend E2E suite (`npm run e2e`) against a real server before every pull request merge.

---

## Layer 1: Vitest (Unit and View Tests)

**Location:** `src/__tests__/`
**Config:** `vitest.config.ts`
**Environment:** jsdom (simulated browser DOM)

All tests mount components with full plugin registration via `mountWithApp` from `src/test/utils/render.ts`. This registers Pinia, Vue Router, TanStack Query, PrimeVue, and ToastService — the same plugins as the live app.

### MSW Handlers

API mocking uses Mock Service Worker (MSW) in Node mode. Handlers are grouped by domain in `src/test/msw/handlers.ts`:

```typescript
// Happy path
server.use(usersHandlers.list(mockUsers))

// Error state
server.use(usersHandlers.error(500, 'Network error'))

// Loading / pending state
server.use(usersHandlers.pending())
```

The MSW server is configured with `onUnhandledRequest: 'error'` in `src/test/setup.ts`. Any unmocked API call will fail the test immediately — this prevents false positives from silently skipped requests.

### Running

```bash
npm test                 # all Vitest tests
npm run test:coverage    # with coverage report
```

---

## Layer 2: Playwright Component Tests (CT)

**Location:** `ct/`
**Config:** `playwright-ct.config.ts`
**Runtime:** Real Chromium, CT iframe server (managed automatically)

Uses `@playwright/experimental-ct-vue`. Components run in a real browser iframe — no jsdom. This catches PrimeVue rendering issues, CSS-driven visibility, and layout bugs that jsdom cannot reproduce.

### Why CT Instead of More Vitest Tests?

| Concern | Vitest (jsdom) | Playwright CT (real browser) |
|---|---|---|
| PrimeVue component rendering | Partial | Full |
| CSS visibility (`v-show`, Tailwind) | Unreliable | Accurate |
| Speed | ~ms | ~seconds |
| Browser APIs (clipboard, canvas) | Polyfilled | Native |

Use Vitest for composable logic and view-level integration. Use CT for components where correct visual rendering matters.

### Plugin Registration

All Vue plugins are registered once in `playwright/index.ts` via the `beforeMount` hook — this mirrors `src/test/utils/render.ts` but targets the CT framework. The router stub (a memory router with a catch-all route) prevents console warnings from components that transitively import `useRouter()`.

### Why `UserTable.vue` is Extracted as a Presentational Component

Playwright CT mounts a single component. A component that calls `useQuery()` internally would need network mocking at the CT layer, which defeats the purpose of isolated component testing. `UserTable.vue` accepts `users`, `loading`, and `error` as props. This makes it trivially mountable with inline fixture data, with no network involved.

The query composable stays in `UsersView.vue` as the orchestrating shell. The existing Vitest test (`UsersView.test.ts`) continues to cover the view-level integration.

### `data-testid` Conventions

CT (and E2E) tests use `data-testid` attributes as stable locators. Never use CSS classes or Tailwind utilities as selectors — they are implementation details and change during refactoring.

| Attribute | Element | Purpose |
|---|---|---|
| `users-table` | `<DataTable>` root | Primary table locator |
| `users-table-container` | Wrapping card `<div>` | Container-level assertions |
| `user-name-cell-{id}` | Name column cell | Per-row avatar/name assertions |
| `copy-email-{id}` | Copy `<Button>` | Per-row action button |
| `users-error` | Error banner `<div>` | Error state assertions |
| `users-empty` | Empty state `<p>` | Empty state assertions |

### Running

```bash
npm run test:ct          # headless Chromium
npm run test:ct:ui       # Playwright UI mode (recommended during development)
```

---

## Layer 3: Playwright E2E Tests

**Location:** `e2e/`
**Config:** `playwright.config.ts`
**Runtime:** Real Chromium, Vite dev server at `http://127.0.0.1:5173`

### Two Modes: Live Backend vs Mocked API

#### Live Backend Tests (`routines.spec.ts`, `auth.spec.ts`)

- Require a running FastAPI backend at `http://127.0.0.1:8000`
- Use `injectAuthToken(page)` from `e2e/helpers/api.ts` to inject a real JWT cookie
- Create and clean up backend state via API helpers (`createRoutine`, `deleteRoutinesByName`)
- Best for: flows that require real database state, mutation testing, and full auth flows

#### Mocked API Tests (`users.spec.ts`)

- Require **only** the Vite dev server — no backend needed
- Use `mockApi(page)` from `e2e/helpers/mockApi.ts` to intercept `fetch` calls
- Use `mockAuthMe(page)` to satisfy the router auth guard without a real session
- Best for: read-heavy flows, error states, empty states, loading states, and new-page development before the backend API exists

---

## How-to: Mock a New API Endpoint

When writing a test for a new or existing endpoint, use `mockApi` from `e2e/helpers/mockApi.ts`.

### Template

```typescript
import { mockApi, mockAuthMe } from './helpers/mockApi'
import { expect, test } from '@playwright/test'

test('my feature renders correctly', async ({ page }) => {
  // 1. Mock auth (required for protected routes) — must come before page.goto()
  await mockAuthMe(page)

  // 2. Mock your endpoint
  await mockApi(page).get('/your-endpoint/', yourFixtureData)

  // 3. Navigate
  await page.goto('/your-page')

  // 4. Assert
  await expect(page.getByText('Expected content')).toBeVisible()
})
```

### Available Mock Methods

| Method | Default status | Use for |
|---|---|---|
| `.get(path, body)` | 200 | Listing or fetching resources |
| `.post(path, body)` | 201 | Creating resources |
| `.patch(path, body)` | 200 | Updating resources |
| `.delete(path)` | 204 | Deleting resources |
| `.error(path, status, detail)` | — | Error state testing |
| `.pending(path)` | — | Loading state testing |

### How `page.route` Works with the Vite Proxy

The app sends API requests to relative paths (e.g. `/users/`). In the browser, these resolve to `http://127.0.0.1:5173/users/`. The Vite dev server then proxies them to `http://127.0.0.1:8000` server-side.

`page.route` intercepts at the **browser level** — before the request reaches the Vite proxy. This means:

- Correct pattern: `http://127.0.0.1:5173/users/` (the Vite origin)
- Incorrect pattern: `http://127.0.0.1:8000/users/` (the FastAPI origin — never matches)

`mockApi` handles this automatically. You only need to pass the path (e.g. `/users/`).

### Auth Bypass (`mockAuthMe`)

The router guard in `src/router/index.ts` calls `useAuth().checkAuth()`, which sends `GET /users/me`. A 200 response with a user object makes the guard treat the session as authenticated.

```typescript
// Must be called BEFORE page.goto() for any protected route
await mockAuthMe(page)

// Optionally provide a custom user
await mockAuthMe(page, { email: 'test@example.com', name: 'Tester', picture: null })
```

---

## Selector Guide: Accessibility Roles over CSS Classes

### The Problem with CSS Classes

```typescript
// Fragile — breaks when a designer renames the class
page.locator('.user-table-row')

// Fragile — breaks when copy changes
page.locator('span.email-cell')
```

CSS classes and text content are implementation details. They change during refactoring and visual redesigns. Tests that depend on them break for reasons unrelated to the feature under test.

### Prefer Accessibility Roles

Semantic HTML elements and ARIA roles are stable identifiers that describe **what an element is**, not how it looks:

```typescript
// Stable — survives CSS refactoring
page.getByRole('heading', { name: 'Users' })
page.getByRole('button', { name: 'Copy email' })
page.getByRole('row').filter({ hasText: 'Alice' })
page.getByRole('img', { name: 'Bob' })
```

Role-based selectors have a second benefit: they fail the test if the element becomes inaccessible (e.g. a button loses its label). This turns accessibility regressions into test failures automatically.

### When to Use `data-testid`

Use `data-testid` when an element has no natural semantic role, or when you need to target a specific instance among many similar elements:

```typescript
// No role distinguishes this wrapping div from others
page.getByTestId('users-table-container')

// Targets a specific row's button by user id
page.getByTestId('copy-email-42')
```

Do not add `data-testid` to elements that already have a unique accessible role. Redundant test IDs add noise to the template.

### Priority Order

1. `getByRole` — always first choice
2. `getByLabel` — for form inputs
3. `getByPlaceholder` — for inputs without visible labels
4. `getByTestId` — for elements without a semantic role
5. CSS selectors — avoid; last resort only

---

## Step-by-Step: Adding a Test for a New Page

Follow these steps when a new route and view are added to the app.

### Step 1: Add `data-testid` Attributes to the Component

Identify the key interactive and structural elements in the new view and tag them:

```vue
<div data-testid="widget-table-container">
  <DataTable data-testid="widget-table" ...>
    <template #empty>
      <p data-testid="widget-empty">No widgets found.</p>
    </template>
  </DataTable>
</div>
```

### Step 2: Create a Page Object Model

Add a file to `e2e/pages/WidgetsPage.ts` following the existing POM pattern:

```typescript
import type { Locator, Page } from '@playwright/test'

export class WidgetsPage {
  private readonly page: Page
  readonly heading: Locator
  readonly tableContainer: Locator
  readonly emptyMessage: Locator

  constructor(page: Page) {
    this.page = page
    this.heading = page.getByRole('heading', { name: 'Widgets' })
    this.tableContainer = page.getByTestId('widget-table-container')
    this.emptyMessage = page.getByTestId('widget-empty')
  }

  async goto(): Promise<void> {
    await this.page.goto('/widgets')
  }

  row(name: string): Locator {
    return this.page.getByTestId('widget-table').getByRole('row').filter({ hasText: name })
  }
}
```

### Step 3: Add MSW Handlers for Vitest

Add handler factories to `src/test/msw/handlers.ts`:

```typescript
export const widgetsHandlers = {
  list(widgets: Widget[] = []) {
    return http.get('/widgets/', () => HttpResponse.json(widgets))
  },
  error(status = 500, detail = 'Failed to load widgets') {
    return http.get('/widgets/', () => HttpResponse.json({ detail }, { status }))
  },
  pending() {
    return http.get('/widgets/', () => new Promise(() => {}))
  },
}
```

### Step 4: Write a Vitest View Test

Add `src/__tests__/WidgetsView.test.ts`:

```typescript
import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'
import * as allure from 'allure-js-commons'
import { applyFrontendAllureLabels } from '../test/allure'
import { widgetsHandlers } from '../test/msw/handlers'
import { server } from '../test/msw/server'
import { mountWithApp } from '../test/utils/render'
import WidgetsView from '../views/WidgetsView.vue'

describe('WidgetsView', () => {
  beforeEach(() => {
    applyFrontendAllureLabels('Vitest', 'base')
    allure.feature('Widgets View')
  })

  it('renders a list of widgets after loading', async () => {
    server.use(widgetsHandlers.list([{ id: 1, name: 'Foo' }]))
    const wrapper = await mountWithApp(WidgetsView)
    await flushPromises()
    expect(wrapper.text()).toContain('Foo')
  })
})
```

### Step 5: Write a Mocked E2E Test

Add `e2e/widgets.spec.ts`:

```typescript
import { expect, test } from '@playwright/test'
import { allure } from 'allure-playwright'
import { applyFrontendE2EAllureLabels } from './helpers/allure'
import { mockApi, mockAuthMe } from './helpers/mockApi'
import { WidgetsPage } from './pages/WidgetsPage'

test.describe('Widgets (mocked API)', () => {
  test.beforeEach(async () => {
    await applyFrontendE2EAllureLabels('Browser E2E', 'top')
    await allure.feature('Widgets Page')
  })

  test('renders widget list', async ({ page }) => {
    await allure.story('List')
    await mockAuthMe(page)
    await mockApi(page).get('/widgets/', [{ id: 1, name: 'Foo' }])
    const widgetsPage = new WidgetsPage(page)
    await widgetsPage.goto()
    await expect(widgetsPage.row('Foo')).toBeVisible()
  })
})
```

### Step 6: Optionally Add a CT Spec

If the view contains a presentational component worth testing in a real browser, extract it with props (see `UserTable.vue` as a reference) and add a CT spec in `ct/WidgetTable.spec.ts`.

---

## Allure Reports

All three layers generate Allure results to separate directories:

| Layer | Results directory | Command |
|---|---|---|
| Vitest | `allure-results/` | `allure serve allure-results` |
| Playwright CT | `allure-results-ct/` | `allure serve allure-results-ct` |
| Playwright E2E | `allure-results-e2e/` | `allure serve allure-results-e2e` |

### Labelling Convention

| Layer | `suite` | `layer` |
|---|---|---|
| Vitest | `'Vitest'` | `'base'` |
| Playwright CT | `'CT'` | `'middle'` |
| Playwright E2E | `'Browser E2E'` | `'top'` |

---

## Running All Layers

```bash
# Unit / view tests (no backend needed)
npm test

# Component tests (no backend needed)
npm run test:ct

# Mocked E2E tests (only Vite dev server needed)
npm run dev &
npm run e2e:mocked

# Full E2E suite (requires backend + Vite)
just dev-up
npm run e2e
```
