# PrimeVue + Tailwind Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the Sequences domain entirely and migrate all remaining Vue views from hand-rolled scoped CSS to PrimeVue unstyled components styled with Tailwind CSS pass-through.

**Architecture:** Big-bang migration on a single branch. Backend sequences code is deleted first (routes, services, model, schemas, migration to drop table). Frontend sequences files are deleted next. Then PrimeVue pass-through infrastructure is wired up centrally, and each remaining view is rewritten view-by-view to use PrimeVue components with Tailwind utility classes — removing all `<style scoped>` blocks. Vitest tests for RoutinesView are updated to match the new component structure.

**Tech Stack:** Vue 3 Composition API, PrimeVue 4 (unstyled mode), Tailwind CSS v4, Vite, FastAPI, Alembic, Vitest, Playwright

---

## File Map

### New files
| File | Purpose |
|---|---|
| `frontend/src/primevue-pt.ts` | Centralised PrimeVue pass-through config — Tailwind classes for every component |
| `alembic/versions/<rev>_drop_sequences_table.py` | Drop the `sequences` table |

### Modified files
| File | Change |
|---|---|
| `backend/models.py` | Remove `Sequence` class |
| `backend/schemas.py` | Remove Sequence schemas |
| `backend/main.py` | Remove sequences router import and `app.include_router(router)` |
| `frontend/tailwind.config.js` | Add `primary` colour tokens |
| `frontend/src/main.ts` | Add ToastService; pass `pt` config to PrimeVue |
| `frontend/src/App.vue` | Add `<Toast />`; replace scoped CSS with Tailwind |
| `frontend/src/router/index.ts` | Remove sequence routes; redirect `/` → `/routines` |
| `frontend/vite.config.ts` | Remove `/sequences` proxy block |
| `frontend/src/components/layout/AppNavbar.vue` | Remove Sequences link; Tailwind styling |
| `frontend/src/components/layout/AppSidebar.vue` | Tailwind styling; remove scoped CSS |
| `frontend/src/views/LoginView.vue` | PrimeVue `InputText` + `Button`; Tailwind |
| `frontend/src/views/AuthCallbackView.vue` | PrimeVue `ProgressSpinner`; Tailwind |
| `frontend/src/views/UsersView.vue` | PrimeVue `DataTable`, `Button`, `Tag`; Tailwind |
| `frontend/src/views/RoutinesView.vue` | Full rewrite — see Task 7 |
| `frontend/src/views/RoutineDetailView.vue` | Full rewrite — see Task 8 |
| `frontend/src/views/ExecutionHistoryView.vue` | PrimeVue `DataTable`, `Select`, `Tag`; Tailwind |
| `frontend/src/__tests__/RoutinesView.test.ts` | Update assertions for PrimeVue structure |

### Deleted files
| File |
|---|
| `backend/routes.py` |
| `backend/services.py` |
| `tests/test_sequences.py` |
| `frontend/src/views/SequenceListView.vue` |
| `frontend/src/views/SequenceDetailView.vue` |
| `frontend/src/api/sequences.ts` |
| `frontend/src/types/sequence.ts` |
| `frontend/src/__tests__/SequenceListView.test.ts` |
| `frontend/src/__tests__/SequenceDetailView.test.ts` |
| `frontend/src/__tests__/api.sequences.test.ts` |
| `frontend/src/__tests__/types.sequence.test.ts` |

---

## Task 1: Delete Sequences — Backend

**Files:**
- Delete: `backend/routes.py`
- Delete: `backend/services.py`
- Modify: `backend/models.py` — remove `Sequence` class
- Modify: `backend/schemas.py` — remove Sequence schemas
- Modify: `backend/main.py` — remove sequences router
- Delete: `tests/test_sequences.py`
- Create: `alembic/versions/<rev>_drop_sequences_table.py`

- [ ] **Step 1: Delete backend/routes.py and backend/services.py**

```bash
rm backend/routes.py backend/services.py
```

- [ ] **Step 2: Remove Sequence model from backend/models.py**

Delete the `Sequence` class entirely. It looks like:
```python
class Sequence(Base):
    __tablename__ = "sequences"
    ...
```

- [ ] **Step 3: Remove Sequence schemas from backend/schemas.py**

