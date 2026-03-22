# PrimeVue + Tailwind Migration — Design Spec

**Date:** 2026-03-22
**Status:** Approved

---

## Overview

Replace all hand-rolled scoped CSS across the Vue 3 frontend with PrimeVue unstyled components styled via Tailwind CSS pass-through (PT). Simultaneously remove the Sequences domain entirely (frontend + backend) and focus the application on the Routines domain. Migration is a single big-bang branch covering all files.

---

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| PrimeVue mode | Unstyled + Tailwind PT | Matches user's work setup; full styling control |
| Palette | Indigo (existing) | No visual disruption; evolve rather than redesign |
| Migration strategy | Big bang | Project is small; no production risk |
| Sequences | Delete everything | Domain was a learning scaffold; Routines is the focus |
| Error/success feedback | PrimeVue `Toast` | Replaces ~15 scattered inline banner patterns |

---

## Part 1: Deletions — Sequences Domain

### Backend

- **`backend/routes.py`** — delete entirely (sequences routes only)
- **`backend/services.py`** — delete entirely (sequences services only)
- **`backend/models.py`** — remove `Sequence` class
- **`backend/schemas.py`** — remove `SequenceBase`, `SequenceCreate`, `SequenceUpdate`, `SequenceResponse`
- **`backend/main.py`** — remove sequences router import and `app.include_router` call
- **`tests/test_sequences.py`** — delete
- **New Alembic migration** — `drop_sequences_table`: `DROP TABLE sequences` to keep the migration chain clean. This is the new head migration and depends on the current head (`ce0b38a4532b`).

`tests/test_health.py` and `tests/test_metrics.py` are retained — they are not sequences-specific.

### Frontend

- **`src/views/SequenceListView.vue`** — delete
- **`src/views/SequenceDetailView.vue`** — delete
- **`src/api/sequences.ts`** — delete
- **`src/types/sequence.ts`** — delete
- **`src/__tests__/SequenceListView.test.ts`** — delete
- **`src/__tests__/SequenceDetailView.test.ts`** — delete
- **`src/__tests__/api.sequences.test.ts`** — delete
- **`src/__tests__/types.sequence.test.ts`** — delete (if present)
- **`src/router/index.ts`** — remove `/sequences` and `/sequences/:id` routes
- **`src/components/layout/AppNavbar.vue`** — remove "Sequences" nav link
- **`vite.config.ts`** — remove `/sequences` proxy block

---

## Part 2: PrimeVue + Tailwind Setup

### Configuration

**`src/primevue-pt.ts`** — new file, centralised pass-through definitions.

Defines Tailwind class strings for every PrimeVue component used in the app. Exported as a single object passed to `app.use(PrimeVue, { unstyled: true, pt: primevuePt })` in `main.ts`.

```typescript
// Shape only — classes filled in during implementation
export const primevuePt = {
  button: { root: { class: '...' } },
  datatable: { ... },
  dialog: { ... },
  inputtext: { ... },
  select: { ... },
  tag: { ... },
  // ...
}
```

**`src/style.css`** — already exists and already imports Tailwind base/components/utilities. Update in place to add any additional global base styles needed (e.g. font-family, body background). Do **not** create a second Tailwind entry point — `style.css` is already imported in `main.ts`.

**`tailwind.config.js`** — already exists. Update (not add) to extend `colors` with named indigo tokens:

```js
colors: {
  primary: {
    DEFAULT: '#4f46e5',  // indigo-600
    hover:   '#4338ca',  // indigo-700
    light:   '#ede9fe',  // violet-100
    text:    '#5b21b6',  // violet-800
  }
}
```

**`main.ts`** changes:
- `style.css` is already imported — no Tailwind import change needed
- Import `ToastService` from `primevue/toastservice` and `app.use(ToastService)`
- Pass `pt: primevuePt` to `app.use(PrimeVue, ...)`

**`App.vue`** — add `<Toast />` component (global toast outlet).

### Component Mapping

| Current pattern | PrimeVue component |
|---|---|
| `<button class="btn ...">` | `<Button>` |
| `<dialog>` (native) | `<Dialog>` |
| `<table class="data-table">` | `<DataTable>` + `<Column>` |
| `<input type="text">` | `<InputText>` |
| `<textarea>` | `<Textarea>` |
| `<select>` | `<Select>` |
| `<input type="checkbox">` | `<Checkbox>` |
| `.badge` / status spans | `<Tag>` |
| `.spinner` CSS animation | `<ProgressSpinner>` |
| Inline `.alert--error/success` banners | `<Toast>` via `useToast()` |

All `<style scoped>` blocks are removed from every migrated file. Layout, spacing, colour, and typography are expressed exclusively in Tailwind utility classes.

---

## Part 3: View-by-View Migration

### Layout components

**`AppNavbar.vue`**
- Remove scoped CSS; use Tailwind for layout and colours
- Remove "Sequences" link
- Keep "Routines" and "History" links

