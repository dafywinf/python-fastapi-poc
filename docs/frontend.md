# Frontend Architecture

## Overview

The `frontend/` directory contains a single-page application (SPA) built with
**Vite 8**, **Vue 3**, and **TypeScript**. It communicates exclusively with the
FastAPI backend running on port 8000. PrimeVue is registered in **unstyled mode**
so that all visual styling is owned by the application via **Tailwind CSS v4**.

Two test layers cover the frontend: **Vitest** (unit/component, jsdom, mocked API)
and **Playwright** (browser E2E, real Chromium, real backend). They are deliberately
kept separate — Vitest proves component logic in isolation; Playwright proves the
full frontend ↔ backend integration through an actual browser.

---

## Tech Stack

| Concern | Library | Notes |
|---------|---------|-------|
| Bundler | `vite ^8` | ESM-native, dev-server proxy built in |
| Framework | `vue ^3.5` | Composition API + `<script setup>` |
| Language | TypeScript `~5.9` | Strict mode via `vue-tsc` |
| Component library | `primevue ^4.5` | Unstyled mode — no theme CSS injected |
| Styling | `tailwindcss ^4` | PostCSS via `@tailwindcss/postcss` |
| Routing | `vue-router ^4.6` | HTML5 history mode |
| State | `pinia ^3` | Lightweight store (ready for Phase 2 auth) |
| Unit testing | `vitest ^4` | JSDOM environment, Allure reporter |
| Test utilities | `@vue/test-utils ^2.4` | Component mount helpers |
| Coverage | `@vitest/coverage-v8` | V8 native coverage |
| E2E testing | `@playwright/test ^1.52` | Chromium browser, Page Object Model |
| E2E reporting | `allure-playwright ^3.6` | Allure results to `allure-results-e2e/` |

---

## Key Architectural Decisions

### PrimeVue unstyled mode

PrimeVue is initialised with `{ unstyled: true }`, which disables the library's
built-in CSS. This gives full control over the visual output via Tailwind utility
classes and scoped `<style>` blocks, avoiding the specificity conflicts that arise
when mixing a pre-styled component library with a utility-first CSS framework.

### Vite dev-server proxy → port 8000

All API calls use relative paths (e.g. `/sequences/`). In development, Vite's
`server.proxy` forwards matching requests to `http://localhost:8000`, avoiding
CORS. In production the same relative paths are served from the same origin as
the SPA (or handled by a reverse proxy). No `VITE_API_URL` env var is needed.

The proxy rules use a `bypass` function for routes where both browser navigation
and API `fetch` calls are expected (e.g. `/sequences`, `/users`): navigation requests
(Accept: `text/html`) are served `index.html` so Vue Router handles the route
client-side, while `fetch` calls (Accept: `application/json`) are forwarded to the
backend. Without this, navigating directly to `/sequences` in a browser — or in a
Playwright test — would return JSON instead of the SPA shell.

The `/auth` proxy is configured **without** a bypass. Google's OAuth2 redirect
lands on `/auth/google/callback` as a browser navigation, but it **must** reach
the FastAPI backend — not the SPA shell. Adding a bypass to `/auth` would serve
`index.html` for that redirect and break the OAuth flow entirely.

### Fetch-based API client (no Axios)

`src/api/sequences.ts` wraps `fetch` in a thin typed helper. This avoids an
extra dependency while remaining straightforward to test — tests stub
`globalThis.fetch` with `vi.stubGlobal` and restore it with `vi.unstubAllGlobals`.

### Native `<dialog>` for modals

Create / Edit / Delete modals use the native HTML `<dialog>` element with
`showModal()` / `close()`. This provides built-in focus-trapping, `::backdrop`
styling, and accessibility semantics without a modal library.

### Auth state: `useAuth` composable

Authentication state is managed by `frontend/src/composables/useAuth.ts` — a single source
of truth backed by a Vue `ref<string | null>` initialised from `localStorage.getItem('access_token')`.

Using a `ref` (rather than reading localStorage directly inside a computed) means that
`setToken()` and `logout()` trigger reactive UI updates immediately in the same tick without
needing a component re-mount.