Delete `SequenceBase`, `SequenceCreate`, `SequenceUpdate`, and `SequenceResponse` classes. Keep all Routine/Action/Execution schemas.

- [ ] **Step 4: Update backend/main.py — remove sequences router**

Remove these two lines:
```python
from backend.routes import router   # ← delete this import
...
app.include_router(router)          # ← delete this line
```

The remaining routers (`user_router`, `routines_router`, `actions_router`, `executions_router`) stay.

- [ ] **Step 5: Delete tests/test_sequences.py**

```bash
rm tests/test_sequences.py
```

- [ ] **Step 6: Create Alembic migration to drop sequences table**

```bash
.venv/bin/alembic revision --message "drop_sequences_table"
```

Fill in the generated file:

```python
def upgrade() -> None:
    op.drop_table('sequences')

def downgrade() -> None:
    op.create_table(
        'sequences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
```

- [ ] **Step 7: Apply the migration**

```bash
.venv/bin/alembic upgrade head
```

Expected: migration applies cleanly.

- [ ] **Step 8: Run backend tests to verify nothing is broken**

```bash
.venv/bin/pytest tests/ --ignore=tests/perf --ignore=tests/e2e -q
```

Expected: all tests pass (`test_health`, `test_metrics`, `test_routines`).

- [ ] **Step 9: Run ruff + basedpyright on backend**

```bash
.venv/bin/ruff check backend/ && .venv/bin/ruff format --check backend/ && .venv/bin/basedpyright backend/
```

Expected: 0 errors.

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "chore(cleanup): remove sequences domain from backend"
```

---

## Task 2: Delete Sequences — Frontend

**Files:**
- Delete: all sequence frontend files
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/vite.config.ts`

- [ ] **Step 1: Delete all sequence frontend files**

```bash
rm frontend/src/views/SequenceListView.vue
rm frontend/src/views/SequenceDetailView.vue
rm frontend/src/api/sequences.ts
rm frontend/src/types/sequence.ts
rm frontend/src/__tests__/SequenceListView.test.ts
rm frontend/src/__tests__/SequenceDetailView.test.ts
rm frontend/src/__tests__/api.sequences.test.ts
# Also remove if present:
rm -f frontend/src/__tests__/types.sequence.test.ts
```

- [ ] **Step 2: Update frontend/src/router/index.ts**

Remove sequence imports and routes. Change the root redirect to `/routines`. Result:

```typescript
import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import AuthCallbackView from '../views/AuthCallbackView.vue'
import UsersView from '../views/UsersView.vue'
import RoutinesView from '../views/RoutinesView.vue'
import RoutineDetailView from '../views/RoutineDetailView.vue'
import ExecutionHistoryView from '../views/ExecutionHistoryView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/routines' },
    { path: '/login', name: 'login', component: LoginView },
    { path: '/auth/callback', name: 'auth-callback', component: AuthCallbackView },
    { path: '/users', name: 'users', component: UsersView },
    { path: '/routines', name: 'routines', component: RoutinesView },
    {
      path: '/routines/:id',
      name: 'routine-detail',
      component: RoutineDetailView,
      props: (route) => ({ id: Number(route.params.id) }),
    },
    { path: '/history', name: 'history', component: ExecutionHistoryView },
  ],
})

export default router
```

- [ ] **Step 3: Remove /sequences proxy from frontend/vite.config.ts**

Delete the entire `/sequences` block:
```typescript
'/sequences': {
  target: 'http://localhost:8000',
  ...
},
```

- [ ] **Step 4: Run frontend tests**

```bash
cd frontend && npm test
```

Expected: all remaining tests pass (usePolling, api.routines, RoutinesView).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore(cleanup): remove sequences domain from frontend"
```

---

## Task 3: PrimeVue + Tailwind Infrastructure

> **Prerequisite:** Tasks 1 and 2 must be complete before the build step in this task. The router still imports Sequence views until Task 2 removes them.

**Files:**
- Modify: `frontend/tailwind.config.js`
- Create: `frontend/src/primevue-pt.ts`
- Modify: `frontend/src/main.ts`
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: Review frontend/src/style.css — add global base styles if missing**

Open `frontend/src/style.css`. It already has `@tailwind base/components/utilities` directives. Add global base styles if not already present (body background, font-family):

```css
@layer base {
  body {
    @apply bg-slate-50 text-slate-900 font-sans;
  }
}
```

If these styles are already there or equivalent, skip. Do NOT create a second CSS entry point.

- [ ] **Step 2: Add primary colour tokens to tailwind.config.js**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#4f46e5',
          hover: '#4338ca',
          light: '#ede9fe',
          text: '#5b21b6',
        },
      },
    },
  },
  plugins: [],
}
```

