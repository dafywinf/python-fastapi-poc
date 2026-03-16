# Frontend Architecture

## Overview

The `frontend/` directory contains a single-page application (SPA) built with
**Vite 8**, **Vue 3**, and **TypeScript**. It communicates exclusively with the
FastAPI backend running on port 8000. PrimeVue is registered in **unstyled mode**
so that all visual styling is owned by the application via **Tailwind CSS v4**.

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
| Testing | `vitest ^4` | JSDOM environment, Allure reporter |
| Test utilities | `@vue/test-utils ^2.4` | Component mount helpers |
| Coverage | `@vitest/coverage-v8` | V8 native coverage |

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

### Fetch-based API client (no Axios)

`src/api/sequences.ts` wraps `fetch` in a thin typed helper. This avoids an
extra dependency while remaining straightforward to test — tests stub
`globalThis.fetch` with `vi.stubGlobal` and restore it with `vi.unstubAllGlobals`.

### Native `<dialog>` for modals

Create / Edit / Delete modals use the native HTML `<dialog>` element with
`showModal()` / `close()`. This provides built-in focus-trapping, `::backdrop`
styling, and accessibility semantics without a modal library.

---

## Directory Structure

```
frontend/
├── public/                  # Static assets (favicon, icons)
├── src/
│   ├── __tests__/           # Vitest unit tests (allure-annotated)
│   │   ├── api.sequences.test.ts
│   │   └── types.sequence.test.ts
│   ├── api/
│   │   └── sequences.ts     # Typed fetch wrapper for /sequences endpoints
│   ├── components/
│   │   └── layout/
│   │       ├── AppNavbar.vue    # Top navigation bar
│   │       └── AppSidebar.vue   # Left sidebar (hidden on mobile)
│   ├── router/
│   │   └── index.ts         # Vue Router — HTML5 history
│   ├── types/
│   │   └── sequence.ts      # Sequence, SequenceCreate, SequenceUpdate DTOs
│   ├── views/
│   │   ├── SequenceListView.vue   # Sortable table + Create/Edit/Delete dialogs
│   │   └── SequenceDetailView.vue # Read-only detail + Edit/Delete actions
│   ├── App.vue              # Root component — Navbar + Sidebar + <RouterView>
│   ├── main.ts              # App bootstrap — Vue, Pinia, Router, PrimeVue
│   └── style.css            # Global CSS — Tailwind base/components/utilities
├── vitest.config.ts         # Vitest — jsdom, allure reporter, v8 coverage
├── vite.config.ts           # Vite — proxy, plugin config
├── tailwind.config.js       # Tailwind content paths
├── postcss.config.js        # PostCSS — @tailwindcss/postcss + autoprefixer
├── tsconfig.json            # TypeScript project references root
├── tsconfig.app.json        # App source tsconfig (strict)
└── tsconfig.node.json       # Vite / config files tsconfig
```

---

## Routes

| Path | Component | Description |
|------|-----------|-------------|
| `/` | — | Redirects to `/sequences` |
| `/sequences` | `SequenceListView` | Sortable table of all sequences with CRUD dialogs |
| `/sequences/:id` | `SequenceDetailView` | Read-only detail view with Edit / Delete actions |

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

Tests live in `src/__tests__/` and are run with **Vitest** in a **JSDOM**
environment. Each test file follows the same Allure annotation pattern used in
the Python backend:

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
which the CI job uploads as the `allure-results-frontend` artifact.

Run locally:

```bash
npm test                  # single run
npm run test:coverage     # run with v8 coverage report
```

---

## Development Workflow

```bash
# from project root — start the backend (requires postgres)
just backend-dev

# from frontend/
npm run dev               # Vite dev server on :5173, proxies /sequences → :8000
npm run build             # type-check (vue-tsc) + production build → dist/
npm test                  # Vitest unit tests (no backend needed)
```

---

## C4 Component Diagram

```mermaid
graph TD
    user["👤 User<br/>Browser"]

    subgraph spa["SPA (Vite / Vue 3)"]
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
    apiclient -->|"HTTP via Vite proxy"| backend
```