**`AppSidebar.vue`**
- Remove scoped CSS; use Tailwind

### Views

**`LoginView.vue`**
- `<InputText>` for email/password fields
- `<Button>` for submit
- Tailwind layout; remove scoped CSS

**`AuthCallbackView.vue`**
- `<ProgressSpinner>` for loading state
- Tailwind layout; remove scoped CSS

**`UsersView.vue`**
- `<DataTable>` + `<Column>` for user list
- `<Tag>` for role badges
- `<Button>` for actions
- Tailwind layout; remove scoped CSS

**`RoutinesView.vue`**
- `<DataTable>` + `<Column>` for configured routines table
- `<Button>` for New Routine, Edit, Delete, Run Now
- `<Dialog>` for create/edit and delete confirmation modals
- `<InputText>`, `<Textarea>`, `<Select>`, `<Checkbox>` in the dialog form
- `<Tag>` for schedule type and status badges
- `<ProgressSpinner>` for loading states
- `useToast()` for Run Now success/409 conflict feedback (replaces inline banners)
- **Layout change:** "Currently Executing" and "Recent History" panels become side-by-side cards below the full-width routines table (two-column grid on desktop, stacked on mobile)

**`RoutineDetailView.vue`**
- `<InputText>`, `<Textarea>`, `<Select>`, `<Checkbox>` for edit form
- `<Button>` for Save, Cancel, Run Now, up/down reorder, Delete action
- `<Tag>` for schedule type and action type badges
- `useToast()` for Run Now success/error feedback
- Tailwind layout; remove scoped CSS

**`ExecutionHistoryView.vue`**
- `<DataTable>` + `<Column>` for history list
- `<Select>` for routine filter dropdown
- `<Tag>` for status badges
- Tailwind layout; remove scoped CSS

---

## Part 4: Test Updates

### Vitest unit tests

Tests for migrated views must be updated — current assertions target raw HTML elements (`button`, `table`, `dialog`) and CSS class names. After migration, assertions target:
- PrimeVue component names (via `findComponent`)
- Visible text content and ARIA attributes
- Emitted events and prop values

Files requiring updates:
- `src/__tests__/RoutinesView.test.ts` — assertions updated; remove `HTMLDialogElement.prototype.showModal` polyfill (no longer needed once native `<dialog>` is replaced by PrimeVue `<Dialog>`); add `ToastService` to `global.plugins` in mount options for components that use `useToast()`
- `src/__tests__/usePolling.test.ts` — no changes needed (composable is untouched)
- `src/__tests__/api.routines.test.ts` — no changes needed (API client is untouched)

### Playwright E2E

`frontend/e2e/routines.spec.ts` — minimal changes expected. Tests drive by visible text and labels which remain stable across the component swap.

---

## Out of Scope

- Dark mode
- PrimeVue Styled mode / theme presets
- Pinia global state (local component state is sufficient)
- Drag-to-reorder actions (up/down buttons remain)
- Responsive breakpoints beyond the two-column executing/history layout

---

## Files Changed Summary

| File | Action |
|---|---|
| `backend/routes.py` | Delete |
| `backend/services.py` | Delete |
| `backend/models.py` | Remove Sequence model |
| `backend/schemas.py` | Remove Sequence schemas |
| `backend/main.py` | Remove sequences router |
| `tests/test_sequences.py` | Delete |
| `alembic/versions/<new>.py` | Add — drop sequences table |
| `src/primevue-pt.ts` | Add — centralised PT config |
| `src/style.css` | Update — extend existing Tailwind entry point if needed |
| `tailwind.config.js` | Update — add indigo colour tokens |
| `vite.config.ts` | Update — remove `/sequences` proxy block |
| `src/main.ts` | Update — ToastService, PT config |
| `src/App.vue` | Update — add `<Toast />` |
| `src/router/index.ts` | Remove sequence routes |
| `AppNavbar.vue` | Remove Sequences link, Tailwind styling |
| `AppSidebar.vue` | Tailwind styling |
| `LoginView.vue` | PrimeVue components, Tailwind |
| `AuthCallbackView.vue` | PrimeVue components, Tailwind |
| `UsersView.vue` | PrimeVue components, Tailwind |
| `RoutinesView.vue` | PrimeVue components, Tailwind, layout update |
| `RoutineDetailView.vue` | PrimeVue components, Tailwind |
| `ExecutionHistoryView.vue` | PrimeVue components, Tailwind |
| `src/__tests__/RoutinesView.test.ts` | Update assertions |
| `src/views/SequenceListView.vue` | Delete |
| `src/views/SequenceDetailView.vue` | Delete |
| `src/api/sequences.ts` | Delete |
| `src/types/sequence.ts` | Delete |
| `src/__tests__/SequenceListView.test.ts` | Delete |
| `src/__tests__/SequenceDetailView.test.ts` | Delete |
| `src/__tests__/api.sequences.test.ts` | Delete |
| `src/__tests__/types.sequence.test.ts` | Delete |