- [ ] **Step 3: Create frontend/src/primevue-pt.ts**

This file defines Tailwind utility classes for every PrimeVue component used in the app. The `pt` (pass-through) object is passed to `app.use(PrimeVue, { unstyled: true, pt: primevuePt })`.

```typescript
/**
 * PrimeVue pass-through configuration.
 *
 * Defines Tailwind utility classes for every PrimeVue component used in the
 * app.  Passed to app.use(PrimeVue, { unstyled: true, pt: primevuePt }).
 *
 * PrimeVue PT docs: https://primevue.org/passthrough/
 * Each component's PT slots are listed in its own API docs page.
 */

type Cls = { class: string | Record<string, boolean> | (string | Record<string, boolean>)[] }
type DynCls = (opts: { props: Record<string, unknown> }) => Cls

export const primevuePt: Record<string, Record<string, Cls | DynCls>> = {
  // ── Button ───────────────────────────────────────────────────────────────
  button: {
    root: (({ props }) => ({
      class: [
        'inline-flex items-center gap-1.5 font-medium cursor-pointer transition-colors rounded-md border border-transparent',
        // Size
        props['size'] === 'small'
          ? 'px-2.5 py-1 text-xs'
          : 'px-4 py-2 text-sm',
        // Severity
        !props['severity'] || props['severity'] === 'primary'
          ? 'bg-indigo-600 text-white hover:bg-indigo-700'
          : props['severity'] === 'secondary'
          ? 'bg-transparent text-slate-600 border-slate-300 hover:bg-slate-50'
          : props['severity'] === 'danger'
          ? 'bg-transparent text-red-600 border-red-300 hover:bg-red-50'
          : 'bg-transparent text-slate-600 border-slate-300 hover:bg-slate-50',
        // Disabled
        props['disabled'] ? 'opacity-60 cursor-not-allowed pointer-events-none' : '',
      ],
    })) as DynCls,
  },

  // ── DataTable ─────────────────────────────────────────────────────────────
  datatable: {
    root: { class: 'w-full' },
    table: { class: 'w-full border-collapse text-sm' },
    thead: { class: '' },
    headerRow: { class: '' },
    headerCell: { class: 'px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide bg-slate-50 border-b border-slate-200' },
    tbody: { class: '' },
    row: { class: 'border-t border-slate-100 hover:bg-slate-50 transition-colors' },
    bodyCell: { class: 'px-4 py-3 text-slate-900' },
    emptyMessage: { class: '' },
    emptyMessageCell: { class: 'px-4 py-10 text-center text-sm text-slate-400' },
  },

  // ── Column (used inside DataTable) ───────────────────────────────────────
  column: {
    headerCell: { class: 'px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide bg-slate-50 border-b border-slate-200' },
    bodyCell: { class: 'px-4 py-3 text-slate-900' },
  },

  // ── Dialog ───────────────────────────────────────────────────────────────
  dialog: {
    root: { class: 'bg-white rounded-xl shadow-2xl w-[480px] max-w-[92vw] mx-auto' },
    mask: { class: 'fixed inset-0 bg-slate-900/45 z-50 flex items-center justify-center' },
    header: { class: 'flex items-center justify-between px-6 pt-6 pb-0' },
    title: { class: 'text-lg font-semibold text-slate-900' },
    headerActions: { class: 'flex items-center' },
    closeButton: { class: 'p-1.5 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer border-none bg-transparent' },
    closeIcon: { class: 'w-4 h-4' },
    content: { class: 'px-6 py-5' },
    footer: { class: 'flex justify-end gap-3 px-6 pb-6 pt-2' },
  },

  // ── InputText ─────────────────────────────────────────────────────────────
  inputtext: {
    root: { class: 'w-full px-3 py-2 border border-slate-300 rounded-md text-sm text-slate-900 outline-none transition-colors focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 font-[inherit] bg-white' },
  },

  // ── Textarea ──────────────────────────────────────────────────────────────
  textarea: {
    root: { class: 'w-full px-3 py-2 border border-slate-300 rounded-md text-sm text-slate-900 outline-none transition-colors focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 font-[inherit] resize-y bg-white' },
  },

  // ── Select (formerly Dropdown) ────────────────────────────────────────────
  select: {
    root: { class: 'flex items-center border border-slate-300 rounded-md text-sm bg-white cursor-pointer transition-colors focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-500/20' },
    label: { class: 'flex-1 px-3 py-2 text-slate-900 text-sm' },
    dropdown: { class: 'px-2 text-slate-400 flex items-center' },
    panel: { class: 'bg-white border border-slate-200 rounded-md shadow-lg mt-1 z-50 overflow-hidden' },
    listContainer: { class: 'overflow-y-auto max-h-60' },
    list: { class: 'py-1' },
    option: { class: 'px-3 py-2 text-sm text-slate-900 hover:bg-indigo-50 cursor-pointer' },
  },

  // ── Checkbox ──────────────────────────────────────────────────────────────
  checkbox: {
    root: { class: 'flex items-center gap-2 cursor-pointer select-none' },
    box: { class: 'w-4 h-4 border-2 border-slate-300 rounded transition-colors' },
    icon: { class: 'w-3 h-3 text-white' },
  },

  // ── ProgressSpinner ───────────────────────────────────────────────────────
  progressspinner: {
    root: { class: 'relative w-8 h-8' },
    circle: { class: 'animate-spin stroke-indigo-600' },
  },

  // ── Tag ───────────────────────────────────────────────────────────────────
  tag: {
    root: (({ props }) => ({
      class: [
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize',
        !props['severity'] || props['severity'] === 'primary'
          ? 'bg-indigo-100 text-indigo-700'
          : props['severity'] === 'secondary'
          ? 'bg-slate-100 text-slate-600'
          : props['severity'] === 'success'
          ? 'bg-green-100 text-green-700'
          : props['severity'] === 'danger'
          ? 'bg-red-100 text-red-600'
          : props['severity'] === 'warn'
          ? 'bg-yellow-100 text-yellow-700'
          : props['severity'] === 'info'
          ? 'bg-blue-100 text-blue-700'
          : 'bg-slate-100 text-slate-600',
      ],
    })) as DynCls,
    value: { class: '' },
  },

  // ── Toast ─────────────────────────────────────────────────────────────────
  toast: {
    root: { class: 'fixed bottom-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none' },
    message: (({ props }) => ({
      class: [
        'flex items-start gap-3 px-4 py-3 rounded-lg shadow-lg pointer-events-auto min-w-72 border',
        props['message'] && (props['message'] as Record<string, string>)['severity'] === 'success'
          ? 'bg-green-50 border-green-200'
          : props['message'] && (props['message'] as Record<string, string>)['severity'] === 'error'
          ? 'bg-red-50 border-red-200'
          : props['message'] && (props['message'] as Record<string, string>)['severity'] === 'warn'
          ? 'bg-yellow-50 border-yellow-200'
          : 'bg-blue-50 border-blue-200',
      ],
    })) as DynCls,
    messageContent: { class: 'flex flex-col gap-0.5 flex-1' },
    summary: { class: 'text-sm font-semibold text-slate-900' },
    detail: { class: 'text-sm text-slate-600' },
    closeButton: { class: 'ml-auto p-0.5 rounded hover:bg-black/5 text-slate-400 hover:text-slate-600 border-none bg-transparent cursor-pointer' },
    closeIcon: { class: 'w-4 h-4' },
  },
}
```