The composable exposes:
- `isAuthenticated` — `ComputedRef<boolean>`: true if token exists and `exp` claim is in the future
- `user` — `ComputedRef<{ email, name } | null>`: decoded from the JWT payload
- `setToken(t)` — called by `AuthCallbackView` after the OAuth redirect
- `login()` / `logout()` — navigate to `/login` or clear state and go home

JWT payloads use base64url encoding; `decodePayload` normalises to standard base64 before
calling `atob()` so it works correctly with real JWTs from the backend.

---

## Directory Structure

```
frontend/
├── public/                  # Static assets (favicon, icons)
├── src/
│   ├── __tests__/           # Vitest unit + component tests (jsdom, mocked API)
│   │   ├── api.sequences.test.ts
│   │   ├── types.sequence.test.ts
│   │   ├── SequenceListView.test.ts
│   │   └── SequenceDetailView.test.ts
│   ├── api/
│   │   ├── sequences.ts     # Typed fetch wrapper for /sequences endpoints
│   │   └── users.ts         # Typed fetch wrapper for /users endpoints
│   ├── composables/
│   │   └── useAuth.ts       # Auth state — token, isAuthenticated, user, login/logout
│   ├── components/
│   │   └── layout/
│   │       ├── AppNavbar.vue    # Top navigation bar (shows user email + logout when authenticated)
│   │       └── AppSidebar.vue   # Left sidebar (hidden on mobile)
│   ├── router/
│   │   └── index.ts         # Vue Router — HTML5 history
│   ├── types/
│   │   └── sequence.ts      # Sequence, SequenceCreate, SequenceUpdate DTOs
│   ├── views/
│   │   ├── SequenceListView.vue   # Sortable table + Create/Edit/Delete dialogs (write actions auth-gated)
│   │   ├── SequenceDetailView.vue # Read-only detail + Edit/Delete actions
│   │   ├── LoginView.vue          # "Sign in with Google" — window.location.href to /auth/google/login
│   │   ├── AuthCallbackView.vue   # Reads ?token= from URL, calls setToken(), navigates to /
│   │   └── UsersView.vue          # Lists all registered users (public)
│   ├── App.vue              # Root component — Navbar + Sidebar + <RouterView>
│   ├── main.ts              # App bootstrap — Vue, Pinia, Router, PrimeVue
│   └── style.css            # Global CSS — Tailwind base/components/utilities
├── e2e/                     # Playwright browser E2E tests (real Chromium + real backend)
│   ├── helpers/
│   │   └── api.ts           # injectAuthToken, createSequence, deleteSequence, listSequences
│   ├── pages/
│   │   ├── SequenceListPage.ts  # Page Object — list view locators & helpers
│   │   ├── SequenceDetailPage.ts# Page Object — detail view locators
│   │   └── dialogs.ts           # FormDialog + DeleteDialog helpers
│   ├── auth.spec.ts             # Google OAuth login flow + auth-gated UI assertions
│   ├── sequences.list.spec.ts   # Heading, empty state, row render, name-link nav
│   ├── sequences.crud.spec.ts   # Create, create-cancel, edit, delete via dialogs
│   └── sequences.detail.spec.ts # Navigate, back link, edit, delete + redirect
├── playwright.config.ts     # Playwright — Chromium, allure reporter, webServer
├── vitest.config.ts         # Vitest — jsdom, allure reporter, v8 coverage
├── vite.config.ts           # Vite — proxy (/sequences bypass; /auth no bypass; /users bypass; /health)
├── postcss.config.js        # PostCSS — @tailwindcss/postcss + autoprefixer
├── tsconfig.json            # TypeScript project references root
├── tsconfig.app.json        # App source tsconfig (strict)
├── tsconfig.node.json       # Vite / config files tsconfig
└── tsconfig.e2e.json        # E2E test tsconfig (DOM lib, no emit)
```

---

## Routes

| Path | Component | Description |
|------|-----------|-------------|
| `/` | — | Redirects to `/sequences` |
| `/sequences` | `SequenceListView` | Sortable table of all sequences with CRUD dialogs |
| `/sequences/:id` | `SequenceDetailView` | Read-only detail view with Edit / Delete actions |
| `/login` | `LoginView.vue` | "Sign in with Google" — sets `window.location.href` to `/auth/google/login` (top-level navigation, not fetch — required for the cross-origin redirect to Google) |
| `/auth/callback` | `AuthCallbackView.vue` | Reads `?token=` from URL, calls `setToken()`, navigates to `/` |
| `/users` | `UsersView.vue` | Lists all users who have logged in (public — no auth required) |

