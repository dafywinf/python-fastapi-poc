# Testing Strategy

## Philosophy

Each test layer has a single responsibility. Higher layers prove integration
and user experience; lower layers prove logic and edge cases cheaply.

This repo now follows a **test pyramid with a somewhat thick middle**, not an
ice cream cone.

- most coverage sits in backend integration tests and frontend Vitest tests
- browser E2E coverage exists, but it is intentionally light and focused
- contract and component behavior are mostly proven below the browser layer

```
                     ┌──────────────────────────────┐
                     │  Playwright E2E               │  real browser + real backend
                     ├──────────────────────────────┤
                     │  Backend obs. E2E             │  full Docker Compose stack
                     ├──────────────────────────────┤
                     │  Backend perf                 │  real ports + testcontainers
                     ├──────────────────────────────┤
                     │  Frontend Vitest              │  jsdom + MSW + generated API contract
                     ├──────────────────────────────┤
                     │  Backend unit/int             │  real PostgreSQL (testcontainers)
                     └──────────────────────────────┘
```

A test belongs in the **lowest layer that can meaningfully catch the bug.**
Playwright is not a substitute for Vitest; Vitest is not a substitute for backend
integration tests.

---

## Layer Reference

### Backend — Unit

| | |
|---|---|
| **Runner** | pytest |
| **Environment** | No database. Pure Python logic only. |
| **Location** | `tests/unit/` |
| **Run** | `just backend-test-fast` |
| **Allure results** | `allure-results/` → CI artifact `allure-results-backend` |

**Safe to run anywhere** — devcontainer, host, CI. No Docker required.

---

### Backend — Integration

| | |
|---|---|
| **Runner** | pytest |
| **Environment** | Real PostgreSQL container (testcontainers, spun up per session) |
| **Location** | `tests/integration/` |
| **Run** | `just backend-test` (host only) |
| **Allure results** | `allure-results/` → CI artifact `allure-results-backend` |

**What it proves:** Every API endpoint returns the correct status codes, response
shapes, and database side-effects. The database layer is real — no mocking, no
SQLite.

**What it does NOT cover:** Frontend rendering, browser interaction, dialog
behaviour, routing, observability stack integration.

**Data strategy:** Each test is wrapped in a savepoint transaction
(`join_transaction_mode="create_savepoint"`) that is rolled back on teardown.
No truncation required; tests are fully isolated.

---

### Backend — Performance

| | |
|---|---|
| **Runner** | pytest (marked `perf`) |
| **Environment** | Real PostgreSQL container (testcontainers); real ports 18001–18004 |
| **Location** | `tests/perf/` |
| **Run** | `just backend-perf` |
| **Allure results** | `allure-results-perf/` → CI artifact `allure-results-perf` |

**What it proves:** Sync `def` handlers process requests concurrently via the
thread pool; `async def` handlers with blocking I/O serialise requests. These
tests are intentionally slow (~20s) and demonstrate the key architectural choice.

---

### Backend — Observability E2E

| | |
|---|---|
| **Runner** | pytest (marked `e2e`) |
| **Environment** | Full Docker Compose stack (PostgreSQL + Prometheus + Loki + Grafana) + FastAPI on host |
| **Location** | `tests/e2e/` |
| **Run** | `just backend-e2e` (requires `just platform-up` + `just backend-dev`) |
| **Allure results** | `allure-results-e2e/` → CI artifact `allure-results-e2e` |

**What it proves:** Prometheus scrapes metrics from `/metrics`, Loki receives
log lines, Grafana datasources are healthy and queryable. The observability stack
works end-to-end.

**What it does NOT cover:** Frontend behaviour, browser rendering.

---

### Frontend — Unit / Component (Vitest)

| | |
|---|---|
| **Runner** | Vitest |
| **Environment** | JSDOM (Node.js), no backend |
| **Location** | `frontend/src/__tests__/` |
| **Run** | `just frontend-test` |
| **Allure results** | `frontend/allure-results/` → CI artifact `allure-results-frontend` |

**What it proves:** Component rendering, user interaction (click, fill, submit),
query/mutation behavior, auth-aware rendering, API client behavior, and basic
accessibility checks.

**What it does NOT cover:** Real HTTP calls, Vue Router navigation in a real
browser, backend integration, dialog focus-trapping.

**Data strategy:** Component and client tests run against a shared app-aware
test harness plus **MSW** request handlers. The handlers are shaped from the
checked-in OpenAPI-generated schema so frontend assumptions stay aligned with
the backend contract. No backend process is involved.

Important files:

- `frontend/src/test/setup.ts`
- `frontend/src/test/utils/render.ts`
- `frontend/src/test/msw/server.ts`
- `frontend/src/test/msw/handlers.ts`
- `frontend/src/api/generated/schema.d.ts`

**Allure annotations:**
```ts
import * as allure from 'allure-js-commons'

describe('RoutinesView — initial render', () => {
  beforeEach(() => {
    allure.feature('Routines')
    allure.story('List View')
  })
  it('renders a data row for each routine', async () => { ... })
})
```

---

### Frontend — Browser E2E (Playwright)

| | |
|---|---|
| **Runner** | Playwright (`@playwright/test`) |
| **Browser** | Chromium (headless) |
| **Environment** | Real Vite dev server (:5173) + real FastAPI backend (:8000) + real PostgreSQL |
| **Location** | `frontend/e2e/` |
| **Run** | `just frontend-e2e` (requires `just dev-up`) |
| **Allure results** | `frontend/allure-results-e2e/` → CI artifact `allure-results-frontend-e2e` |

**What it proves:** The full frontend ↔ backend integration through a real
browser: page navigation, dialog open/close, form submission, table updates,
redirects, and accessibility smoke checks. Catches issues that jsdom cannot —
real Vue Router navigation, browser focus behavior, and Vite proxy routing.