> **Note on PT keys:** If a component doesn't render as expected, check its PT slot names in the PrimeVue 4 API docs (e.g. https://primevue.org/datatable/#api.datatable.PassThrough). Slot names changed between v3 and v4.

- [ ] **Step 4: Update frontend/src/main.ts**

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import App from './App.vue'
import router from './router'
import { primevuePt } from './primevue-pt'
import './style.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(PrimeVue, { unstyled: true, pt: primevuePt })
app.use(ToastService)

app.mount('#app')
```

- [ ] **Step 5: Update frontend/src/App.vue**

Replace the entire file. The `<style scoped>` block is replaced with Tailwind classes inline:

```vue
<template>
  <div class="flex flex-col h-screen overflow-hidden">
    <AppNavbar />
    <div class="flex flex-1 overflow-hidden">
      <AppSidebar />
      <main class="flex-1 overflow-y-auto p-7 bg-white">
        <RouterView />
      </main>
    </div>
    <Toast />
  </div>
</template>

<script setup lang="ts">
import Toast from 'primevue/toast'
import AppNavbar from './components/layout/AppNavbar.vue'
import AppSidebar from './components/layout/AppSidebar.vue'
</script>
```

- [ ] **Step 6: Verify build is clean**

```bash
cd frontend && npm run build
```

Expected: builds without type errors or warnings.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat(ui): wire up PrimeVue pass-through and ToastService"
```