---

## API Client

`src/api/sequences.ts` exports a `sequencesApi` object with five methods that
map directly to the backend endpoints:

| Method | HTTP | Endpoint |
|--------|------|----------|
| `list()` | `GET` | `/sequences/` |
| `get(id)` | `GET` | `/sequences/:id` |
| `create(payload)` | `POST` | `/sequences/` |
| `update(id, payload)` | `PATCH` | `/sequences/:id` |
| `delete(id)` | `DELETE` | `/sequences/:id` |

All methods throw an `Error` with the API `detail` string when the response is
not OK, so callers can display it directly in the UI.

---

## Testing

### Unit / Component Tests (Vitest)

Tests live in `src/__tests__/` and are run with **Vitest** in a **JSDOM**
environment. The API is stubbed with `vi.stubGlobal('fetch', ...)` — no backend
needed. Each test file follows the same Allure annotation pattern used in the
Python backend:

```ts
import * as allure from 'allure-js-commons'

describe('sequencesApi.list', () => {
  beforeEach(() => allure.feature('Sequences API'))

  it('returns an array of sequences on success', async () => {
    allure.story('List')
    // ...
  })
})
```

The **allure-vitest** reporter writes results to `frontend/allure-results/`,
uploaded as the `allure-results-frontend` CI artifact.

```bash
npm test                  # single run
npm run test:coverage     # run with v8 coverage report
```

### E2E Tests (Playwright)

Browser-level tests live in `e2e/` and run against a real Chromium browser, the
live Vite dev server, and the live FastAPI backend. Tests use the **Page Object
Model** (`e2e/pages/`) and are fully independent — each creates and deletes its
own data via the REST API.

```bash
just frontend-e2e-install   # install Chromium once
just frontend-e2e            # run (requires just dev-up)
cd frontend && allure serve allure-results-e2e   # view report
```

Playwright E2E tests that require an authenticated state do **not** contact Google.
`injectAuthToken(page)` from `e2e/helpers/api.ts` calls `POST /auth/token` (available
when `ENABLE_PASSWORD_AUTH=true`) and injects the JWT into localStorage directly,
simulating a completed OAuth login.

For the full strategy — data patterns, Allure locations, CI job mapping, and how
to add new tests — see [`docs/testing.md`](./testing.md).

---

## Development Workflow

```bash
# from project root — start the full stack
just platform-up          # start postgres
just dev-up               # start backend (:8000) + frontend (:5173) in background

# from frontend/
npm run dev               # Vite dev server on :5173, proxies /sequences → :8000
npm run build             # type-check (vue-tsc) + production build → dist/
npm test                  # Vitest unit tests (no backend needed)
npm run e2e               # Playwright e2e tests (requires dev-up)
```

---

## C4 Component Diagram

```mermaid
graph TD
    user["👤 User<br/>Browser"]
    playwright["🎭 Playwright<br/>Chromium — E2E tests<br/>e2e/*.spec.ts"]

    subgraph spa["SPA (Vite / Vue 3) — :5173"]
        router["Vue Router<br/>HTML5 history"]
        listview["SequenceListView<br/>Sortable table<br/>Create / Edit / Delete dialogs"]
        detailview["SequenceDetailView<br/>Read-only + Edit / Delete"]
        apiclient["sequencesApi<br/>fetch wrapper"]
        navbar["AppNavbar"]
        sidebar["AppSidebar"]
    end

    backend["🐍 FastAPI<br/>localhost:8000<br/>REST API"]

    user -->|"navigates"| router
    router --> listview
    router --> detailview
    listview -->|"calls"| apiclient
    detailview -->|"calls"| apiclient
    apiclient -->|"HTTP via Vite proxy<br/>(bypass for navigation)"| backend
    playwright -->|"drives browser<br/>full page navigation"| spa
    playwright -->|"test setup/teardown<br/>direct REST calls"| backend
```