**What it does NOT cover:** API edge cases (e.g. 422 validation errors), backend
business logic, observability stack.

**Data strategy:** Each test creates its own fixtures via the REST API directly
(`request` fixture pointing at `http://localhost:8000`) and deletes them in a
`finally` block. Tests are fully independent and can run in any order.

**Page Object Model:** All locators live in `e2e/pages/`. Tests should not contain raw
`page.locator(...)` calls.

```ts
// e2e/pages/RoutinesPage.ts — locators owned here, not in tests
editButtonFor(name: string): Locator {
  return this.row(name).getByTitle('Edit')
}

// e2e/routines.spec.ts — tests stay readable
await routinesPage.editButtonFor(original).click()
```

---

## Allure Reports

### Labeling Scheme

Allure is used to make the pyramid visible in reports, not just to pretty-print
test output. The repo uses one consistent label scheme across pytest, Vitest,
and Playwright:

| Label | Meaning | Typical values |
|-------|---------|----------------|
| `parentSuite` | Top-level product area | `Backend`, `Frontend` |
| `suite` | Test runner layer | `API Integration`, `Vitest`, `Performance`, `Live Stack E2E`, `Browser E2E` |
| `layer` | Pyramid layer | `base`, `middle`, `top` |
| `feature` / `story` | Functional area inside the suite | `Routines`, `Auth UI`, `Execution`, `Protected route` |

Current layer mapping:

- `tests/unit/` -> `Backend` / `Unit` / `layer=base`
- `tests/integration/` -> `Backend` / `API Integration` / `layer=base`
- `tests/perf/` -> `Backend` / `Performance` / `layer=middle`
- `tests/e2e/` -> `Backend` / `Live Stack E2E` / `layer=top`
- `frontend/src/__tests__/` -> `Frontend` / `Vitest` / `layer=base`
- `frontend/e2e/` -> `Frontend` / `Browser E2E` / `layer=top`

That means you can filter Allure results by `layer=base`, `layer=middle`, or
`layer=top` and see the pyramid directly instead of inferring it from file names.

### Combined report (recommended)

```bash
just report
```

Clears all previous results, runs the full test suite (`just ci`), then opens a single Allure report merging all three results directories. Requires `just platform-up` and `just dev-up`.

### Per-suite reports

| Suite | Results directory | How to view |
|-------|-------------------|-------------|
| Backend unit + integration | `allure-results/` | `just backend-test-report` |
| Backend perf | `allure-results-perf/` | `just backend-perf-report` |
| Backend obs E2E | `allure-results-e2e/` | `just backend-e2e` then `allure serve allure-results-e2e` |
| Frontend unit (Vitest) | `frontend/allure-results/` | `just frontend-test-report` |
| Frontend browser E2E (Playwright) | `frontend/allure-results-e2e/` | `just frontend-e2e-report` |

### Clearing stale results

```bash
just clean-reports
```

Deletes all three results directories so the next run starts from a clean slate. `just report` calls this automatically.

---

## CI Job Mapping

| GitHub Actions job | Suite(s) | Allure artifact | Needs |
|-------------------|----------|-----------------|-------|
| `frontend` | Vitest unit/component | `allure-results-frontend` | — |
| `backend-lint` | Ruff + basedpyright | — | — |
| `backend-test` | pytest unit + integration | `allure-results-backend` | `backend-lint` |
| `backend-perf` | pytest perf | — | `backend-lint` |
| `e2e` | pytest observability E2E | `allure-results-e2e` | `backend-lint` |
| `frontend-e2e` | Playwright browser E2E | `allure-results-frontend-e2e` | `backend-lint`, `frontend` |

---

## How to Add a New Test

### Backend unit test

1. Add a class to `tests/unit/` (no DB fixture, no client).
2. Decorate with `@allure.feature` and `@allure.story` at the **class level**.
3. Safe to run anywhere — devcontainer, host, CI.

### Backend integration test

1. Add a class to `tests/integration/` (or create a new file there).
2. Decorate with `@allure.feature` and `@allure.story` at the **class level**.
3. Use the `client: TestClient` fixture — the session is already isolated via savepoint.
4. **Run on host only** — requires Docker for testcontainers.

```python
@allure.feature("Routines")
@allure.story("Validation")
class TestRoutineValidation:
    def test_rejects_bad_schedule(self, client: TestClient) -> None:
        response = client.post("/routines/", json={"schedule_type": "interval"})
        assert response.status_code == 422
```

### Frontend Vitest test

1. Add to `frontend/src/__tests__/` (Vitest only picks up `src/**/*.{test,spec}.ts`).
2. Prefer the shared render helper and MSW handlers over raw `fetch` stubs.
3. Use `allure.feature` / `allure.story` for reporting.

```ts
describe('My new behaviour', () => {
  beforeEach(() => {
    allure.feature('Routines')
    allure.story('My Story')
  })
})
```

### Playwright E2E test

1. Add a spec file to `frontend/e2e/` (for example `routines.newfeature.spec.ts`).
2. Add any new locators to the relevant Page Object in `e2e/pages/`.
3. Create test data via the `request` fixture; always clean up in `finally`.

```ts
test('my new scenario', async ({ page, request }) => {
  // Setup
  const res = await request.post('http://localhost:8000/routines/', {
    data: { name: 'test', schedule_type: 'manual', is_active: true },
  })
  const { id } = await res.json() as { id: number }

  try {
    const routinesPage = new RoutinesPage(page)
    await routinesPage.goto()
    await expect(routinesPage.row('test')).toBeVisible()
  } finally {
    await request.delete(`http://localhost:8000/routines/${id}`)
  }
})
```