---

## Task 4: Migrate Layout Components

**Files:**
- Modify: `frontend/src/components/layout/AppNavbar.vue`
- Modify: `frontend/src/components/layout/AppSidebar.vue`

- [ ] **Step 1: Rewrite AppNavbar.vue**

Remove the Sequences link. Replace the entire `<style scoped>` block with Tailwind inline classes:

```vue
<script setup lang="ts">
import Button from 'primevue/button'
import { useAuth } from '../../composables/useAuth'

const { isAuthenticated, user, login, logout } = useAuth()
</script>

<template>
  <header class="flex items-center justify-between px-6 h-14 bg-slate-800 text-slate-100 flex-shrink-0 border-b border-slate-700">
    <div class="flex items-center gap-6">
      <RouterLink to="/routines" class="text-base font-semibold text-white tracking-tight no-underline">
        Home Auto
      </RouterLink>
      <nav class="flex gap-4">
        <RouterLink to="/routines" class="text-sm text-slate-400 no-underline hover:text-white transition-colors [&.router-link-active]:text-white">Routines</RouterLink>
        <RouterLink to="/history" class="text-sm text-slate-400 no-underline hover:text-white transition-colors [&.router-link-active]:text-white">History</RouterLink>
        <RouterLink to="/users" class="text-sm text-slate-400 no-underline hover:text-white transition-colors [&.router-link-active]:text-white">Users</RouterLink>
      </nav>
    </div>
    <div class="flex items-center gap-3">
      <template v-if="isAuthenticated && user">
        <span class="text-xs text-slate-400">{{ user.email }}</span>
        <Button label="Logout" size="small" severity="secondary" @click="logout" />
      </template>
      <Button v-else label="Sign in with Google" size="small" @click="login" />
    </div>
  </header>
</template>
```

- [ ] **Step 2: Rewrite AppSidebar.vue**

The current sidebar only has a Sequences nav item (being deleted) and a version footer. Replace entirely with Tailwind (no scoped CSS):

```vue
<template>
  <aside class="w-[220px] shrink-0 bg-slate-50 border-r border-slate-200 flex flex-col justify-between py-4 hidden md:flex">
    <nav class="flex flex-col gap-1 px-3">
      <RouterLink
        to="/routines"
        class="flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium text-slate-600 hover:bg-slate-200 hover:text-slate-900 transition-colors no-underline"
        active-class="bg-indigo-100 text-indigo-800"
      >
        <span class="w-4 text-center">&#9776;</span>
        <span>Routines</span>
      </RouterLink>
    </nav>
    <div class="px-6">
      <span class="text-xs text-slate-400">v0.1.0</span>
    </div>
  </aside>
</template>
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(ui): migrate navbar and sidebar to Tailwind"
```

---

## Task 5: Migrate LoginView + AuthCallbackView

**Files:**
- Modify: `frontend/src/views/LoginView.vue`
- Modify: `frontend/src/views/AuthCallbackView.vue`

- [ ] **Step 1: Rewrite LoginView.vue**

Read the current file first. Replace with PrimeVue `InputText` + `Button` and Tailwind layout:

```vue
<script setup lang="ts">
import { ref } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import { useAuth } from '../composables/useAuth'

const { login } = useAuth()
const email = ref('')
const password = ref('')
</script>

<template>
  <div class="flex items-center justify-center min-h-[70vh]">
    <div class="w-full max-w-sm border border-slate-200 rounded-xl p-8 shadow-sm bg-white">
      <h1 class="text-xl font-semibold text-slate-900 mb-6 text-center">Sign in</h1>
      <div class="flex flex-col gap-4">
        <Button label="Sign in with Google" class="w-full justify-center" @click="login" />
      </div>
    </div>
  </div>
</template>
```

> **Note:** Read the actual `LoginView.vue` before rewriting — it may have more logic (password auth form etc.) that must be preserved. Replace only the template/style, not the script logic.

- [ ] **Step 2: Rewrite AuthCallbackView.vue**

Read the current file first. Replace scoped CSS with PrimeVue `<ProgressSpinner>`:

```vue
<script setup lang="ts">
import ProgressSpinner from 'primevue/progressspinner'
// Existing script logic unchanged — preserve all imports and composable calls
</script>

<template>
  <div class="flex items-center justify-center min-h-[70vh] gap-3 text-slate-500">
    <ProgressSpinner class="w-8 h-8" />
    <span class="text-sm">Signing you in…</span>
  </div>
</template>
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(ui): migrate LoginView and AuthCallbackView to PrimeVue + Tailwind"
```

---

## Task 6: Migrate UsersView

**Files:**
- Modify: `frontend/src/views/UsersView.vue`

- [ ] **Step 1: Read UsersView.vue**

Read the full file first to understand its current structure before rewriting.

- [ ] **Step 2: Rewrite template and style — preserve all script logic**

Replace the `<template>` and `<style scoped>` sections. Use `DataTable` + `Column` for the users list, `Tag` for role badges, `Button` for actions. Example column:

```vue
<DataTable :value="users" class="border border-slate-200 rounded-lg overflow-hidden">
  <Column field="email" header="Email" />
  <Column field="role" header="Role">
    <template #body="{ data }">
      <Tag :value="data.role" :severity="data.role === 'admin' ? 'primary' : 'secondary'" />
    </template>
  </Column>
  <Column header="Actions">
    <template #body="{ data }">
      <Button label="Remove" severity="danger" size="small" @click="removeUser(data)" />
    </template>
  </Column>
</DataTable>
```

Add required imports at the top of `<script setup>`:
```typescript
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(ui): migrate UsersView to PrimeVue + Tailwind"
```

---

## Task 7: Migrate RoutinesView

**Files:**
- Modify: `frontend/src/views/RoutinesView.vue`

This is the largest view. Read the full current file before starting. Preserve all script logic — refs, functions, `usePolling` calls, `runNow`, CRUD handlers. Only the `<template>` and `<style scoped>` change.

- [ ] **Step 1: Add PrimeVue imports to script setup**

```typescript
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import Checkbox from 'primevue/checkbox'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'

const toast = useToast()
```

- [ ] **Step 2: Replace Toast calls in runNow function**

Replace the `runNowSuccess` / `runNowError` ref pattern with toast notifications:

```typescript
async function runNow(routine: Routine): Promise<void> {
  runNowLoading.value[routine.id] = true
  try {
    await routinesApi.runNow(routine.id)
    toast.add({ severity: 'success', summary: 'Started', detail: `${routine.name} is running`, life: 3000 })
    await refreshActive()
  } catch (e) {
    const msg = e instanceof Error ? e.message : 'Failed to start'
    toast.add({ severity: msg.includes('already running') ? 'warn' : 'error', summary: 'Run Now', detail: msg, life: 4000 })
  } finally {
    delete runNowLoading.value[routine.id]
  }
}
```

Remove `runNowSuccess` and `runNowError` refs — they are replaced by toast.

- [ ] **Step 3: Rewrite template**

Key structural changes:
1. **Routines table** → `<DataTable>` with columns for Name, Schedule, Active, Actions
2. **Executing + History panels** → side-by-side in a `grid grid-cols-2 gap-4` container
3. **Create/Edit dialog** → PrimeVue `<Dialog>` with `:visible` binding
4. **Delete dialog** → PrimeVue `<Dialog>` with `:visible` binding
5. **All `<style scoped>`** → deleted

