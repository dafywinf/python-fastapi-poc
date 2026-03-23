# Frontend Architecture

## Overview

The `frontend/` directory contains the Vue 3 SPA for the home automation
application. It is built with Vite and TypeScript, uses PrimeVue in unstyled
mode, Tailwind CSS for visual styling, Pinia for auth/session state, and
TanStack Vue Query for server-state fetching and mutation invalidation.

The frontend is now routines-focused. The older CRUD scaffolding has been
removed from the live app.

Two main test layers cover the UI:

- Vitest for component, API-client, and accessibility checks in `jsdom`
- Playwright for a small set of real-browser smoke flows

For the full cross-repo test strategy, see [docs/testing.md](./testing.md).

## Tech Stack

| Concern | Library | Notes |
|---------|---------|-------|
| Bundler | `vite` | Dev server, build, proxying |
| Framework | `vue` | Composition API + `<script setup>` |
| Language | `typescript` | Strict frontend types |
| UI primitives | `primevue` | Unstyled mode plus PT config |
| Styling | `tailwindcss` | App-owned styling layer |
| Routing | `vue-router` | HTML5 history, lazy-loaded route views |
| App state | `pinia` | Auth/session state |
| Server state | `@tanstack/vue-query` | Queries, mutations, invalidation |
| Unit/component tests | `vitest` + `@vue/test-utils` | `jsdom` environment |
| API mocking | `msw` | Shared contract-aware request handlers |
| Contract generation | `openapi-typescript` | Generated schema types from backend OpenAPI |
| Browser E2E | `@playwright/test` | Light smoke coverage |
| A11y checks | `vitest-axe`, `@axe-core/playwright` | Automated accessibility checks |
| Formatting/linting | `eslint`, `prettier`, `stylelint` | Current frontend quality gates |

## Key Decisions

### PrimeVue in unstyled mode

PrimeVue is initialised with `unstyled: true`, and visual styling is supplied by
the application via Tailwind utility classes and PrimeVue PT configuration in
`src/primevue-pt.ts`. The point is consistency of primitives without giving up
control of the final look.

### Shared API client

The frontend uses `src/api/client.ts` as the single transport layer. It owns:

- JSON parsing
- bearer-token injection
- form-body handling
- consistent error extraction
- `204 No Content` handling

Feature API modules such as `src/api/routines.ts`, `src/api/users.ts`, and
`src/api/auth.ts` are thin wrappers on top of that shared client.

### Pinia for auth, Vue Query for backend data

Auth state lives in `src/stores/auth.ts`. That includes token hydration,
authentication status, and current-user derivation.

Fetched backend data does not live in Pinia. Routines, users, and execution
history use Vue Query so views can stay thin and mutations can invalidate data
cleanly instead of manually synchronising arrays.

### Feature composables instead of fat route views

The route views are now mostly orchestration and presentation. Query/mutation
logic lives in feature composables such as:

- `src/features/routines/useRoutinesPage.ts`
- `src/features/routines/useRoutineDetailPage.ts`
- `src/features/routines/useExecutionHistoryPage.ts`
- `src/features/users/queries/useUsersQuery.ts`

This makes the view components easier to read and keeps server-state behavior in
one place.

### OpenAPI-backed contract tests

The frontend exports the backend OpenAPI schema and generates local TypeScript
types:

- `src/api/generated/openapi.json`
- `src/api/generated/schema.d.ts`

Vitest tests use MSW handlers shaped from that contract, which is the main way
the UI is tested without needing a live backend for every scenario.

### Auth-aware route guards

The router uses route metadata plus a global `beforeEach` guard:

- `/login` is public-only
- `/users` requires authentication
- `/routines`, `/routines/:id`, and `/history` are readable without auth

Write actions are then hidden in the UI when unauthenticated.

## Directory Structure

```text
frontend/
├── src/
│   ├── __tests__/                # Vitest tests
│   ├── api/
│   │   ├── auth.ts
│   │   ├── client.ts
│   │   ├── routines.ts
│   │   ├── users.ts
│   │   └── generated/            # exported OpenAPI + generated TS schema
│   ├── components/
│   │   └── layout/               # App shell components
│   ├── composables/
│   │   ├── useAuth.ts            # compatibility wrapper around auth store
│   │   └── usePolling.ts
│   ├── features/
│   │   ├── routines/
│   │   │   ├── components/
│   │   │   ├── mutations/
│   │   │   ├── queries/
│   │   │   └── use*Page.ts
│   │   └── users/
│   │       └── queries/
│   ├── router/
│   │   └── index.ts
│   ├── stores/
│   │   └── auth.ts
│   ├── test/
│   │   ├── msw/
│   │   ├── setup.ts
│   │   └── utils/
│   ├── types/
│   │   └── routine.ts            # facade over generated contract types
│   ├── views/
│   │   ├── AuthCallbackView.vue
│   │   ├── ExecutionHistoryView.vue
│   │   ├── LoginView.vue
│   │   ├── RoutineDetailView.vue
│   │   ├── RoutinesView.vue
│   │   └── UsersView.vue
│   ├── App.vue
│   ├── main.ts
│   ├── primevue-pt.ts
│   └── style.css
├── e2e/
│   ├── accessibility.spec.ts
│   ├── auth.spec.ts
│   ├── routines.spec.ts
│   ├── helpers/
│   └── pages/
├── .prettierrc.json
├── .stylelintrc.json
├── eslint.config.js
├── package.json
├── playwright.config.ts
├── vite.config.ts
└── vitest.config.ts
```

## Routes

| Path | Description | Auth |
|------|-------------|------|
| `/` | Redirects to `/routines` | — |
| `/login` | Google sign-in entry point | Public-only |
| `/auth/callback` | Stores returned token fragment and redirects | — |
| `/routines` | Main routines list, active executions, recent history | Read-only public, write actions auth-gated |
| `/routines/:id` | Routine detail and action editing | Read-only public, write actions auth-gated |
| `/history` | Full execution history | Public |
| `/users` | Registered users | Auth required |

## API and Data Flow

### Transport

UI events call feature composables, which call feature API modules, which call
the shared API client.

### Queries

Vue Query handles:

- routines list
- routine detail
- active executions
- execution history
- users list

### Mutations

Routine and action mutations invalidate the appropriate query keys rather than
manually editing local view state. This is the main architectural shift from the
older page-local approach.

## Testing

### Vitest

Vitest covers most frontend behavior:

- component rendering
- auth-aware UI
- API client behavior
- query/mutation flows
- a11y checks with `vitest-axe`

The shared test harness is:

- `src/test/setup.ts`
- `src/test/utils/render.ts`
- `src/test/msw/server.ts`
- `src/test/msw/handlers.ts`

### Playwright

Playwright remains intentionally small. It is used for:

- auth smoke coverage
- routines smoke coverage
- browser-level accessibility smoke checks

These tests run against the real frontend and backend.

## Development Commands

From `frontend/`:

```bash
npm run dev
npm run build
npm run lint
npm run format
npm run stylelint
npm test
npm run e2e
npm run api:generate-types
```

From the repo root:

```bash
just frontend-dev
just frontend-check
just frontend-test
just frontend-e2e
```

## Proxy and OAuth Notes

The Vite dev server proxies API calls to the backend on port `8000`. The `/auth`
proxy must continue to forward browser navigations to the backend so Google OAuth
callbacks are handled server-side.

After successful login, the backend redirects to the SPA using a URL fragment:

```text
/auth/callback#token=<jwt>
```

That is deliberate: URL fragments are not sent to the server and do not appear
in server access logs.
