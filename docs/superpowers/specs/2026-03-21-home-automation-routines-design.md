# Home Automation Routines — Design Spec

**Date:** 2026-03-21
**Status:** Approved

---

## Overview

Extend the existing FastAPI + Vue 3 application with a **Home Automation Routines** domain. A Routine is a named, ordered sequence of Actions that executes on a cron schedule, a repeating interval, or immediately on demand. The primary learning goal is well-structured Vue 3 patterns: reactive CRUD tables, a reusable polling composable, and dynamic multi-panel home page updates.

---

## Domain Model

### Routine

A named automation that owns an ordered list of Actions and a schedule.

| Field | Type | Notes |
|---|---|---|
| `id` | Integer | Primary key |
| `name` | String | Required |
| `description` | String | Nullable |
| `schedule_type` | Enum | `cron` \| `interval` \| `manual` |
| `schedule_config` | JSON | `{"cron": "0 7 * * *"}` or `{"seconds": 7200}` — null for manual |
| `is_active` | Boolean | Whether APScheduler should register this routine |
| `created_at` | DateTime | Server default `now()` |

### Action

An ordered step within a Routine. Two types supported initially.

| Field | Type | Notes |
|---|---|---|
| `id` | Integer | Primary key |
| `routine_id` | Integer | FK → `routines` |
| `position` | Integer | Ordering within the routine |
| `action_type` | Enum | `sleep` \| `echo` |
| `config` | JSON | `{"seconds": 5}` for sleep; `{"message": "Hello"}` for echo |

### RoutineExecution

An append-only record of each time a Routine ran.

| Field | Type | Notes |
|---|---|---|
| `id` | Integer | Primary key |
| `routine_id` | Integer | FK → `routines` |
| `status` | Enum | `running` \| `completed` \| `failed` |
| `triggered_by` | Enum | `cron` \| `interval` \| `manual` |
| `started_at` | DateTime | Set on creation |
| `completed_at` | DateTime | Nullable — set when status changes to completed/failed |

---

## Backend Architecture

### Scheduler Lifecycle

APScheduler (`BackgroundScheduler`) starts in a FastAPI `lifespan` handler. On startup it queries all `is_active=True` routines and registers their jobs. Cron routines use `CronTrigger`; interval routines use `IntervalTrigger`. Each job dispatches to a thread pool executor, consistent with the project's sync-first architecture.

### Execution Engine

When a job fires (scheduled or via Run Now):

1. Insert a `routine_executions` row with `status=running`
2. Iterate actions ordered by `position`
3. `sleep` → `time.sleep(n)`; `echo` → `logger.info(message)`
4. On success: update status to `completed`, set `completed_at`
5. On any exception: update status to `failed`, set `completed_at`, log the error

### API Surface

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/routines` | List all routines |
| `POST` | `/routines` | Create a routine |
| `GET` | `/routines/{id}` | Get routine detail |
| `PUT` | `/routines/{id}` | Update routine (name, schedule, is_active) |
| `DELETE` | `/routines/{id}` | Delete routine (cancels scheduler job) |
| `GET` | `/routines/{id}/actions` | List actions for a routine |
| `POST` | `/routines/{id}/actions` | Add an action |
| `PUT` | `/actions/{id}` | Update action (type, config, position) |
| `DELETE` | `/actions/{id}` | Remove an action |
| `POST` | `/routines/{id}/run` | Trigger immediate execution (returns 409 if already running) |
| `GET` | `/executions/active` | Currently running executions (polled by frontend) |
| `GET` | `/executions/history` | Recent completed/failed executions |

### Conflict Guard

`POST /routines/{id}/run` checks for an existing `running` execution before inserting. Returns `409 Conflict` if one exists.

### Configuration

New settings in `backend/config.py`:
- `scheduler_enabled: bool = True` — allows disabling APScheduler in test environments

---

## Frontend Architecture

### `usePolling(fn, intervalMs)` Composable

The core Vue learning pattern. Calls `fn` on a timer, cleans up on `onUnmounted`.

```ts
// Exposes:
const { data, loading, error, refresh } = usePolling(fetchActiveExecutions, 3000)
```

- `data` — reactive ref updated on each successful poll
- `loading` — true only on the initial fetch
- `error` — populated on failure; panel shows a subtle error state rather than crashing
- `refresh()` — callable externally to trigger an immediate poll (used by Run Now button)

### Home Page Panels

Three panels rendered on the home page:

**Configured Routines**
Standard CRUD table. On create/edit/delete the local `ref` array is updated directly after the API call — no polling needed. Each row has Edit, Delete, and Run Now buttons. Run Now posts to `/routines/{id}/run` then calls `refresh()` on the executing panel.

**Currently Executing**
Polls `/executions/active` every 3 seconds via `usePolling`. Rows appear when a routine starts and disappear when it completes. Shows routine name, trigger type, and elapsed time.

**Recent History**
Polls `/executions/history` every 5 seconds via `usePolling`. Shows last 10 completed/failed runs with routine name, status, trigger type, and duration.

### Additional Pages

**Routine Detail / Edit**
- Manage action list: add, remove, reorder (up/down buttons)
- Configure schedule type and schedule config
- Run Now button

**Execution History**
- Full paginated history view for a single routine or all routines

### Navigation

New nav items added to the existing `AppNavbar`:
- **Routines** → home page (three-panel view)
- **History** → full execution history page

---

## Testing

### Backend

- Real PostgreSQL via testcontainers (existing pattern)
- Tests cover: routine CRUD, action CRUD with ordering, execution lifecycle (`running` → `completed` / `failed`), 409 conflict guard on Run Now
- APScheduler disabled in tests via `scheduler_enabled=False` config override — execution engine called directly in tests

### Frontend

- **Vitest**: unit tests for `usePolling` (mock timers via `vi.useFakeTimers`), API client functions, and key components
- **Playwright E2E**: create a routine with an `echo` + `sleep` action → click Run Now → assert it appears in the executing panel → assert it moves to history when done

### Allure

All test classes decorated with `@allure.feature("Routines")` / `@allure.story(...)` per existing project standards.

---

## Migration Strategy

Two Alembic migrations:
1. `add_routines_and_actions_tables`
2. `add_routine_executions_table`

Existing `sequences` table and routes remain untouched. The new domain lives alongside the existing one.

---

## Action Types — Extensibility Note

`sleep` and `echo` are the two initial action types. The `action_type` enum and `config` JSON field are intentionally open — adding a `http_request` or `home_assistant` type later requires only a new branch in the execution engine and a new config schema, with no structural DB changes.

---

## Out of Scope (This Phase)

- Step-level execution progress (routine-level status only)
- Real smart home device integration
- WebSockets / SSE (polling is sufficient and simpler to learn first)
- Drag-to-reorder actions (up/down buttons only)
- Multi-user routine ownership