Dialog binding pattern (PrimeVue 4 uses `:visible` + `@update:visible`):
```vue
<Dialog
  :visible="formDialogOpen"
  :modal="true"
  :header="editingRoutine ? 'Edit Routine' : 'New Routine'"
  @update:visible="formDialogOpen = false"
>
  <!-- form content -->
</Dialog>
```

Replace the `ref<HTMLDialogElement>` + `showModal()`/`close()` pattern with a `ref<boolean>` for each dialog:
```typescript
const formDialogOpen = ref(false)
const deleteDialogOpen = ref(false)

function openCreate(): void {
  // ... reset form
  formDialogOpen.value = true
}

function openEdit(routine: Routine): void {
  // ... populate form
  formDialogOpen.value = true
}
```

Executing panel card:
```vue
<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
  <!-- Currently Executing -->
  <div class="border border-slate-200 rounded-lg overflow-hidden">
    <div class="px-4 py-3 border-b border-slate-200">
      <h2 class="text-sm font-semibold text-slate-900 m-0">Currently Executing</h2>
    </div>
    <!-- table or empty state -->
  </div>

  <!-- Recent History -->
  <div class="border border-slate-200 rounded-lg overflow-hidden">
    <div class="px-4 py-3 border-b border-slate-200">
      <h2 class="text-sm font-semibold text-slate-900 m-0">Recent History</h2>
    </div>
    <!-- table or empty state -->
  </div>
</div>
```

Tag severity mapping for schedule types:
- `cron` → `severity="primary"` (indigo)
- `interval` → `severity="info"` (blue)
- `manual` → `severity="secondary"` (slate)

Tag severity mapping for execution status:
- `running` → `severity="warn"` (yellow)
- `completed` → `severity="success"` (green)
- `failed` → `severity="danger"` (red)

- [ ] **Step 4: Remove `<style scoped>` block entirely**

Delete everything between `<style scoped>` and `</style>`.

- [ ] **Step 5: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(ui): migrate RoutinesView to PrimeVue + Tailwind"
```

---

## Task 8: Migrate RoutineDetailView

**Files:**
- Modify: `frontend/src/views/RoutineDetailView.vue`

Read the full current file before starting. Preserve all script logic.

- [ ] **Step 1: Add PrimeVue imports and useToast**

```typescript
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import Checkbox from 'primevue/checkbox'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'

const toast = useToast()
```

- [ ] **Step 2: Replace runNow feedback with toast**

```typescript
async function runNow(): Promise<void> {
  if (!routine.value) return
  runNowLoading.value = true
  try {
    await routinesApi.runNow(routine.value.id)
    toast.add({ severity: 'success', summary: 'Started', detail: `${routine.value.name} is running`, life: 3000 })
  } catch (e) {
    const msg = e instanceof Error ? e.message : 'Failed to start'
    toast.add({ severity: 'error', summary: 'Run Now failed', detail: msg, life: 4000 })
  } finally {
    runNowLoading.value = false
  }
}
```

Remove `runNowSuccess` and `runNowError` refs.

- [ ] **Step 3: Rewrite template**

Key points:
- Page layout: `flex flex-col gap-5 max-w-3xl`
- Back link: `<RouterLink to="/routines" class="text-sm text-indigo-600 hover:underline font-medium">← Back</RouterLink>`
- Header: `flex items-center justify-between`
- Detail list (read-only metadata): CSS grid with labelled rows — `grid grid-cols-[140px_1fr]`
- Edit form: inside a `border border-slate-200 rounded-lg p-5` card
- Actions list: `flex flex-col border border-slate-200 rounded-lg overflow-hidden`, each action row a `flex items-center gap-3 px-4 py-3 border-b border-slate-100`
- Add action form: inside a `border border-slate-200 rounded-lg p-4`
- `<Select>` for schedule_type and action_type dropdowns — uses `:options` array + `optionLabel`/`optionValue`

Select usage pattern:
```vue
<Select
  v-model="form.schedule_type"
  :options="[
    { label: 'manual', value: 'manual' },
    { label: 'cron', value: 'cron' },
    { label: 'interval', value: 'interval' },
  ]"
  option-label="label"
  option-value="value"
  class="w-full"
