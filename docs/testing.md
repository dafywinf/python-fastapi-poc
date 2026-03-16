# Testing Strategy

## Philosophy

Each test layer has a single responsibility. Higher layers prove integration
and user experience; lower layers prove logic and edge cases cheaply.

```
                     ┌──────────────────────────────┐
                     │  Playwright E2E  (12 tests)   │  real browser + real backend
                     ├──────────────────────────────┤
                     │  Backend obs. E2E (11 tests)  │  full Docker Compose stack
                     ├──────────────────────────────┤
                     │  Backend perf   (6 tests)     │  real ports + testcontainers
                     ├──────────────────────────────┤
                     │  Frontend Vitest (47 tests)   │  jsdom + mocked fetch
                     ├──────────────────────────────┤
                     │  Backend unit/int (21 tests)  │  real PostgreSQL (testcontainers)
                     └──────────────────────────────┘
```

A test belongs in the **lowest layer that can meaningfully catch the bug.**
Playwright is not a substitute for Vitest; Vitest is not a substitute for backend
integration tests.

---

## Layer Reference

### Backend — Unit / Integration

| | |
|---|---|
| **Runner** | pytest |
| **Environment** | Real PostgreSQL container (testcontainers, spun up per session) |
| **Location** | `tests/test_health.py`, `tests/test_metrics.py`, `tests/test_sequences.py` |
| **Run** | `just backend-test` |
| **Allure results** | `allure-results/` → CI artifact `allure-results-e2e` |

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
| **Allure results** | `allure-results/` (combined with integration results) |

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
| **Allure results** | `allure-results/` (combined with integration results) |

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
API client request/response shapes, TypeScript DTO validation.

**What it does NOT cover:** Real HTTP calls, Vue Router navigation in a real
browser, backend integration, dialog focus-trapping.

**Data strategy:** `globalThis.fetch` is stubbed with `vi.stubGlobal` and
restored with `vi.unstubAllGlobals`. No backend process is involved.

**Allure annotations:**
```ts
import * as allure from 'allure-js-commons'

describe('SequenceListView — initial render', () => {
  beforeEach(() => {
    allure.feature('Sequences')
    allure.story('List View')
  })
  it('renders a data row for each sequence', async () => { ... })
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
redirect after delete. Catches issues that jsdom cannot — real Vue Router
navigation, native `<dialog>` behaviour, Vite proxy routing.

**What it does NOT cover:** API edge cases (e.g. 422 validation errors), backend
business logic, observability stack.

**Data strategy:** Each test creates its own fixtures via the REST API directly
(`request` fixture pointing at `http://localhost:8000`) and deletes them in a
`finally` block. Tests are fully independent and can run in any order.

**Page Object Model:** All locators live in `e2e/pages/`. Tests never contain raw
`page.locator(...)` calls.

```ts
// e2e/pages/SequenceListPage.ts — locators owned here, not in tests
editButtonFor(name: string): Locator {
  return this.row(name).getByTitle('Edit')
}

// e2e/sequences.crud.spec.ts — tests stay readable
await listPage.editButtonFor(original).click()
```

---

## Allure Reports

### Combined report (recommended)

```bash
just report
```

Clears all previous results, runs the full test suite (`just ci`), then opens a single Allure report merging all three results directories. Requires `just platform-up` and `just dev-up`.

### Per-suite reports

| Suite | Results directory | How to view |
|-------|-------------------|-------------|
| Backend integration + perf + obs E2E | `allure-results/` | `just backend-test-report` |
| Frontend unit (Vitest) | `frontend/allure-results/` | `just frontend-test-report` |
| Frontend browser E2E (Playwright) | `frontend/allure-results-e2e/` | `just frontend-e2e-report` |

### Clearing stale results

```bash
just clean-reports
```

Deletes all three results directories so the next run starts from a clean slate. `just report` calls this automatically.

---

## CI Job Mapping

| GitHub Actions job | Suite(s) | Needs |
|-------------------|----------|-------|
| `frontend` | Vitest unit/component | — |
| `backend-lint` | Ruff + basedpyright | — |
| `backend-test` | pytest unit/integration | `backend-lint` |
| `backend-perf` | pytest perf | `backend-lint` |
| `e2e` | pytest observability E2E | `backend-lint` |
| `frontend-e2e` | Playwright browser E2E | `backend-lint`, `frontend` |

---

## How to Add a New Test

### Backend integration test

1. Add a class to the appropriate `tests/test_*.py` file (or create a new one).
2. Decorate with `@allure.feature` and `@allure.story` at the **class level**.
3. Use the `client: TestClient` fixture — the session is already isolated via savepoint.

```python
@allure.feature("Sequences")
@allure.story("Validation")
class TestSequenceValidation:
    def test_rejects_empty_name(self, client: TestClient) -> None:
        response = client.post("/sequences/", json={"name": ""})
        assert response.status_code == 422
```

### Frontend Vitest test

1. Add to `frontend/src/__tests__/` (Vitest only picks up `src/**/*.{test,spec}.ts`).
2. Stub `fetch` with `vi.stubGlobal` in `beforeEach`; restore with `vi.unstubAllGlobals` in `afterEach`.
3. Use `allure.feature` / `allure.story` for reporting.

```ts
describe('My new behaviour', () => {
  beforeEach(() => {
    allure.feature('Sequences')
    allure.story('My Story')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(...))
  })
  afterEach(() => vi.unstubAllGlobals())
})
```

### Playwright E2E test

1. Add a spec file to `frontend/e2e/` (e.g. `sequences.newfeature.spec.ts`).
2. Add any new locators to the relevant Page Object in `e2e/pages/`.
3. Create test data via the `request` fixture; always clean up in `finally`.

```ts
test('my new scenario', async ({ page, request }) => {
  // Setup
  const res = await request.post('http://localhost:8000/sequences', { data: { name: 'test' } })
  const { id } = await res.json() as { id: number }

  try {
    const listPage = new SequenceListPage(page)
    await listPage.goto()
    await expect(listPage.row('test')).toBeVisible()
  } finally {
    await request.delete(`http://localhost:8000/sequences/${id}`)
  }
})
```