/>
```

- [ ] **Step 4: Remove `<style scoped>` block**

- [ ] **Step 5: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(ui): migrate RoutineDetailView to PrimeVue + Tailwind"
```

---

## Task 9: Migrate ExecutionHistoryView

**Files:**
- Modify: `frontend/src/views/ExecutionHistoryView.vue`

Read the full current file before starting.

- [ ] **Step 1: Add PrimeVue imports**

```typescript
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
```

- [ ] **Step 2: Rewrite template**

- Page header with `<Select>` for routine filter dropdown
- `<DataTable>` for execution history rows
- `<Tag>` for status and triggered_by badges
- Remove `<style scoped>`

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(ui): migrate ExecutionHistoryView to PrimeVue + Tailwind"
```

---

## Task 10: Update RoutinesView Tests

**Files:**
- Modify: `frontend/src/__tests__/RoutinesView.test.ts`

- [ ] **Step 1: Remove the HTMLDialogElement polyfill**

Delete these lines — they're no longer needed since native `<dialog>` is replaced by PrimeVue `<Dialog>`:
```typescript
HTMLDialogElement.prototype.showModal = vi.fn()
HTMLDialogElement.prototype.close = vi.fn()
```

- [ ] **Step 2: Add ToastService to global plugins**

PrimeVue's `useToast()` composable requires `ToastService` to be registered. Add it to the `mount` call's `global.plugins`:

```typescript
import ToastService from 'primevue/toastservice'

// In each test that mounts RoutinesView:
const wrapper = mount(RoutinesView, {
  global: {
    plugins: [makeRouter(), ToastService],
  },
})
```

Or add it to a shared mount helper if one exists in the test file.

- [ ] **Step 3: Update assertions**

Read `frontend/src/__tests__/RoutinesView.test.ts` first to identify which assertions target raw HTML elements or CSS class names. Then update them.

Assertions currently targeting raw HTML elements need updating. The key principle: **assert on visible text and behaviour, not internal DOM structure**. Most text-based assertions will still pass; the ones that fail are those checking for specific HTML elements like `<dialog>`, `<table>`, or CSS class names.

Common patterns after migration:
```typescript
// Before (raw element)
expect(wrapper.find('dialog').exists()).toBe(true)

// After (PrimeVue Dialog — visible text or data-testid)
expect(wrapper.text()).toContain('New Routine')

// Before (button by class)
expect(wrapper.find('.btn--primary').text()).toBe('Save')

// After (button by visible text)
expect(wrapper.find('button[type="submit"]').text()).toContain('Save')
// or find by text content
const buttons = wrapper.findAll('button')
const saveBtn = buttons.find(b => b.text().includes('Save'))
```

- [ ] **Step 4: Run tests and fix all failures**

```bash
cd frontend && npm test -- --reporter=verbose 2>&1 | head -60
```

Fix each failing test. Re-run until all pass.

- [ ] **Step 5: Run full frontend test suite**

```bash
cd frontend && npm test
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "test(ui): update RoutinesView tests for PrimeVue components"
```

---

## Task 11: Final Verification

- [ ] **Step 1: Run backend tests**

```bash
.venv/bin/pytest tests/ --ignore=tests/perf --ignore=tests/e2e -q
```

Expected: all pass.

- [ ] **Step 2: Run frontend tests**

```bash
cd frontend && npm test
```

Expected: all pass.

- [ ] **Step 3: Run frontend build**

```bash
cd frontend && npm run build
```

Expected: builds clean with no errors or warnings.

- [ ] **Step 4: Run ruff + basedpyright**

```bash
.venv/bin/ruff check backend/ && .venv/bin/basedpyright backend/
```

Expected: 0 errors.

- [ ] **Step 5: Run ESLint**

```bash
cd frontend && npm run lint
```

Expected: no errors.

- [ ] **Step 6: Commit any remaining fixes, then push**

```bash
git add -A
git commit -m "chore: final cleanup after PrimeVue migration"
git push origin feat/primevue-tailwind-migration
```
